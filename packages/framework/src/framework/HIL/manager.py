"""
HIL Manager - Central pause/resume engine.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from .state import RunState, RunStateStorage
from .models import RunStatus, PauseReason, ResumeData, PauseResult, ResumeResult
from .events import HILEvent, HILEventBus
from .exceptions import RunNotFoundError, RunNotPausedError, InvalidResumeDataError


class HILManager:
    """
    Central Human-in-the-Loop manager.
    
    Handles pause/resume logic for all three HIL patterns:
    1. Tool Approval - Pause before tool execution
    2. Tool Suspension - Pause mid-tool execution
    3. External Execution - Pause for external tool execution
    
    Example:
        manager = HILManager(storage)
        
        # Pause for approval
        result = await manager.pause_for_approval(run_id, tool_call)
        
        # Resume with approval
        await manager.resume(run_id, ResumeData(decision="approve"))
    """
    
    def __init__(self, storage: RunStateStorage):
        """
        Initialize HIL manager.
        
        Args:
            storage: Run state storage backend
        """
        self.storage = storage
        self.event_bus = HILEventBus()
        
    async def create_run(
        self,
        agent_id: str,
        thread_id: Optional[str] = None,
        execution_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new run.
        
        Args:
            agent_id: ID of the agent
            thread_id: Optional thread ID for conversation context
            execution_context: Execution context (messages, config, etc.)
            
        Returns:
            Run ID
        """
        run_id = f"run-{uuid.uuid4().hex[:12]}"
        
        state = RunState(
            run_id=run_id,
            agent_id=agent_id,
            thread_id=thread_id,
            status=RunStatus.RUNNING,
            execution_context=execution_context,
            created_at=datetime.now()
        )
        
        await self.storage.save(state)
        return run_id
        
    async def pause_for_approval(
        self,
        run_id: str,
        tool_call: Dict[str, Any]
    ) -> PauseResult:
        """
        Pause execution for tool approval.
        
        Args:
            run_id: Run ID
            tool_call: Tool call details (name, args, etc.)
            
        Returns:
            Pause result
        """
        # Get current state
        state = await self.storage.get(run_id)
        if not state:
            raise RunNotFoundError(f"Run {run_id} not found")
            
        # Update state to paused
        state.status = RunStatus.PAUSED_APPROVAL
        state.pause_reason = PauseReason.APPROVAL
        state.pause_data = {
            "tool_call": tool_call,
            "message": f"Approve execution of {tool_call.get('name')}?"
        }
        state.paused_at = datetime.now()
        
        await self.storage.save(state)
        
        # Emit event
        self.event_bus.emit(HILEvent(
            run_id=run_id,
            event_type="run.paused.approval",
            timestamp=datetime.now(),
            data={"tool_call": tool_call}
        ))
        
        return PauseResult(
            paused=True,
            run_id=run_id,
            reason=PauseReason.APPROVAL,
            message=state.pause_data["message"],
            pause_data=state.pause_data
        )
        
    async def pause_for_suspension(
        self,
        run_id: str,
        tool_call_id: str,
        suspend_data: Dict[str, Any]
    ) -> PauseResult:
        """
        Pause execution for mid-tool suspension.
        
        Args:
            run_id: Run ID
            tool_call_id: Tool call ID that was suspended
            suspend_data: Suspension data (message, schema, etc.)
            
        Returns:
            Pause result
        """
        state = await self.storage.get(run_id)
        if not state:
            raise RunNotFoundError(f"Run {run_id} not found")
            
        state.status = RunStatus.PAUSED_SUSPENSION
        state.pause_reason = PauseReason.SUSPENSION
        state.pause_data = {
            "tool_call_id": tool_call_id,
            **suspend_data
        }
        state.paused_at = datetime.now()
        
        await self.storage.save(state)
        
        # Emit event
        self.event_bus.emit(HILEvent(
            run_id=run_id,
            event_type="run.paused.suspension",
            timestamp=datetime.now(),
            data=suspend_data
        ))
        
        return PauseResult(
            paused=True,
            run_id=run_id,
            reason=PauseReason.SUSPENSION,
            message=suspend_data.get("message"),
            pause_data=state.pause_data
        )
        
    async def pause_for_external(
        self,
        run_id: str,
        tool_call: Dict[str, Any]
    ) -> PauseResult:
        """
        Pause execution for external tool execution.
        
        Args:
            run_id: Run ID
            tool_call: Tool call details
            
        Returns:
            Pause result
        """
        state = await self.storage.get(run_id)
        if not state:
            raise RunNotFoundError(f"Run {run_id} not found")
            
        state.status = RunStatus.PAUSED_EXTERNAL
        state.pause_reason = PauseReason.EXTERNAL
        state.pause_data = {
            "tool_call": tool_call,
            "message": f"Execute {tool_call.get('name')} externally and provide result"
        }
        state.paused_at = datetime.now()
        
        await self.storage.save(state)
        
        # Emit event
        self.event_bus.emit(HILEvent(
            run_id=run_id,
            event_type="run.paused.external",
            timestamp=datetime.now(),
            data={"tool_call": tool_call}
        ))
        
        return PauseResult(
            paused=True,
            run_id=run_id,
            reason=PauseReason.EXTERNAL,
            message=state.pause_data["message"],
            pause_data=state.pause_data
        )
        
    async def resume(
        self,
        run_id: str,
        resume_data: ResumeData
    ) -> ResumeResult:
        """
        Resume a paused run.
        
        Args:
            run_id: Run ID to resume
            resume_data: Resume data (decision, data, or result)
            
        Returns:
            Resume result with execution outcome
        """
        state = await self.storage.get(run_id)
        if not state:
            raise RunNotFoundError(f"Run {run_id} not found")
            
        # Check if run is paused
        if state.status not in [
            RunStatus.PAUSED_APPROVAL,
            RunStatus.PAUSED_SUSPENSION,
            RunStatus.PAUSED_EXTERNAL
        ]:
            raise RunNotPausedError(f"Run {run_id} is not paused (status: {state.status})")
            
        # Validate resume data matches pause reason
        if state.pause_reason == PauseReason.APPROVAL and not resume_data.decision:
            raise InvalidResumeDataError("Approval requires 'decision' field")
        elif state.pause_reason == PauseReason.SUSPENSION and not resume_data.data:
            raise InvalidResumeDataError("Suspension requires 'data' field")
        elif state.pause_reason == PauseReason.EXTERNAL and not resume_data.result:
            raise InvalidResumeDataError("External execution requires 'result' field")
            
        # Update state
        state.status = RunStatus.RUNNING
        state.resumed_at = datetime.now()
        await self.storage.save(state)
        
        # Emit event
        self.event_bus.emit(HILEvent(
            run_id=run_id,
            event_type="run.resumed",
            timestamp=datetime.now(),
            data={"pause_reason": state.pause_reason.value}
        ))
        
        return ResumeResult(
            resumed=True,
            run_id=run_id,
            result={
                "pause_reason": state.pause_reason.value,
                "pause_data": state.pause_data,
                "resume_data": resume_data.dict()
            }
        )
        
    async def complete_run(self, run_id: str) -> None:
        """
        Mark a run as completed.
        
        Args:
            run_id: Run ID to complete
        """
        await self.storage.update_status(
            run_id,
            RunStatus.COMPLETED,
            completed_at=datetime.now()
        )
        
        # Emit event
        self.event_bus.emit(HILEvent(
            run_id=run_id,
            event_type="run.completed",
            timestamp=datetime.now(),
            data={}
        ))
        
    async def fail_run(self, run_id: str, error: str) -> None:
        """
        Mark a run as failed.
        
        Args:
            run_id: Run ID to fail
            error: Error message
        """
        await self.storage.update_status(
            run_id,
            RunStatus.FAILED,
            completed_at=datetime.now()
        )
        
        # Emit event
        self.event_bus.emit(HILEvent(
            run_id=run_id,
            event_type="run.failed",
            timestamp=datetime.now(),
            data={"error": error}
        ))
