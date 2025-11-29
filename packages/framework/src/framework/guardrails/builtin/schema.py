"""
Schema validation guardrails.

Supports both JSON Schema and Pydantic models.
Following pattern: Pydantic for developer API, JSON Schema for internal representation.
"""

import json
from typing import Any


try:
    import jsonschema  # type: ignore[import-untyped]

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

try:
    from pydantic import BaseModel, ValidationError

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

from ...middlewares import MiddlewareContext
from ..base import SchemaGuardrail
from ..exceptions import SchemaValidationError


class JSONSchemaGuardrail(SchemaGuardrail):
    """
    Validates output against JSON Schema.

    Example:
        ```python
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer", "minimum": 0}},
            "required": ["name"],
        }

        agent = Agent(
            name="StructuredAgent",
            model=Gemini("1.5-flash"),
            instructions="Respond with JSON",
            output_middlewares=[JSONSchemaGuardrail(schema=schema)],
        )
        ```
    """

    def __init__(self, schema: dict[str, Any]):
        """
        Initialize with JSON schema.

        Args:
            schema: JSON Schema dict

        Raises:
            ImportError: If jsonschema library not installed
        """
        if not HAS_JSONSCHEMA:
            raise ImportError(
                "jsonschema library required for JSONSchemaGuardrail. "
                "Install with: pip install jsonschema"
            )

        super().__init__(schema)

    async def validate_schema(
        self, output: str, schema: dict[str, Any], context: MiddlewareContext
    ) -> bool:
        """
        Validate output against JSON schema.

        Raises:
            SchemaValidationError: If validation fails
        """
        try:
            # Parse JSON
            data = json.loads(output)
        except json.JSONDecodeError as e:
            raise SchemaValidationError(f"Output is not valid JSON: {e}")

        try:
            # Validate against schema
            jsonschema.validate(data, schema)
            return True
        except jsonschema.ValidationError as e:
            raise SchemaValidationError(f"Schema validation failed: {e.message}")


class PydanticSchemaGuardrail(SchemaGuardrail):
    """
    Validates output against Pydantic model.

    This is the developer-facing API (easier to write and maintain).
    Internally converts to JSON Schema for validation.

    Example:
        ```python
        from pydantic import BaseModel


        class UserResponse(BaseModel):
            name: str
            age: int
            email: str


        agent = Agent(
            name="TypedAgent",
            model=Gemini("1.5-flash"),
            instructions="Respond with JSON",
            output_middlewares=[PydanticSchemaGuardrail(model=UserResponse)],
        )
        ```
    """

    def __init__(self, model: type[BaseModel]):
        """
        Initialize with Pydantic model.

        Args:
            model: Pydantic model class

        Raises:
            ImportError: If pydantic library not installed
        """
        if not HAS_PYDANTIC:
            raise ImportError(
                "pydantic library required for PydanticSchemaGuardrail. "
                "Install with: pip install pydantic"
            )

        self.model = model

        # Convert Pydantic model to JSON Schema (internal representation)
        # This follows pattern
        json_schema = model.model_json_schema()

        super().__init__(json_schema)

    async def validate_schema(
        self, output: str, schema: dict[str, Any], context: MiddlewareContext
    ) -> bool:
        """
        Validate output against Pydantic model.

        Raises:
            SchemaValidationError: If validation fails
        """
        try:
            # Parse JSON
            data = json.loads(output)
        except json.JSONDecodeError as e:
            raise SchemaValidationError(f"Output is not valid JSON: {e}")

        try:
            # Validate with Pydantic
            self.model(**data)
            return True
        except ValidationError as e:
            raise SchemaValidationError(f"Pydantic validation failed: {e}")


class OutputSchemaEnforcer(SchemaGuardrail):
    """
    Enforces output schema by extracting and validating JSON from text.

    This is more lenient - it extracts JSON from the output even if there's
    surrounding text, then validates it.

    Example:
        ```python
        schema = {"type": "object", "properties": {"answer": {"type": "string"}}}

        agent = Agent(
            name="FlexibleAgent",
            model=Gemini("1.5-flash"),
            output_middlewares=[OutputSchemaEnforcer(schema=schema)],
        )

        # Works even if output is: "Here's the answer: {\"answer\": \"42\"}"
        ```
    """

    def __init__(self, schema: dict[str, Any], extract_json: bool = True):
        """
        Initialize enforcer.

        Args:
            schema: JSON Schema dict
            extract_json: If True, extract JSON from surrounding text
        """
        if not HAS_JSONSCHEMA:
            raise ImportError(
                "jsonschema library required for OutputSchemaEnforcer. "
                "Install with: pip install jsonschema"
            )

        self.extract_json = extract_json
        super().__init__(schema)

    def _extract_json(self, text: str) -> str | None:
        """Extract JSON object or array from text."""
        # Find first { or [
        start_obj = text.find("{")
        start_arr = text.find("[")

        if start_obj == -1 and start_arr == -1:
            return None

        # Determine which comes first
        if start_obj == -1:
            start = start_arr
            end_char = "]"
        elif start_arr == -1:
            start = start_obj
            end_char = "}"
        else:
            start = min(start_obj, start_arr)
            end_char = "}" if start == start_obj else "]"

        # Find matching closing bracket
        depth = 0
        for i in range(start, len(text)):
            if text[i] in "{[":
                depth += 1
            elif text[i] in "]}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]

        return None

    async def validate_schema(
        self, output: str, schema: dict[str, Any], context: MiddlewareContext
    ) -> bool:
        """
        Validate output against schema, optionally extracting JSON first.

        Raises:
            SchemaValidationError: If validation fails
        """
        # Extract JSON if enabled
        if self.extract_json:
            json_str = self._extract_json(output)
            if not json_str:
                raise SchemaValidationError("No JSON object or array found in output")
        else:
            json_str = output

        try:
            # Parse JSON
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise SchemaValidationError(f"Output is not valid JSON: {e}")

        try:
            # Validate against schema
            jsonschema.validate(data, schema)
            return True
        except jsonschema.ValidationError as e:
            raise SchemaValidationError(f"Schema validation failed: {e.message}")
