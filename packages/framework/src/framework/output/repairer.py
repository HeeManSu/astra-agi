"""
Output repairer with LLM retry logic.
"""
import json
import re
from typing import Any, Dict, List

from .formats import OutputFormat
from .builtin.json import JSONSchemaFormat
from .builtin.pydantic import PydanticFormat
from .exceptions import OutputRepairError


class OutputRepairer:
    """
    Repairs malformed output with automatic retry.
    
    Strategy:
    1. Try to fix JSON syntax
    2. Re-validate
    3. If still invalid, ask LLM to repair
    4. Retry up to max_retries times
    
    Example:
        ```python
        repairer = OutputRepairer(
            model=model,
            output_format=OutputFormat.JSON(schema={...}),
            max_retries=2
        )
        
        repaired = await repairer.repair(malformed_output, original_messages)
        ```
    """
    
    def __init__(
        self,
        model: Any,
        output_format: OutputFormat,
        max_retries: int = 2
    ):
        """
        Initialize repairer.
        
        Args:
            model: Model instance to use for repair
            output_format: Output format to repair to
            max_retries: Maximum number of repair attempts
        """
        self.model = model
        self.output_format = output_format
        self.max_retries = max_retries
    
    async def repair(
        self,
        output: str,
        original_messages: List[Dict[str, str]]
    ) -> str:
        """
        Attempt to repair malformed output.
        
        Args:
            output: Malformed output
            original_messages: Original conversation messages
            
        Returns:
            Repaired output
            
        Raises:
            OutputRepairError: If repair fails after max_retries
        """
        # Try JSON repair first for JSON-based formats
        if isinstance(self.output_format, (JSONSchemaFormat, PydanticFormat)):
            repaired = self._try_json_repair(output)
            if await self.output_format.validate(repaired):
                return repaired
        
        # Ask LLM to repair
        for attempt in range(self.max_retries):
            repair_messages = original_messages + [
                {"role": "assistant", "content": output},
                {
                    "role": "user",
                    "content": (
                        f"Your response was malformed. Please fix it to match the required format.\n\n"
                        f"Requirements: {self.output_format.get_instructions()}\n\n"
                        f"Please provide ONLY the corrected response, nothing else."
                    )
                }
            ]
            
            # Call model to repair
            response = await self.model.invoke(repair_messages)
            repaired_output = response.content
            
            # Validate repaired output
            if await self.output_format.validate(repaired_output):
                return repaired_output
        
        raise OutputRepairError(
            f"Failed to repair output after {self.max_retries} attempts. "
            f"Last output: {output[:200]}..."
        )
    
    def _try_json_repair(self, output: str) -> str:
        """
        Try to fix common JSON issues.
        
        Args:
            output: Potentially malformed JSON
            
        Returns:
            Repaired JSON string
        """
        # Extract JSON from markdown code blocks
        if "```json" in output.lower():
            match = re.search(r'```json\s*(.*?)\s*```', output, re.DOTALL | re.IGNORECASE)
            if match:
                output = match.group(1).strip()
        elif "```" in output:
            match = re.search(r'```\s*(.*?)\s*```', output, re.DOTALL)
            if match:
                potential_json = match.group(1).strip()
                # Check if it looks like JSON
                if potential_json.startswith(('{', '[')):
                    output = potential_json
        
        # Try to parse and re-serialize (fixes formatting issues)
        try:
            data = json.loads(output)
            return json.dumps(data)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON object or array from surrounding text
        json_match = self._extract_json_from_text(output)
        if json_match:
            try:
                data = json.loads(json_match)
                return json.dumps(data)
            except json.JSONDecodeError:
                pass
        
        return output
    
    def _extract_json_from_text(self, text: str) -> str:
        """
        Extract JSON object or array from surrounding text.
        
        Args:
            text: Text potentially containing JSON
            
        Returns:
            Extracted JSON string or original text
        """
        # Find first { or [
        start_obj = text.find('{')
        start_arr = text.find('[')
        
        if start_obj == -1 and start_arr == -1:
            return text
        
        # Determine which comes first
        if start_obj == -1:
            start = start_arr
            open_char = '['
            close_char = ']'
        elif start_arr == -1:
            start = start_obj
            open_char = '{'
            close_char = '}'
        else:
            start = min(start_obj, start_arr)
            open_char = '{' if start == start_obj else '['
            close_char = '}' if start == start_obj else ']'
        
        # Find matching closing bracket
        depth = 0
        for i in range(start, len(text)):
            if text[i] == open_char:
                depth += 1
            elif text[i] == close_char:
                depth -= 1
                if depth == 0:
                    return text[start:i+1]
        
        return text
