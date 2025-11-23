import pytest
import json
import uuid
from datetime import datetime
from framework.storage.databases.sqlite import SQLiteStorage
from framework.storage.stores.thread import ThreadStore
from framework.storage.stores.message import MessageStore
from framework.storage.models import Thread, Message

@pytest.fixture
async def storage(tmp_path):
    """Fixture for initialized storage."""
    db_path = tmp_path / "test_stores.db"
    s = SQLiteStorage(str(db_path))
    await s.connect()
    yield s
    await s.disconnect()

@pytest.mark.asyncio
async def test_thread_store_crud(storage):
    """Test ThreadStore Create, Read, Update."""
    store = ThreadStore(storage)
    
    # Create
    thread_id = str(uuid.uuid4())
    thread = Thread(id=thread_id, title="Test Thread", metadata={"key": "value"})
    await store.create(thread)
    
    # Read
    fetched = await store.get(thread_id)
    assert fetched is not None
    assert fetched.id == thread_id
    assert fetched.title == "Test Thread"
    assert fetched.metadata == {"key": "value"}
    
    # Update
    await store.update(thread_id, title="Updated Title", metadata={"new": "data"})
    updated = await store.get(thread_id)
    assert updated is not None
    assert updated.title == "Updated Title"
    assert updated.metadata == {"new": "data"} # Replaces metadata based on implementation? 
    # Implementation: updates.append("metadata = ?") -> params.append(json.dumps(metadata))
    # So it replaces.
    
    # Get non-existent
    assert await store.get("non-existent") is None

@pytest.mark.asyncio
async def test_message_store_crud(storage):
    """Test MessageStore Add, Get."""
    # Need a thread first due to foreign key
    thread_store = ThreadStore(storage)
    thread_id = str(uuid.uuid4())
    await thread_store.create(Thread(id=thread_id))
    
    store = MessageStore(storage)
    
    # Add single
    msg1 = Message(id=str(uuid.uuid4()), thread_id=thread_id, role="user", content="Hello")
    await store.add(msg1)
    
    # Add many
    msg2 = Message(id=str(uuid.uuid4()), thread_id=thread_id, role="assistant", content="Hi")
    msg3 = Message(id=str(uuid.uuid4()), thread_id=thread_id, role="user", content="How are you?")
    await store.add_many([msg2, msg3])
    
    # Get by thread
    messages = await store.get_by_thread(thread_id)
    assert len(messages) == 3
    # Ordered by created_at (default now())
    # Since execution is fast, order might be tricky if timestamps are identical.
    # But usually insertion order is preserved if timestamps are equal in some DBs or if we wait.
    # Let's just check content presence.
    contents = [m.content for m in messages]
    assert "Hello" in contents
    assert "Hi" in contents
    assert "How are you?" in contents
    
    # Pagination
    page1 = await store.get_by_thread(thread_id, limit=2, offset=0)
    assert len(page1) == 2
    
    page2 = await store.get_by_thread(thread_id, limit=2, offset=2)
    assert len(page2) == 1

@pytest.mark.asyncio
async def test_message_store_foreign_key_constraint(storage):
    """Test that adding message to non-existent thread fails."""
    store = MessageStore(storage)
    msg = Message(id="1", thread_id="non-existent", role="user", content="Fail")
    
    with pytest.raises(Exception): # sqlite3.IntegrityError wrapped or direct
        await store.add(msg)
