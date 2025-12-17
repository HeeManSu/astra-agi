"""
Test storage initialization and multi-agent sharing.

Database Parts Tested:
- LibSQLStorage connection and initialization
- Table creation (astra_threads, astra_messages)
- Schema version tracking
- Multiple agents sharing the same database
- Thread isolation between agents

Tests:
- Basic storage connection
- Table auto-creation on first connection
- Schema version upsert
- Multiple agents using same storage backend
- Data isolation by thread_id
- Edge cases (duplicate initialization, invalid URLs, etc.)
"""

import asyncio
import os
from pathlib import Path

from framework.agents import Agent
from framework.models import Gemini
from framework.storage.databases.libsql import LibSQLStorage
from sqlalchemy import text


async def test_basic_initialization():
    """Test basic storage initialization."""
    print("\n" + "=" * 60)
    print("Test 1: Basic Storage Initialization")
    print("=" * 60)

    db_file = "./test_astra_init.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    # Remove existing DB file if it exists
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"Removed existing DB file: {db_file}")

    print(f"Initializing LibSQL Storage with URL: {db_url}")

    # Initialize the storage backend
    libsql_storage = LibSQLStorage(url=db_url, echo=False)

    try:
        # Connect (validates the engine and auto-creates tables)
        print("Connecting to database...")
        await libsql_storage.connect()
        print("Connected successfully.")

        # Verify DB file was created
        if os.path.exists(db_file):
            file_size = os.path.getsize(db_file)
            print(f"Database file created: {db_file} ({file_size} bytes)")
        else:
            print(f"Database file not found: {db_file}")

        # Verify tables exist
        tables_to_check = ["astra_threads", "astra_messages"]
        for table_name in tables_to_check:
            exists = await libsql_storage.table_exists(table_name)
            if exists:
                print(f"Table '{table_name}' exists")
            else:
                print(f"Table '{table_name}' not found")

        # Verify initialization flag
        if libsql_storage._initialized:
            print("Storage is marked as initialized")
        else:
            print("Storage initialization flag is False")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        # Clean up
        print("Disconnecting...")
        await libsql_storage.disconnect()
        print("Disconnected.")

        # Clean up DB file
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Cleaned up DB file: {db_file}")


async def test_agent_initialization():
    """Test agent initialization with storage."""
    print("\n" + "=" * 60)
    print("Test 2: Agent Initialization with Storage")
    print("=" * 60)

    db_file = "./test_astra_agent.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    print(f"Creating storage: {db_url}")

    libsql_storage = LibSQLStorage(url=db_url, echo=False)
    await libsql_storage.connect()

    try:
        # Initialize agent with storage
        print("Initializing Agent with storage...")
        agent = Agent(
            name="TestAgent",
            instructions="You are a helpful assistant.",
            model=Gemini("gemini-2.5-flash"),
            storage=libsql_storage,
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
        await libsql_storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Cleaned up DB file: {db_file}")


async def test_duplicate_initialization():
    """Test that duplicate initialization is safe (idempotent)."""
    print("\n" + "=" * 60)
    print("Test 3: Duplicate Initialization (Idempotent)")
    print("=" * 60)

    db_file = "./test_astra_duplicate.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    libsql_storage = LibSQLStorage(url=db_url, echo=False)

    try:
        # First initialization
        print("First connect() call...")
        await libsql_storage.connect()
        print("First initialization successful")

        # Second initialization (should be safe)
        print("Second connect() call (should be idempotent)...")
        await libsql_storage.connect()
        print("Second initialization successful (idempotent)")

        # Verify tables still exist
        tables = ["astra_threads", "astra_messages"]
        for table_name in tables:
            exists = await libsql_storage.table_exists(table_name)
            assert exists, f"Table {table_name} should exist after duplicate init"
        print("All tables still exist after duplicate initialization")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        await libsql_storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)


async def test_invalid_url():
    """Test error handling for invalid database URL."""
    print("\n" + "=" * 60)
    print("Test 4: Invalid Database URL")
    print("=" * 60)

    # Invalid URL (missing protocol)
    invalid_url = "invalid:///path/to/db.db"

    try:
        libsql_storage = LibSQLStorage(url=invalid_url, echo=False)
        print(f"Created storage with invalid URL: {invalid_url}")

        # This might fail during connect or during engine creation
        try:
            await libsql_storage.connect()
            print("Connection succeeded (unexpected)")
        except Exception as e:
            print(f"Expected error caught: {type(e).__name__}: {e}")

    except Exception as e:
        print(f"Error caught early: {type(e).__name__}: {e}")


