"""
Middleware enums for execution stages and semantic categories.

These enums define the *contract* between the framework, built-in middleware,
and user-defined middleware.

Important:
- Stages describe *WHEN* middleware runs (temporal).
- Categories describe *WHY* middleware exists (semantic).
- Categories MUST NOT affect execution order or control flow.
"""

from enum import Enum


class MiddlewareStage(str, Enum):
    """
    Execution stages for middleware.

    Stages represent *when* a middleware runs in the pipeline.
    They are part of the execution model and affect ordering.

    Notes:
    - Stages are framework-controlled.
    - Users can target stages, but should NOT invent new ones.
    - New stages may be added in the future without breaking existing middleware.
    """

    INPUT = "input"
    """
    Runs before the LLM is called.

    Typical use cases:
    - Input validation
    - Safety checks (PII, prompt injection)
    - Input normalization / formatting
    """

    OUTPUT = "output"
    """
    Runs after the LLM generates a response.

    Typical use cases:
    - Output validation (JSON schema)
    - Content safety checks
    - Output formatting / truncation
    - Metadata enrichment (latency, tokens)
    """

    # ---- Planned / Future Stages (non-breaking additions) ----
    # TOOL_INPUT = "tool_input"
    #   Runs before a tool function is executed
    #
    # TOOL_OUTPUT = "tool_output"
    #   Runs after a tool returns data
    #
    # LLM_INPUT = "llm_input"
    #   Runs after all input middleware but just before the LLM call
    #
    # LLM_OUTPUT = "llm_output"
    #   Runs immediately after the LLM response, before output middleware


class MiddlewareCategory(str, Enum):
    """
    Semantic categories for middleware.

    Categories represent *what* the middleware is responsible for.
    They are purely descriptive and DO NOT affect execution order.

    Categories exist to support:
    - Readability and intent
    - Observability and tracing
    - UI grouping and filtering
    - Policy enforcement (e.g., "disable all safety middleware")
    """

    SAFETY = "safety"
    """
    Safety and security-related middleware.

    Examples:
    - PII detection / masking
    - Prompt injection detection
    - Content moderation
    """

    VALIDATION = "validation"
    """
    Structural or logical validation middleware.

    Examples:
    - JSON parsing
    - JSON schema validation
    - Range or constraint checks
    """

    OPTIMIZATION = "optimization"
    """
    Representation and performance optimizations.

    Important:
    - Must not change semantic meaning.
    - Must be reversible or transparent to the LLM.

    Examples:
    - TOON encoding
    - Dictionary key compression
    """

    FORMATTING = "formatting"
    """
    Presentation-level transformations.

    Examples:
    - Trimming whitespace
    - Normalizing newlines
    - Output truncation
    """

    LOGGING = "logging"
    """
    Observability and diagnostics.

    Examples:
    - Input/output logging
    - Timing measurement
    - Debug metadata injection
    """

    CUSTOM = "custom"
    """
    User-defined or uncategorized middleware.

    Used when:
    - No predefined category fits
    - Experimentation or application-specific logic
    """
