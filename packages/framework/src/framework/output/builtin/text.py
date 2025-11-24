"""
Text-based output formats (PlainText, Markdown).
"""
from typing import Any, Dict, Optional

from ..formats import OutputFormat


class PlainTextFormat(OutputFormat):
    """
    Plain text output format (default).
    
    No special formatting or validation.
    
    Example:
        ```python
        agent = Agent(
            model=Gemini("1.5-flash"),
            output_format=OutputFormat.PLAIN_TEXT()
        )
        ```
    """
    
    def get_instructions(self) -> str:
        """No special instructions for plain text."""
        return ""
    
    def get_response_format(self) -> Optional[Dict[str, Any]]:
        """No special response format."""
        return None
    
    async def validate(self, output: str) -> bool:
        """Plain text is always valid."""
        return True
    
    async def parse(self, output: str) -> str:
        """Return output as-is."""
        return output


class MarkdownFormat(OutputFormat):
    """
    Markdown formatted output.
    
    Instructs the model to format response in markdown.
    
    Example:
        ```python
        agent = Agent(
            model=Gemini("1.5-flash"),
            output_format=OutputFormat.MARKDOWN()
        )
        ```
    """
    
    def get_instructions(self) -> str:
        """Instruct model to use markdown."""
        return "Format your response in markdown."
    
    def get_response_format(self) -> Optional[Dict[str, Any]]:
        """No special response format (handled via instructions)."""
        return None
    
    async def validate(self, output: str) -> bool:
        """Markdown is flexible, always valid."""
        return True
    
    async def parse(self, output: str) -> str:
        """Return markdown output as-is."""
        return output
