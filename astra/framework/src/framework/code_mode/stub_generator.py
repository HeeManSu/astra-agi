"""
Stub Generator for Team Code Mode.

This module generates Python stub code from a TeamSemanticLayer.
The generated stubs are used as context for LLM code generation.

Flow:
    Team → TeamSemanticLayer → generate_stubs() → Python stub string → LLM prompt

Output Format:
    - Each Agent becomes a class
    - Each Tool becomes a @staticmethod
    - Each method has full docstring with Args, Returns, Example

Example Output:
    class inventory:
        '''Manages inventory operations.'''

        @staticmethod
        def check_inventory(product_ids: list[str]) -> str:
            '''Check stock availability...'''
            ...
"""

import json

from framework.code_mode.semantic import (
    DomainSchema,
    EntitySemanticLayer,
    ParamSchema,
    ToolSchema,
)


# JSON Schema to Python type mapping
_JSON_SCHEMA_TYPE_MAP = {
    "string": "str",
    "number": "float",
    "integer": "int",
    "boolean": "bool",
    "array": "list",
    "object": "dict",
}


# Type Normalization
def _type_to_python(type_str: str) -> str:
    """
    Normalize type strings for Python syntax.

    Handles both Python types and JSON Schema types from MCP tools.
    Pydantic model names (like ValidateOrderOutput) are converted to 'dict'
    because tools return dict objects that can be inspected.

    Args:
        type_str: Type as string from Pydantic schema or JSON Schema

    Returns:
        Normalized Python type string

    Examples:
        >>> _type_to_python("str")
        'str'
        >>> _type_to_python("string")  # JSON Schema
        'str'
        >>> _type_to_python("ValidateOrderOutput")
        'dict'  # Pydantic models return as dict
    """
    # JSON Schema types → Python types
    if type_str in _JSON_SCHEMA_TYPE_MAP:
        return _JSON_SCHEMA_TYPE_MAP[type_str]

    # Primitive types - keep as-is
    primitives = {"str", "int", "float", "bool", "dict", "list", "Any", "None"}
    if type_str in primitives:
        return type_str

    # Generic types like list[dict], list[str] - keep as-is
    if type_str.startswith(("list[", "dict[")):
        return type_str

    # Union types - keep as-is
    if "|" in type_str:
        return type_str

    # Pydantic model names (e.g., ValidateOrderOutput) → tools return dict
    return "dict"


def _sanitize_identifier(name: str) -> str:
    """
    Sanitize a name to be a valid Python identifier.

    Converts dashes to underscores (common in MCP tool names).

    Args:
        name: Original name (e.g., 'append-blocks')

    Returns:
        Valid Python identifier (e.g., 'append_blocks')

    Examples:
        >>> _sanitize_identifier("get-block")
        'get_block'
        >>> _sanitize_identifier("get_stock_price")
        'get_stock_price'
    """
    return name.replace("-", "_")


# Parameter Formatting
def _format_param_signature(param: ParamSchema) -> str:
    """
    Format a single parameter for the function signature.

    Handles four cases:
    1. Required without default: `order_id: str`
    2. Required with default: `domain: str = 'in'` (still required, but has fallback)
    3. Optional with None: `notes: str | None = None`
    4. Optional with value: `limit: int = 10`

    Args:
        param: ParamSchema with name, type, required, default

    Returns:
        Formatted parameter string for function signature
    """
    type_str = _type_to_python(param.type)

    if param.required:
        if param.default is not None:
            # Required with default: show the default value
            default_repr = repr(param.default)
            return f"{param.name}: {type_str} = {default_repr}"
        else:
            # Required without default: just name: type
            return f"{param.name}: {type_str}"
    else:
        # Optional: check if default is None or has a value
        if param.default is None:
            return f"{param.name}: {type_str} | None = None"
        else:
            # Use repr() to properly quote strings
            default_repr = repr(param.default)
            return f"{param.name}: {type_str} = {default_repr}"


