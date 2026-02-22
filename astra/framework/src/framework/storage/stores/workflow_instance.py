"""
WorkflowInstanceStore - domain store for DSL workflow execution runs.

Provides CRUD operations over the astra_workflow_instances collection.
Each document tracks a single workflow execution: status, node states,
state snapshots, and the execution journal.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from framework.storage.base import StorageBackend
from framework.storage.databases.mongodb import MongoDBStorage
from framework.storage.models import NodeExecution, WorkflowInstance
from framework.storage.stores.base import BaseStore


class WorkflowInstanceStore(BaseStore[WorkflowInstance]):
    """
    WorkflowInstanceStore manages astra_workflow_instances records.

    Methods:
    - create(WorkflowInstance) -> WorkflowInstance
    - get(instance_id) -> WorkflowInstance | None
    - update_status(instance_id, status, **fields) -> WorkflowInstance | None
    - update_node(instance_id, node_id, node_data) -> None
    - list_by_agent(agent_id, limit) -> list[WorkflowInstance]
    - list_by_status(status) -> list[WorkflowInstance]
    """

    def __init__(self, storage: StorageBackend) -> None:
        super().__init__(
            storage=storage,
            model_cls=WorkflowInstance,
            collection_name="astra_workflow_instances",
        )

    def _get_id_field(self) -> str:
        """Return the ID field name based on storage backend."""
        if isinstance(self._storage, MongoDBStorage):
            return "_id"
        return "id"

    async def create(self, instance: WorkflowInstance) -> WorkflowInstance:
        """
        Insert a new workflow instance.

        Args:
            instance: WorkflowInstance object to create

        Returns:
            Created WorkflowInstance with id populated
        """
        data = instance.model_dump(exclude_unset=True)

        # For SQL backends, generate id if not provided
        if not isinstance(self._storage, MongoDBStorage):
            if "id" not in data or data.get("id") is None:
                data["id"] = f"wfi-{uuid4().hex[:10]}"

        doc = self._prepare_document(data)
        result = await self.storage.execute(
            self.storage.build_insert_query(self.collection_name, doc)
        )

        if isinstance(self._storage, MongoDBStorage) and result:
            data["id"] = str(result.inserted_id)

        return WorkflowInstance(**data)

    async def get(self, instance_id: str) -> WorkflowInstance | None:
        """
        Fetch a single workflow instance by ID.

        Args:
            instance_id: Workflow instance identifier

        Returns:
            WorkflowInstance or None if not found
        """
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(instance_id)}
            except Exception:
                filter_dict = {id_field: instance_id}
        else:
            filter_dict = {id_field: instance_id}

        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            limit=1,
        )
        row = await self.storage.fetch_one(query)
        if row is None:
            return None
        return self._row_to_model(row)

    async def update_status(
        self,
        instance_id: str,
        status: str,
        **fields: object,
    ) -> WorkflowInstance | None:
        """
        Update workflow status and any additional fields.

        Args:
            instance_id: Workflow instance identifier
            status: New status (RUNNING, FAILED, WAITING, COMPLETED, CANCELLED)
            **fields: Additional fields to update (e.g., error, response, state_snapshot)

        Returns:
            Updated WorkflowInstance or None if not found
        """
        id_field = self._get_id_field()

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(instance_id)}
            except Exception:
                filter_dict = {id_field: instance_id}
        else:
            filter_dict = {id_field: instance_id}

        update_data: dict = {
            "status": status,
            "updated_at": datetime.now(timezone.utc),
            **fields,
        }

        # Set completed_at and duration_ms on terminal statuses
        if status in ("COMPLETED", "FAILED", "CANCELLED"):
            update_data["completed_at"] = datetime.now(timezone.utc)

        query = self.storage.build_update_query(
            collection=self.collection_name,
            filter_dict=filter_dict,
            update_data=update_data,
        )
        await self.storage.execute(query)
        return await self.get(instance_id)

    async def update_node(
        self,
        instance_id: str,
        node_id: str,
        node_data: NodeExecution,
    ) -> None:
        """
        Update a single node's execution state within the instance.

        For MongoDB: Uses dot-notation for atomic nested update.
        For SQL: Reads full node_status_map, modifies, writes back.

        Args:
            instance_id: Workflow instance identifier
            node_id: Node identifier within the workflow
            node_data: NodeExecution object representing the new state
        """
        id_field = self._get_id_field()
        node_dict = node_data.model_dump(exclude_unset=True)

        if isinstance(self._storage, MongoDBStorage):
            from bson import ObjectId

            try:
                filter_dict = {id_field: ObjectId(instance_id)}
            except Exception:
                filter_dict = {id_field: instance_id}

            # MongoDB supports atomic dot-notation updates
            update_data = {
                f"node_status_map.{node_id}": node_dict,
                "updated_at": datetime.now(timezone.utc),
            }

            query = self.storage.build_update_query(
                collection=self.collection_name,
                filter_dict=filter_dict,
                update_data=update_data,
            )
            await self.storage.execute(query)
        else:
            # SQL: read-modify-write the JSON column
            instance = await self.get(instance_id)
            if instance is None:
                return

            # Convert all existing NodeExecution objects to dicts for JSON storage
            node_map: dict[str, Any] = {
                k: v.model_dump() if hasattr(v, "model_dump") else v
                for k, v in dict(instance.node_status_map).items()
            }
            node_map[node_id] = node_dict

            filter_dict = {id_field: instance_id}
            query = self.storage.build_update_query(
                collection=self.collection_name,
                filter_dict=filter_dict,
                update_data={
                    "node_status_map": node_map,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            await self.storage.execute(query)

    async def list_by_agent(
        self,
        agent_id: str,
        limit: int = 50,
    ) -> list[WorkflowInstance]:
        """
        List workflow instances for a specific agent, most recent first.

        Args:
            agent_id: Agent identifier
            limit: Maximum results (default 50)

        Returns:
            List of WorkflowInstance objects
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"agent_id": agent_id},
            sort=[("created_at", -1)],
            limit=limit,
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]

    async def list_by_status(self, status: str) -> list[WorkflowInstance]:
        """
        List all instances with a given status.

        Primarily used for crash recovery (status="RUNNING").

        Args:
            status: Status to filter by

        Returns:
            List of WorkflowInstance objects
        """
        query = self.storage.build_select_query(
            collection=self.collection_name,
            filter_dict={"status": status},
            sort=[("created_at", -1)],
        )
        rows = await self.storage.fetch_all(query)
        return [self._row_to_model(row) for row in rows]
