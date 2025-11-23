from typing import List, Dict, Any, Optional, TYPE_CHECKING
from ..storage.models import Message

if TYPE_CHECKING:
    from ..storage.memory import AgentMemory

class ConversationManager:
    """
    Manages short-term conversation context with token-efficient strategies.
    
    Uses a sliding window approach to keep only recent messages in context,
    preventing token waste and staying within LLM context limits.
    
    Strategy Options:
    1. Sliding Window (default): Keep last N messages, drop older ones
    2. Sliding Window + Summary: Summarize messages beyond window, keep summary
    
    The summary approach is useful for long conversations where you want to
    retain some context from earlier in the conversation without using many tokens.
    """
    
    def __init__(self, max_messages: int = 10, enable_summary: bool = False):
        """
        Initialize conversation manager.
        
        Args:
            max_messages: Maximum messages to keep in context (default: 10)
                         10 messages = ~5 conversation turns (user + assistant)
                         Keeps token usage low while maintaining recent context
            enable_summary: Whether to summarize old messages (default: False)
                           When True, messages beyond max_messages are summarized
                           into a single system message for context retention
        """
        self.max_messages = max_messages
        self.enable_summary = enable_summary
        self._summary_cache: Dict[str, str] = {}  # Cache summaries by thread_id
        
    async def get_context(
        self, 
        thread_id: str, 
        memory: 'AgentMemory'
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation context for the current turn.
        
        This is the core optimization: instead of loading ALL history,
        we only load the last N messages. This:
        - Reduces token usage significantly
        - Stays within context window limits
        - Maintains recent conversation flow
        
        If enable_summary is True, also includes a summary of older messages.
        
        Args:
            thread_id: Thread ID to load context from
            memory: AgentMemory instance for storage access
            
        Returns:
            List of message dicts in format: [{"role": "user", "content": "..."}]
            If summary enabled, first message will be a system message with summary
        """
        # Load only recent messages (not full history!)
        recent_messages = await memory.get_history(
            thread_id, 
            limit=self.max_messages
        )
        
        context = []
        
        # Add summary if enabled and there are older messages
        if self.enable_summary and len(recent_messages) == self.max_messages:
            # Check if there are more messages beyond our window
            all_count = await memory.get_message_count(thread_id)
            if all_count > self.max_messages:
                # Generate or retrieve summary
                summary = await self._get_summary(thread_id, memory, all_count)
                if summary:
                    context.append({
                        "role": "system",
                        "content": f"Previous conversation summary: {summary}"
                    })
        
        # Add recent messages
        context.extend([
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ])
        
        return context
    
    async def _get_summary(
        self,
        thread_id: str,
        memory: 'AgentMemory',
        total_count: int
    ) -> Optional[str]:
        """
        Get or generate summary of old messages.
        
        For now, returns a simple count-based summary.
        Future: Could use LLM to generate actual summary.
        """
        # Simple summary for now (avoid LLM call to keep it fast)
        older_count = total_count - self.max_messages
        return f"This conversation has {older_count} earlier messages not shown here."