async def test_memory_directory():
    """Test that database file is created in memory directory."""
    print("\n" + "=" * 60)
    print("Test 5: Database File Location")
    print("=" * 60)

    # Create a test directory
    test_dir = Path("./test_storage_dir")
    test_dir.mkdir(exist_ok=True)

    db_file = test_dir / "nested_db.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if db_file.exists():
        db_file.unlink()

    libsql_storage = LibSQLStorage(url=db_url, echo=False)

    try:
        await libsql_storage.connect()
        print(f"Connected to: {db_url}")

        # Check if file exists
        if db_file.exists():
            print(f"Database file created at: {db_file.absolute()}")
            print(f"File size: {db_file.stat().st_size} bytes")
        else:
            print(f"Database file not found at: {db_file.absolute()}")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        await libsql_storage.disconnect()
        if db_file.exists():
            db_file.unlink()
        if test_dir.exists():
            test_dir.rmdir()
        print("Cleaned up test directory")


async def test_table_schema_verification():
    """Test that tables have correct schema."""
    print("\n" + "=" * 60)
    print("Test 6: Table Schema Verification")
    print("=" * 60)

    db_file = "./test_astra_schema.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    libsql_storage = LibSQLStorage(url=db_url, echo=False)

    try:
        await libsql_storage.connect()

        # Check that astra_threads has expected columns

        async with libsql_storage.engine.connect() as conn:
            # Get table info for astra_threads
            stmt = text("PRAGMA table_info(astra_threads)")
            result = await conn.execute(stmt)
            columns = result.fetchall()

            print(f"astra_threads has {len(columns)} columns:")
            expected_columns = [
                "id",
                "resource_id",
                "title",
                "metadata",
                "is_archived",
                "created_at",
                "updated_at",
            ]
            found_columns = [col[1] for col in columns]  # Column name is at index 1

            for col in expected_columns:
                if col in found_columns:
                    print(f"  Column '{col}' exists")
                else:
                    print(f"  Column '{col}' missing")

            # Check astra_messages
            stmt = text("PRAGMA table_info(astra_messages)")
            result = await conn.execute(stmt)
            columns = result.fetchall()

            print(f"\nastra_messages has {len(columns)} columns:")
            expected_msg_columns = [
                "id",
                "thread_id",
                "role",
                "content",
                "metadata",
                "sequence",
                "created_at",
            ]
            found_msg_columns = [col[1] for col in columns]

            for col in expected_msg_columns:
                if col in found_msg_columns:
                    print(f"  Column '{col}' exists")
                else:
                    print(f"  Column '{col}' missing")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        await libsql_storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)


async def test_auto_connect():
    """Test that storage auto-connects when used without explicit connect()."""
    print("\n" + "=" * 60)
    print("Test 7: Auto-Connect Functionality")
    print("=" * 60)

    db_file = "./test_astra_autoconnect.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    print("Creating storage WITHOUT calling connect()...")
    libsql_storage = LibSQLStorage(url=db_url, echo=False)

    try:
        # Verify not initialized yet
        assert not libsql_storage._initialized, "Storage should not be initialized yet"

        # Create agent with storage
        print("Creating agent with storage...")
        agent = Agent(
            name="AutoConnectAgent",
            instructions="You are helpful.",
            model=Gemini("gemini-2.5-flash"),
            storage=libsql_storage,
        )

        print(f"Agent created: {agent}")
        print(f"Storage initialized: {libsql_storage._initialized}")

        # Now use storage
        print("\nUsing storage (should auto-connect)...")
        thread_id = "test-thread-123"
        if agent.storage is None:
            raise RuntimeError("Agent storage should be initialized")
        await agent.storage.add_message(thread_id=thread_id, role="user", content="Hello")

        # Verify auto-connect happened
        assert libsql_storage._initialized, "Storage should be auto-initialized after use"
        print("Storage auto-connected successfully!")

        # Verify tables exist
        tables = ["astra_threads", "astra_messages"]
        for table_name in tables:
            exists = await libsql_storage.table_exists(table_name)
            assert exists, f"Table {table_name} should exist after auto-connect"
            print(f"Table '{table_name}' exists")

        # Verify DB file was created
        if os.path.exists(db_file):
            print(f"Database file created: {db_file}")
        else:
            print(f"Database file not found: {db_file}")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        if agent.storage:
            await agent.storage.stop()  # Stop queue manager
        await libsql_storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Cleaned up DB file: {db_file}")


