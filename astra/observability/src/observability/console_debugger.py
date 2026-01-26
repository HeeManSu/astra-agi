"""Console debugger for real-time observability output."""

import sys
from typing import Any


# ANSI Color Codes
class Colors:
    """ANSI color codes for terminal output."""

    MAGENTA = "\033[95m"
    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


class ConsoleDebugger:
    """Real-time console debug output.

    Prints trace/span events to stdout for debugging.
    Does NOT persist to database - only for local development.
    Uses sys.stdout for clean, dependency-free output.
    """

    def __init__(self, enabled: bool = False):
        """Initialize console debugger.

        Args:
            enabled: Whether debug mode is active
        """
        self.enabled = enabled
        self._span_depth: dict[str, int] = {}  # Track nesting depth by span_id

    def _write(self, message: str) -> None:
        """Write message to stdout.

        Args:
            message: Message to write
        """
        sys.stdout.write(message + "\n")
        sys.stdout.flush()

    def trace_start(self, trace_id: str, name: str, attributes: dict[str, Any]) -> None:
        """Print trace start event.

        Args:
            trace_id: Unique trace identifier
            name: Trace name (e.g., "agent.finance_analyst.stream")
            attributes: Trace metadata
        """
        if not self.enabled:
            return

        c = Colors
        sep = "=" * 40
        self._write(f"\n{c.MAGENTA}{c.BOLD}{sep} Trace: {name} {sep}{c.RESET}")
        self._write(f"{c.MAGENTA}DEBUG{c.RESET} Trace ID: {c.YELLOW}{trace_id}{c.RESET}")

        # Print important attributes
        for key in ["agent_id", "team_id", "thread_id"]:
            if key in attributes:
                self._write(
                    f"{c.MAGENTA}DEBUG{c.RESET}   {c.GREEN}{key}{c.RESET}: {c.YELLOW}{attributes[key]}{c.RESET}"
                )

    def trace_end(self, trace_id: str, status: str, duration_ms: float) -> None:
        """Print trace end event.

        Args:
            trace_id: Unique trace identifier
            status: Trace status (SUCCESS/ERROR)
            duration_ms: Total execution duration
        """
        if not self.enabled:
            return

        c = Colors
        duration_s = duration_ms / 1000
        self._write(
            f"\n{c.MAGENTA}DEBUG{c.RESET} {c.BOLD}Trace completed:{c.RESET} {c.GREEN if status == 'SUCCESS' else c.YELLOW}{status}{c.RESET} in {c.CYAN}{duration_s:.2f}s{c.RESET}"
        )
        self._write(f"{c.MAGENTA}{'=' * 90}{c.RESET}\n")

    def span_start(
        self,
        span_id: str,
        trace_id: str,
        name: str,
        kind: str,
        parent_span_id: str | None,
        attributes: dict[str, Any],
    ) -> None:
        """Print span start event with minimalist tree styling.

        Args:
            span_id: Unique span identifier
            trace_id: Parent trace identifier
            name: Span name (e.g., "code_generation", "llm.generate_code")
            kind: Span kind (STEP, GENERATION, TOOL)
            parent_span_id: Parent span ID if nested
            attributes: Span metadata
        """
        if not self.enabled:
            return

        c = Colors

        # Calculate indentation based on parent
        if parent_span_id and parent_span_id in self._span_depth:
            depth = self._span_depth[parent_span_id] + 1
        else:
            depth = 0

        self._span_depth[span_id] = depth
        indent = "  " * depth

        # Minimalist tree start
        self._write(f"{c.MAGENTA}DEBUG{c.RESET} {indent}{c.CYAN}▶{c.RESET} {c.BOLD}{name}{c.RESET}")

        # Print key attributes inline or on next line if important
        if "model" in attributes:
            self._write(
                f"{c.MAGENTA}DEBUG{c.RESET} {indent}  {c.DIM}Model: {attributes['model']}{c.RESET}"
            )

    def span_log(
        self, span_id: str, level: str, message: str, data: dict[str, Any] | None = None
    ) -> None:
        """Print span log event.

        Args:
            span_id: Span identifier
            level: Log level (DEBUG, INFO, WARN, ERROR)
            message: Log message
            data: Additional structured data
        """
        if not self.enabled:
            return

        c = Colors

        # Get indentation
        depth = self._span_depth.get(span_id, 0)
        indent = "  " * depth

        # Print log message with level indicator
        color = c.DIM if level == "DEBUG" else c.GREEN if level == "INFO" else c.YELLOW
        prefix = f"{c.MAGENTA}DEBUG{c.RESET} {indent}  "
        self._write(f"{prefix}{color}{message}{c.RESET}")

        # Print data if present
        if data:
            for key, value in data.items():
                if isinstance(value, (int, float)):
                    val = f"{c.YELLOW}{value}{c.RESET}"
                else:
                    val = str(value)
                    if len(val) > 100:
                        val = val[:100] + "..."
                    val = f"{c.CYAN}{val}{c.RESET}"
                self._write(f"{prefix}  {c.DIM}{key}{c.RESET}: {val}")

    def span_end(
        self, span_id: str, name: str, status: str, duration_ms: float, attributes: dict[str, Any]
    ) -> None:
        """Print span end with metrics and duration.

        Args:
            span_id: Span identifier
            name: Span name
            status: Span status (SUCCESS/ERROR)
            duration_ms: Span duration
            attributes: Final span attributes (includes metrics)
        """
        if not self.enabled:
            return

        c = Colors
        depth = self._span_depth.get(span_id, 0)
        indent = "  " * depth

        duration_s = duration_ms / 1000
        duration_str = f"{duration_s:.3f}s" if duration_s >= 1 else f"{duration_ms:.1f}ms"

        # Check for metrics
        has_tokens = any(k in attributes for k in ["total_tokens", "input_tokens"])

        metrics_part = ""
        if has_tokens:
            total = attributes.get("total_tokens", 0)
            in_t = attributes.get("input_tokens", 0)
            out_t = attributes.get("output_tokens", 0)
            metrics_part = f" {c.DIM}[{in_t}i/{out_t}o sum:{total}t]{c.RESET}"

        # Success/Error indicators
        status_symbol = f"{c.GREEN}✔{c.RESET}" if status == "SUCCESS" else f"{c.YELLOW}✘{c.RESET}"

        self._write(
            f"{c.MAGENTA}DEBUG{c.RESET} {indent}{c.CYAN}◀{c.RESET} {c.BOLD}{name}{c.RESET} {status_symbol} in {c.CYAN}{duration_str}{c.RESET}{metrics_part}"
        )

        # Clear depth tracking
        if span_id in self._span_depth:
            del self._span_depth[span_id]
