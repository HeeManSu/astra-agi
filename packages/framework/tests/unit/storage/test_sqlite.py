import pytest
import os
import aiosqlite
from framework.storage.databases.sqlite import SQLiteStorage

@pytest.mark.asyncio
async def test_sqlite_connect_disconnect(tmp_path):
    """Test connection and disconnection."""
    db_path = tmp_path / "test.db"
    storage = SQLiteStorage(str(db_path))
    
    assert storage._conn is None
    
    await storage.connect()
    assert storage._conn is not None
    assert isinstance(storage._conn, aiosqlite.Connection)
    
    await storage.disconnect()
    assert storage._conn is None

@pytest.mark.asyncio
async def test_sqlite_schema_initialization(tmp_path):
    """Test that schema is initialized on connect."""
    db_path = tmp_path / "test_schema.db"
    storage = SQLiteStorage(str(db_path))
    
    await storage.connect()
    
    # Check tables exist
    tables = await storage.fetch_all("SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [t['name'] for t in tables]
    
    assert "threads" in table_names
    assert "messages" in table_names
    
    await storage.disconnect()

@pytest.mark.asyncio
async def test_sqlite_crud_operations(tmp_path):
    """Test basic execute, fetch_one, fetch_all."""
    db_path = tmp_path / "test_crud.db"
    storage = SQLiteStorage(str(db_path))
    await storage.connect()
    
    # Create a test table
    await storage.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    
    # Insert
    await storage.execute("INSERT INTO test (name) VALUES (?)", ["item1"])
    await storage.execute("INSERT INTO test (name) VALUES (?)", ["item2"])
    
    # Fetch one
    row = await storage.fetch_one("SELECT * FROM test WHERE name = ?", ["item1"])
    assert row is not None
    assert row['name'] == "item1"
    
    # Fetch all
    rows = await storage.fetch_all("SELECT * FROM test ORDER BY id")
    assert len(rows) == 2
    assert rows[0]['name'] == "item1"
    assert rows[1]['name'] == "item2"
    
    await storage.disconnect()

@pytest.mark.asyncio
async def test_sqlite_file_uri_handling(tmp_path):
    """Test handling of file: URI prefix."""
    # Note: aiosqlite/sqlite3 handles file: URIs, but our class strips it for path checking
    # Let's verify it works
    db_path = tmp_path / "test_uri.db"
    uri = f"file:{db_path}"
    
    storage = SQLiteStorage(uri)
    # Check if path was stripped correctly for internal usage if needed, 
    # but the class stores it as db_path. 
    # The implementation: if db_path.startswith("file:"): db_path = db_path.replace("file:", "")
    
    assert storage.db_path == str(db_path)
    
    await storage.connect()
    assert os.path.exists(db_path)
    await storage.disconnect()