async def test_multiple_agents_shared_storage():
    """Test multiple agents sharing the same storage instance."""
    print("\n" + "=" * 60)
    print("Test 8: Multiple Agents Sharing Storage")
    print("=" * 60)

    db_file = "./test_astra_shared.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    if os.path.exists(db_file):
        os.remove(db_file)

    # Create ONE storage instance
    print("Creating shared storage instance...")
    shared_storage = LibSQLStorage(url=db_url, echo=False)

    try:
        # Create multiple agents with the SAME storage
        print("\nCreating 3 agents with shared storage...")
        agents = []
        for i in range(3):
            agent = Agent(
                name=f"Agent{i + 1}",
                instructions=f"You are agent {i + 1}.",
                model=Gemini("gemini-2.5-flash"),
                storage=shared_storage,  # Same storage instance
            )
            agents.append(agent)
            print(f"  Created {agent.name} (id: {agent.id})")

        # Verify all agents share the same storage instance
        storage_ids = [id(agent.storage.storage) for agent in agents if agent.storage]
        assert len(set(storage_ids)) == 1, "All agents should share the same storage instance"
        print("All agents share the same storage instance")

        # Use first agent (should auto-connect)
        print("\nUsing first agent (should auto-connect storage)...")
        thread_id_1 = "thread-agent1"
        await agents[0].storage.add_message(
            thread_id=thread_id_1, role="user", content="Hello from Agent1"
        )

        # Verify storage is initialized
        assert shared_storage._initialized, "Storage should be initialized after first use"
        print("Storage initialized after first agent use")

        # Use other agents (should use same tables, no re-initialization)
        print("\nUsing other agents (should use same tables)...")
        thread_id_2 = "thread-agent2"
        thread_id_3 = "thread-agent3"

        await agents[1].storage.add_message(
            thread_id=thread_id_2, role="user", content="Hello from Agent2"
        )
        await agents[2].storage.add_message(
            thread_id=thread_id_3, role="user", content="Hello from Agent3"
        )

        # Wait for queue to flush
        await asyncio.sleep(1)

        # Verify all messages are in the SAME database
        print("\nVerifying data storage...")
        history_1 = await agents[0].storage.get_history(thread_id_1)
        history_2 = await agents[1].storage.get_history(thread_id_2)
        history_3 = await agents[2].storage.get_history(thread_id_3)

        print(f"  Agent1 thread messages: {len(history_1)}")
        print(f"  Agent2 thread messages: {len(history_2)}")
        print(f"  Agent3 thread messages: {len(history_3)}")

        # All should have messages
        assert len(history_1) > 0, "Agent1 should have messages"
        assert len(history_2) > 0, "Agent2 should have messages"
        assert len(history_3) > 0, "Agent3 should have messages"

        # Verify they're stored in the same tables (not separate tables per agent)
        # Check that we can query all threads from any agent
        all_threads = await agents[0].storage.threads.get_all(limit=10)
        thread_ids = [t.id for t in all_threads]

        assert thread_id_1 in thread_ids, "Thread1 should be accessible"
        assert thread_id_2 in thread_ids, "Thread2 should be accessible"
        assert thread_id_3 in thread_ids, "Thread3 should be accessible"

        print("All agents store data in the same tables")
        print("Data is separated by thread_id, not by agent")
        print("All agents can access all threads")

        # Verify only ONE set of tables exists (not per agent)
        tables = ["astra_threads", "astra_messages"]
        for table_name in tables:
            exists = await shared_storage.table_exists(table_name)
            assert exists, f"Table {table_name} should exist"
        print("Only one set of tables exists (shared across all agents)")

        # Verify DB file size (should contain all data)
        if os.path.exists(db_file):
            file_size = os.path.getsize(db_file)
            print(f"Database file: {db_file} ({file_size} bytes)")

    except Exception as e:
        print(f"Error occurred: {e}")
        raise
    finally:
        # Clean up all agents' storage
        for agent in agents:
            if agent.storage:
                await agent.storage.stop()
        await shared_storage.disconnect()
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"Cleaned up DB file: {db_file}")


async def main():
    """Run all initialization tests."""
    print("\n" + "=" * 60)
    print("Storage Initialization Tests")
    print("=" * 60)

    tests = [
        test_basic_initialization,
        test_agent_initialization,
        test_duplicate_initialization,
        test_invalid_url,
        test_memory_directory,
        test_table_schema_verification,
        test_auto_connect,
        test_multiple_agents_shared_storage,
    ]

    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"\nTest {test.__name__} failed: {e}")
            raise

    print("\n" + "=" * 60)
    print("All initialization tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
