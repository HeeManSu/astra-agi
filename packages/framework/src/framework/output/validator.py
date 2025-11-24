"""
Output validator.
"""
from .formats import OutputFormat


class OutputValidator:
    """
    Validates output against format specification.
    
    Example:
        ```python
        validator = OutputValidator(output_format=OutputFormat.JSON(schema={...}))
        is_valid = await validator.validate(output)
        ```
    """
    
    def __init__(self, output_format: OutputFormat):
        """
        Initialize validator.
        
        Args:
            output_format: Output format to validate against
        """
        self.output_format = output_format
    
    async def validate(self, output: str) -> bool:
        """
        Validate output against format.
        
        Args:
            output: Model output string
            
        Returns:
            True if valid, False otherwise
        """
        return await self.output_format.validate(output)
