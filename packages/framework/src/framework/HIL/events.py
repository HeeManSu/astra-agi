"""
HIL event system for pause/resume notifications.
"""

from typing import Dict, Any, Callable, List
from datetime import datetime
from pydantic import BaseModel


class HILEvent(BaseModel):
    """Base HIL event."""
    run_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any] = {}


class HILEventBus:
    """
    Simple in-memory event bus for HIL events.
    
    Allows subscribing to HIL events (pause, resume, etc.) and
    emitting events when they occur.
    
    Example:
        bus = HILEventBus()
        
        def on_pause(event: HILEvent):
            print(f"Run {event.run_id} paused: {event.data}")
        
        bus.subscribe("run.paused.approval", on_pause)
        bus.emit(HILEvent(
            run_id="123",
            event_type="run.paused.approval",
            timestamp=datetime.now(),
            data={"tool": "delete_file"}
        ))
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        
    def subscribe(self, event_type: str, callback: Callable[[HILEvent], None]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event is emitted
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        
    def emit(self, event: HILEvent) -> None:
        """
        Emit an event to all subscribers.
        
        Args:
            event: Event to emit
        """
        if event.event_type in self._subscribers:
            for callback in self._subscribers[event.event_type]:
                try:
                    callback(event)
                except Exception as e:
                    # Log error but don't fail
                    print(f"Error in event callback: {e}")
