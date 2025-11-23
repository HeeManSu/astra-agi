import pytest
from datetime import datetime
from framework.HIL.manager import HILManager
from framework.HIL.models import RunStatus, PauseReason, ResumeData
from framework.HIL.state import RunState, RunStateStorage
from framework.storage import SQLiteStorage


@pytest.mark.asyncio
async def test_hil_manager_create_run(tmp_path):
    """Test creating a new run."""
    storage = SQLiteStorage(str(tmp_path / "test.db"))
    await storage.connect()
    
    hil = HILManager(RunStateStorage(storage))
    
    run_id = await hil.create_run(
        agent_id="agent-1",
        thread_id="thread-1"
    )
    
    assert run_id.startswith("run-")
    
    # Verify run state was saved
    state = await hil.storage.get(run_id)
    assert state is not None
    assert state.agent_id == "agent-1"
    assert state.status == RunStatus.RUNNING
    
    await storage.disconnect()


@pytest.mark.asyncio
async def test_hil_pause_for_approval(tmp_path):
    """Test pausing for tool approval."""
    storage = SQLiteStorage(str(tmp_path / "test.db"))
    await storage.connect()
    
    hil = HILManager(RunStateStorage(storage))
    
    # Create run
    run_id = await hil.create_run(agent_id="agent-1")
    
    # Pause for approval
    tool_call = {"name": "delete_file", "args": {"path": "/tmp/test.txt"}}
    result = await hil.pause_for_approval(run_id, tool_call)
    
    assert result.paused is True
    assert result.reason == PauseReason.APPROVAL
    assert result.message is not None and "delete_file" in result.message
    
    # Verify state
    state = await hil.storage.get(run_id)
    assert state is not None
    assert state.status == RunStatus.PAUSED_APPROVAL
    assert state.pause_data is not None
    assert state.pause_data["tool_call"] == tool_call
    
    await storage.disconnect()


@pytest.mark.asyncio
async def test_hil_resume_approval(tmp_path):
    """Test resuming after approval."""
    storage = SQLiteStorage(str(tmp_path / "test.db"))
    await storage.connect()
    
    hil = HILManager(RunStateStorage(storage))
    
    # Create and pause run
    run_id = await hil.create_run(agent_id="agent-1")
    tool_call = {"name": "delete_file", "args": {"path": "/tmp/test.txt"}}
    await hil.pause_for_approval(run_id, tool_call)
    
    # Resume with approval
    resume_data = ResumeData(decision="approve")
    result = await hil.resume(run_id, resume_data)
    
    assert result.resumed is True
    
    # Verify state
    state = await hil.storage.get(run_id)
    assert state is not None
    assert state.status == RunStatus.RUNNING
    assert state.resumed_at is not None
    
    await storage.disconnect()


@pytest.mark.asyncio
async def test_hil_pause_for_external(tmp_path):
    """Test pausing for external execution."""
    storage = SQLiteStorage(str(tmp_path / "test.db"))
    await storage.connect()
    
    hil = HILManager(RunStateStorage(storage))
    
    # Create run
    run_id = await hil.create_run(agent_id="agent-1")
    
    # Pause for external execution
    tool_call = {"name": "run_shell", "args": {"command": "ls -la"}}
    result = await hil.pause_for_external(run_id, tool_call)
    
    assert result.paused is True
    assert result.reason == PauseReason.EXTERNAL
    
    # Verify state
    state = await hil.storage.get(run_id)
    assert state is not None
    assert state.status == RunStatus.PAUSED_EXTERNAL
    
    await storage.disconnect()


@pytest.mark.asyncio
async def test_hil_event_bus():
    """Test HIL event bus."""
    from framework.HIL.events import HILEventBus, HILEvent
    
    bus = HILEventBus()
    events_received = []
    
    def on_pause(event):
        events_received.append(event)
    
    bus.subscribe("run.paused.approval", on_pause)
    
    # Emit event
    event = HILEvent(
        run_id="run-123",
        event_type="run.paused.approval",
        timestamp=datetime.now(),
        data={"tool": "delete_file"}
    )
    bus.emit(event)
    
    assert len(events_received) == 1
    assert events_received[0].run_id == "run-123"