# Example Formatting
def _format_example(domain_id: str, tool: ToolSchema) -> str:
    """
    Generate example from tool's ExampleSchema.

    Creates a readable example with result assignment and formatted dict output,
    making it easy for LLM to learn the expected usage pattern.

    Args:
        domain_id: Class name (e.g., "inventory")
        tool: ToolSchema with example data

    Returns:
        Formatted example string

    Output Format:
        result = inventory.check_inventory(["PROD-001", "PROD-002"])

        result == {
            "products": [...],
            ...
        }
    """
    if not tool.example:
        return ""

    # Build function call arguments from example input
    args = []
    for param in tool.parameters:
        value = tool.example.input.get(param.name)
        if value is not None:
            args.append(repr(value))

    # Construct call string
    call = f"{domain_id}.{tool.name}({', '.join(args)})"

    # Format output as indented dict
    output_dict = tool.example.output
    formatted_output = json.dumps(output_dict, indent=4)
    # Add proper indentation for docstring (12 spaces for each line)
    indented_output = "\n".join(f"            {line}" for line in formatted_output.split("\n"))

    # Return formatted example
    lines = [
        f"            result = {call}",
        "",
        f"            result == {indented_output.strip()}",
    ]
    return "\n".join(lines)


# Docstring Generation
def _generate_docstring(domain_id: str, tool: ToolSchema) -> str:
    """
    Generate a complete docstring with Args, Returns, and Example sections.

    This is the key part for LLM understanding - detailed docstrings
    provide context for accurate code generation.

    Args:
        domain_id: Class name for example formatting
        tool: ToolSchema with description, parameters, returns, example

    Returns:
        Complete docstring string (with proper indentation)
    """
    lines = []

    # Opening triple quotes
    lines.append('        """')

    # Tool description
    lines.append(f"        {tool.description}")
    lines.append("")

    # Args section - show both default values and required markers
    lines.append("        Args:")
    for p in tool.parameters:
        # Build suffix with default and required markers
        suffix_parts = []
        if p.default is not None:
            suffix_parts.append(f"default: {p.default!r}")
        if p.required:
            suffix_parts.append("required")

        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        lines.append(f"            {p.name}: {p.description}{suffix}")

    # Returns section with field details
    lines.append("")
    lines.append("        Returns:")
    return_type = _type_to_python(tool.returns.type)
    if tool.returns.fields:
        lines.append(f"            {return_type} with fields:")
        lines.extend(
            f"            - {field.name} ({field.type}): {field.description}"
            for field in tool.returns.fields
        )
    else:
        lines.append(f"            {return_type}: {tool.returns.description}")

    # Example section (if available)
    if tool.example:
        lines.append("")
        lines.append("        Example:")
        lines.append(_format_example(domain_id, tool))

    # Closing triple quotes
    lines.append('        """')

    return "\n".join(lines)


# Tool Stub Generation
def _generate_tool_stub(domain_id: str, tool: ToolSchema) -> str:
    """
    Generate a single @staticmethod stub for a tool.

    Creates a complete method with:
    - @staticmethod decorator
    - Function signature with typed parameters
    - Full docstring with Args/Returns/Example
    - Ellipsis (...) as body placeholder

    Args:
        domain_id: Class name for example formatting
        tool: ToolSchema to convert to stub

    Returns:
        Complete method stub string
    """
    lines = []

    # Sanitize tool name for Python (e.g., 'get-block' -> 'get_block')
    method_name = _sanitize_identifier(tool.name)

    # Build parameter list
    parameters = tool.parameters
    params = [_format_param_signature(param) for param in parameters]

    # Format params with proper indentation (one param per line for readability)
    if len(params) <= 2:
        # Short param list - single line
        param_str = ", ".join(params)
        signature_lines = [
            f"    def {method_name}({param_str}) -> {_type_to_python(tool.returns.type)}:"
        ]
    else:
        # Long param list - multi-line
        signature_lines = [f"    def {method_name}("]
        for param in params:
            signature_lines.append(f"        {param},")
        signature_lines.append(f"    ) -> {_type_to_python(tool.returns.type)}:")

    # Assemble method
    lines.append("    @staticmethod")
    lines.extend(signature_lines)
    lines.append(_generate_docstring(domain_id, tool))
    lines.append("        ...")

    return "\n".join(lines)


