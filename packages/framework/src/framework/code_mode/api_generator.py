"""
Virtual API Generator for Code Execution Mode.

This module generates compact API surface descriptions for LLM prompts.
The API surface shows available tools grouped by module in a readable format.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from framework.code_mode.tool_registry import ToolRegistry, ToolSpec


class VirtualAPIGenerator:
    """Generates API surface descriptions from tool registry.

    This class converts ToolRegistry contents into compact, readable
    API surface descriptions that can be included in LLM prompts.
    """

    def generate_compact_api_surface(self, registry: ToolRegistry) -> str:
        """Generate compact API surface for LLM prompt.

        Format:
            You can call these Python functions using import from astra_api.

            Module: {module_name}

            - {function_name}({params}) -> {return_type}

                {description}

        Args:
            registry: ToolRegistry instance with populated tools

        Returns:
            Formatted API surface string
        """
        grouped = registry.get_specs_grouped_by_module()

        if not grouped:
            return "No tools available."

        # Build API surface
        lines = [
            "You can call these Python functions using import from astra_api.",
            "",  # Empty line
        ]

        # Sort modules alphabetically for consistency
        sorted_modules = sorted(grouped.keys())

        for module_name in sorted_modules:
            tools = grouped[module_name]

            # Skip empty modules
            if not tools:
                continue

            # Add module header
            lines.append(f"Module: {module_name}")
            lines.append("")  # Empty line

            # Sort tools by name for consistency
            sorted_tools = sorted(tools, key=lambda t: t.name)

            for tool_spec in sorted_tools:
                # Extract function signature
                function_name, params_str, return_type = self._extract_function_signature(tool_spec)

                # Add function signature
                lines.append(f"- {function_name}({params_str}) -> {return_type}")
                lines.append("")  # Empty line

                # Add description (indented)
                description = tool_spec.description.strip()
                if description:
                    # Indent description with 4 spaces
                    lines.append(f"    {description}")
                else:
                    # Fallback for tools without description
                    lines.append("    No description available.")

                lines.append("")  # Empty line between tools

        return "\n".join(lines)

    def _extract_function_signature(self, tool_spec: ToolSpec) -> tuple[str, str, str]:
        """Extract function signature components from ToolSpec.

        Args:
            tool_spec: ToolSpec instance

        Returns:
            Tuple of (function_name, params_string, return_type)
        """
        # Extract function name (remove module prefix if present)
        function_name = self._extract_function_name(tool_spec.name)

        # Extract parameters
        params_str = self._extract_parameters(tool_spec.parameters)

        # Determine return type (default to dict for most tools)
        return_type = self._infer_return_type(tool_spec.parameters)

        return (function_name, params_str, return_type)

    def _extract_function_name(self, tool_name: str) -> str:
        """Extract function name from full tool name.

        If tool name contains dots (e.g., 'crm.get_user'), extract
        the part after the last dot. Otherwise, return as-is.

        Args:
            tool_name: Full tool name (may include module prefix)

        Returns:
            Function name without module prefix
        """
        if "." in tool_name:
            return tool_name.split(".")[-1]
        return tool_name

    def _extract_parameters(self, parameters: dict[str, Any]) -> str:
        """Extract parameter string from JSON Schema.

        Args:
            parameters: JSON Schema parameters dict

        Returns:
            Comma-separated parameter string (e.g., "user_id: int, name: str")
        """
        props = parameters.get("properties", {})
        required = parameters.get("required", [])

        if not props:
            return ""

        param_list = []

        # Process required parameters first
        for param_name in required:
            if param_name in props:
                param_type = self._json_schema_to_python_type(props[param_name])
                param_list.append(f"{param_name}: {param_type}")

        # Process optional parameters
        for param_name, param_schema in props.items():
            if param_name not in required:
                param_type = self._json_schema_to_python_type(param_schema)
                param_list.append(f"{param_name}: {param_type}")

        return ", ".join(param_list)

    def _json_schema_to_python_type(self, schema: dict[str, Any]) -> str:
        """Convert JSON Schema type to Python type hint.

        Args:
            schema: JSON Schema type definition

        Returns:
            Python type string (e.g., "int", "str", "dict", "list")
        """
        schema_type = schema.get("type")

        if schema_type == "integer":
            return "int"
        if schema_type == "number":
            return "float"
        if schema_type == "string":
            return "str"
        if schema_type == "boolean":
            return "bool"
        if schema_type == "array":
            # For arrays, return "list" (could be enhanced to "list[ItemType]")
            return "list"
        if schema_type == "object":
            return "dict"
        if schema_type == "null":
            return "None"

        # Default fallback
        return "Any"

    def _infer_return_type(self, parameters: dict[str, Any]) -> str:
        """Infer return type for tool.

        Most tools return dict, but this can be enhanced based on
        tool metadata or conventions.

        Args:
            parameters: JSON Schema parameters (not used currently)

        Returns:
            Return type string (default: "dict")
        """
        # For now, default to dict for all tools
        # This can be enhanced later with tool metadata
        return "dict"

    def generate_api_file(
        self,
        registry: ToolRegistry,
        output_dir: str = ".astra/generated/",
    ) -> str:
        """Generate Python API file for sandbox execution.

        Creates a Python file with classes and static methods that wrap
        tool calls. The file is written to `.astra/generated/astra_api.py`.

        Args:
            registry: ToolRegistry instance with populated tools
            output_dir: Output directory path (default: ".astra/generated/")

        Returns:
            Absolute path to generated file

        Raises:
            OSError: If directory creation or file writing fails
        """
        grouped = registry.get_specs_grouped_by_module()

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate file content
        lines = [
            "# Auto-generated by Astra Code Mode - DO NOT EDIT",
            "from astra_runtime import call_tool, call_mcp_tool",
            "",
        ]

        if not grouped:
            lines.append("# No tools available.")
        else:
            # Sort modules alphabetically
            for module_name in sorted(grouped.keys()):
                tools = grouped[module_name]
                if not tools:
                    continue

                # Generate class code for this module
                sanitized_name = self._sanitize_module_name(module_name)
                lines.append(f"class {sanitized_name}:")

                # Add module docstring
                if tools and tools[0].description:
                    docstring = tools[0].description.split("\n")[0].strip()
                    lines.append(f'    """{docstring}"""')
                else:
                    lines.append(f'    """{module_name} tools"""')

                lines.append("")

                # Generate methods for each tool
                for tool_spec in sorted(tools, key=lambda t: t.name):
                    # Extract function signature
                    function_name, params_str, return_type = self._extract_function_signature(
                        tool_spec
                    )

                    # Build method
                    lines.append("    @staticmethod")
                    lines.append(f"    def {function_name}({params_str}) -> {return_type}:")

                    # Add docstring
                    description = tool_spec.description.strip()
                    if description:
                        docstring_line = description.split("\n")[0].strip()
                        lines.append(f'        """{docstring_line}"""')
                    else:
                        lines.append('        """No description available."""')

                    # Generate method body
                    call_function = "call_mcp_tool" if tool_spec.is_mcp else "call_tool"
                    tool_name = (
                        tool_spec.name
                        if "." in tool_spec.name
                        else f"{tool_spec.module}.{tool_spec.name}"
                    )

                    # Generate parameter dict
                    props = tool_spec.parameters.get("properties", {})
                    if props:
                        param_entries = [f'"{name}": {name}' for name in props.keys()]
                        params_dict = "{" + ", ".join(param_entries) + "}"
                    else:
                        params_dict = "{}"

                    lines.append(f'        return {call_function}("{tool_name}", {params_dict})')
                    lines.append("")  # Empty line between methods

                lines.append("")  # Empty line between classes

        # Write file
        file_path = output_path / "astra_api.py"
        file_path.write_text("\n".join(lines), encoding="utf-8")

        return str(file_path.resolve())

    def _sanitize_module_name(self, module_name: str) -> str:
        """Sanitize module name to valid Python identifier.

        Args:
            module_name: Original module name

        Returns:
            Sanitized module name
        """
        if not module_name:
            return "default"

        # Replace dashes and spaces with underscores
        sanitized = module_name.replace("-", "_").replace(" ", "_")

        # Remove invalid characters (keep alphanumeric and underscore)
        sanitized = "".join(c if c.isalnum() or c == "_" else "_" for c in sanitized)

        # Ensure it starts with a letter or underscore
        if sanitized and not (sanitized[0].isalpha() or sanitized[0] == "_"):
            sanitized = f"_{sanitized}"

        # Handle empty result
        if not sanitized:
            return "default"

        return sanitized
