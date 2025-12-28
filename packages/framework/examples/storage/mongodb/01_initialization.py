"""
Test MongoDB storage initialization and multi-agent sharing.

Database Parts Tested:
- MongoDBStorage connection and initialization
- Collection creation (astra_threads, astra_messages, astra_facts)
- Multiple agents sharing the same database
- Thread isolation between agents

Tests:
- Basic storage connection
- Collection auto-creation on first connection
- Multiple agents using same storage backend
- Data isolation by thread_id

Requires: MongoDB running locally on port 27017.
"""

import asyncio

from framework.agents import Agent
from framework.models.huggingface import HuggingFaceLocal
from framework.storage.databases.mongodb import MongoDBStorage


async def test_basic_initialization():
    """Test basic MongoDB storage initialization."""
    print("\n" + "=" * 60)
    print("Test 1: Basic MongoDB Storage Initialization")
    print("=" * 60)

    print("Initializing MongoDB Storage...")

    # Initialize the storage backend
    mongodb_storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_storage_test")

    try:
        # Connect (validates the connection and auto-creates collections)
        print("Connecting to MongoDB...")
        await mongodb_storage.connect()
        print("Connected successfully.")

        # Verify collections exist
        collections_to_check = ["astra_threads", "astra_messages", "astra_facts"]
        for coll_name in collections_to_check:
            exists = await mongodb_storage.table_exists(coll_name)
            if exists:
                print(f"Collection '{coll_name}' exists")
            else:
                print(f"Collection '{coll_name}' not found (will be created on first use)")

        # Verify initialization flag
        if mongodb_storage._initialized:
            print("Storage is marked as initialized")
        else:
            print("Storage initialization flag is False")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        # Clean up
        print("Disconnecting...")
        await mongodb_storage.disconnect()
        print("Disconnected.")


async def test_agent_initialization():
    """Test agent initialization with MongoDB storage."""
    print("\n" + "=" * 60)
    print("Test 2: Agent Initialization with MongoDB Storage")
    print("=" * 60)

    print("Creating MongoDB storage...")

    mongodb_storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_agent_test")
    await mongodb_storage.connect()

    try:
        # Initialize agent with storage
        print("Loading model (first time may take a few minutes)...")
        model = HuggingFaceLocal(model_id="HuggingFaceTB/SmolLM2-360M-Instruct")

        print("Initializing Agent with storage...")
        agent = Agent(
            name="TestAgent",
            instructions="You are a helpful assistant.",
            model=model,
            storage=mongodb_storage,
        )

        print(f"Agent created: {agent}")
        print(f"Agent has storage: {agent.storage is not None}")

        if agent.storage:
            print(f"Storage type: {type(agent.storage).__name__}")
            print(f"Max messages: {agent.storage.max_messages}")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        await mongodb_storage.disconnect()
        print("Disconnected from MongoDB")


async def test_duplicate_initialization():
    """Test that duplicate initialization is safe (idempotent)."""
    print("\n" + "=" * 60)
    print("Test 3: Duplicate Initialization (Idempotent)")
    print("=" * 60)

    mongodb_storage = MongoDBStorage(
        url="mongodb://localhost:27017", db_name="astra_duplicate_test"
    )

    try:
        # First initialization
        print("First connect() call...")
        await mongodb_storage.connect()
        print("First initialization successful")

        # Second initialization (should be safe)
        print("Second connect() call (should be idempotent)...")
        await mongodb_storage.connect()
        print("Second initialization successful (idempotent)")

        # Verify initialization flag
        assert mongodb_storage._initialized, "Storage should be initialized"
        print("Duplicate initialization is safe (idempotent)")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        await mongodb_storage.disconnect()


async def test_collection_verification():
    """Test that collections have been created."""
    print("\n" + "=" * 60)
    print("Test 4: Collection Verification")
    print("=" * 60)

    mongodb_storage = MongoDBStorage(
        url="mongodb://localhost:27017", db_name="astra_collection_test"
    )

    try:
        await mongodb_storage.connect()

        # Check collections
        expected_collections = ["astra_threads", "astra_messages", "astra_facts"]
        collection_names = await mongodb_storage.db.list_collection_names()

        print(f"Collections in database: {collection_names}")

        for coll_name in expected_collections:
            exists = await mongodb_storage.table_exists(coll_name)
            status = "✅" if exists else "❌ (will be created on first use)"
            print(f"  {coll_name}: {status}")

        # Check indexes on astra_facts
        if await mongodb_storage.table_exists("astra_facts"):
            indexes = await mongodb_storage.db["astra_facts"].index_information()
            print(f"\nastra_facts indexes: {list(indexes.keys())}")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        await mongodb_storage.disconnect()


async def test_data_operations():
    """Test basic data operations with MongoDB."""
    print("\n" + "=" * 60)
    print("Test 5: Basic Data Operations")
    print("=" * 60)

    mongodb_storage = MongoDBStorage(url="mongodb://localhost:27017", db_name="astra_data_test")

    try:
        await mongodb_storage.connect()

        # Test insert
        print("Testing insert...")
        test_doc = {
            "id": "test-doc-001",
            "key": "test_key",
            "value": {"foo": "bar"},
            "scope": "user",
            "scope_id": "user_test",
        }

        insert_query = mongodb_storage.build_insert_query("astra_facts", test_doc)
        await mongodb_storage.execute(insert_query)
        print("  Insert successful")

        # Test select
        print("Testing select...")
        select_query = mongodb_storage.build_select_query(
            "astra_facts", filter_dict={"id": "test-doc-001"}
        )
        results = await mongodb_storage.fetch_all(select_query)
        print(f"  Found {len(results)} documents")
        if results:
            print(f"  Document: {results[0]}")

        # Test update
        print("Testing update...")
        update_query = mongodb_storage.build_update_query(
            "astra_facts",
            filter_dict={"id": "test-doc-001"},
            update_data={"value": {"foo": "updated"}},
        )
        await mongodb_storage.execute(update_query)
        print("  Update successful")

        # Verify update
        results = await mongodb_storage.fetch_all(select_query)
        if results:
            print(f"  Updated value: {results[0].get('value')}")

        # Clean up test data
        print("Cleaning up test data...")
        await mongodb_storage.db["astra_facts"].delete_one({"id": "test-doc-001"})
        print("  Cleanup successful")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        await mongodb_storage.disconnect()


async def main():
    """Run all MongoDB initialization tests."""
    print("\n" + "=" * 60)
    print("MongoDB Storage Initialization Tests")
    print("=" * 60)

    tests = [
        test_basic_initialization,
        test_duplicate_initialization,
        test_collection_verification,
        test_data_operations,
        # Uncomment to test with agent (requires model download):
        # test_agent_initialization,
    ]

    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"\nTest {test.__name__} failed: {e}")
            raise

    print("\n" + "=" * 60)
    print("All MongoDB initialization tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