# Domain (Class) Stub Generation
def _generate_domain_stub(domain: DomainSchema) -> list[str]:
    """
    Generate a class stub for a domain (Agent).

    Each Agent becomes a Python class with:
    - Class name from domain.id (used as-is)
    - Class docstring from domain.description
    - @staticmethod methods for each tool

    Args:
        domain: DomainSchema representing an Agent

    Returns:
        List of lines for the class stub
    """
    lines = []

    # Sanitize domain.id for Python class name (e.g., 'brave-search' -> 'brave_search')
    class_name = _sanitize_identifier(domain.id)

    # Class definition
    lines.append(f"class {class_name}:")
    lines.append(f'    """{domain.description}"""')

    # Generate each tool as a @staticmethod
    for tool in domain.tools:
        lines.append("")  # Blank line between methods
        lines.append(_generate_tool_stub(class_name, tool))

    # Blank lines after class
    lines.append("")
    lines.append("")

    return lines


# Main Entry Point
def generate_stubs(semantic_layer: EntitySemanticLayer) -> str:
    """
    Generate complete Python stub code from a TeamSemanticLayer.

    This is the main entry point. It produces a single string containing
    all class and method stubs, ready to be injected into an LLM prompt.

    Handles duplicate domains by tracking seen domain IDs and skipping
    any duplicates (e.g., when multiple agents have the same MCP toolkit).

    Flow:
        TeamSemanticLayer
        └── domains[]
            └── DomainSchema → class
                └── tools[]
                    └── ToolSchema → @staticmethod

    Args:
        semantic_layer: Complete semantic layer from build_team_semantic_layer()

    Returns:
        Python stub code as a single string

    Example:
        team = Team(...)
        semantic = team.semantic_layer
        stubs = generate_stubs(semantic)

        prompt = f'''
        You have access to:
        {stubs}

        Task: {user_query}
        '''
    """
    lines = []

    # Header comment with team name
    lines.append(
        "# ═══════════════════════════════════════════════════════════════════════════════"
    )
    lines.append(f"# AVAILABLE TOOLS - {semantic_layer.provider_name}")
    lines.append(
        "# ═══════════════════════════════════════════════════════════════════════════════"
    )
    lines.append("")

    # Track seen domain IDs to avoid duplicate classes
    seen_domains: set[str] = set()

    # Generate each domain (agent) as a class
    for domain in semantic_layer.domains:
        # Skip if we've already generated this domain (deduplication)
        if domain.id in seen_domains:
            continue
        seen_domains.add(domain.id)

        lines.extend(_generate_domain_stub(domain))

    return "\n".join(lines)


def generate_runtime_stubs(semantic_layer: EntitySemanticLayer) -> str:
    """Generate minimal runtime stubs for subprocess execution.

    Unlike generate_stubs() which creates rich docstrings for LLM understanding,
    this function creates minimal stubs that route calls to call_tool().

    Handles duplicate domains by tracking seen domain IDs and skipping
    any duplicates (e.g., when multiple agents have the same MCP toolkit).

    Uses **kwargs pattern for maximum flexibility:
    - Accepts any combination of arguments the LLM generates
    - No need to track defaults - the actual tool's Pydantic model handles validation
    - If LLM adds optional args based on user query, they pass through seamlessly

    Args:
        semantic_layer: Complete semantic layer from build_team_semantic_layer()

    Returns:
        Python stub code that routes class.method(**kwargs) to call_tool()

    Example Output:
        class market_analyst:
            @staticmethod
            def get_stock_price(**kwargs):
                return call_tool("market_analyst.get_stock_price", **kwargs)
    """
    lines = ["\n# ═══════ Agent Stub Classes ═══════\n"]

    # Track seen domain IDs to avoid duplicate classes
    seen_domains: set[str] = set()

    for domain in semantic_layer.domains:
        # Skip if we've already generated this domain (deduplication)
        if domain.id in seen_domains:
            continue
        seen_domains.add(domain.id)

        # Sanitize domain ID for Python class name
        class_name = _sanitize_identifier(domain.id)

        # Class definition
        lines.append(f"class {class_name}:")
        lines.append(f'    """Agent: {domain.name}"""')

        # Generate @staticmethod for each tool
        if not domain.tools:
            lines.append("    pass")

        for tool in domain.tools:
            # Sanitize tool name for Python method
            method_name = _sanitize_identifier(tool.name)

            # Use domain.id (sanitized) for routing - both local and MCP
            full_name = f"{domain.id}.{tool.name}"

            # Use **kwargs for maximum flexibility
            # The actual tool's Pydantic model will validate inputs and apply defaults
            lines.append("    @staticmethod")
            lines.append(f"    def {method_name}(**kwargs):")
            lines.append(f'        return call_tool("{full_name}", **kwargs)')

        lines.append("")

    return "\n".join(lines)
