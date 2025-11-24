"""
Input validation middlewares.
"""
from typing import Dict, List

from ..base import InputMiddleware
from ..context import MiddlewareContext
from ..exceptions import InputValidationError


class InputLengthValidator(InputMiddleware):
    """
    Validates total input message length.
    
    Example:
        ```python
        agent = Agent(
            name="LimitedAgent",
            model=Gemini("1.5-flash"),
            input_middlewares=[InputLengthValidator(max_length=5000)]
        )
        ```
    """
    
    def __init__(self, max_length: int = 10000):
        """
        Initialize validator.
        
        Args:
            max_length: Maximum total characters across all messages
        """
        self.max_length = max_length
    
    async def process(
        self,
        messages: List[Dict[str, str]],
        context: MiddlewareContext
    ) -> List[Dict[str, str]]:
        """Validate message length."""
        total_length = sum(len(m.get('content', '')) for m in messages)
        
        if total_length > self.max_length:
            raise InputValidationError(
                f"Input too long: {total_length} characters exceeds "
                f"maximum of {self.max_length}"
            )
        
        return messages


class EmptyInputValidator(InputMiddleware):
    """
    Validates that input is not empty.
    
    Example:
        ```python
        agent = Agent(
            name="ValidatedAgent",
            model=Gemini("1.5-flash"),
            input_middlewares=[EmptyInputValidator()]
        )
        ```
    """
    
    async def process(
        self,
        messages: List[Dict[str, str]],
        context: MiddlewareContext
    ) -> List[Dict[str, str]]:
        """Validate input is not empty."""
        if not messages:
            raise InputValidationError("Input messages cannot be empty")
        
        # Check if all messages have content
        for msg in messages:
            content = msg.get('content', '').strip()
            if not content:
                raise InputValidationError(
                    f"Message with role '{msg.get('role', 'unknown')}' "
                    f"has empty content"
                )
        
        return messages
