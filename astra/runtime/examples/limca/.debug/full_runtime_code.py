
import sys
import json

def call_tool(name: str, **kwargs):
    """Call a tool in the parent process.

    Sends a JSON request to stdout, waits for response on stdin.

    Args:
        name: Tool name (e.g., "inventory.check_inventory")
        **kwargs: Tool arguments

    Returns:
        Tool result (dict or primitive)

    Raises:
        RuntimeError: If tool execution fails
    """
    # Send request to parent via stdout
    request = {"type": "call_tool", "name": name, "args": kwargs}
    print(json.dumps(request), flush=True)

    # Wait for response from parent via stdin
    # Use 100MB buffer limit to handle very large tool responses
    response_line = sys.stdin.readline(100 * 1024 * 1024)
    if not response_line:
        raise RuntimeError("No response from parent process")

    response = json.loads(response_line)

    # Check for error
    if response.get("type") == "error":
        raise RuntimeError(response.get("message", "Tool execution failed"))

    return response.get("data", {})


def synthesize_response(message):   # (message:str -> message)
    """Return final response to parent and exit.

    This ends the subprocess execution and sends the final answer.

    Args:
        message: Final response message (can be str, dict, or list)
    """
    # Handle dict/list by JSON serializing, otherwise use str @todo: Proper review required
    if isinstance(message, (dict, list)):
        message_str = json.dumps(message, ensure_ascii=False, default=str)
    else:
        message_str = str(message)

    request = {"type": "synthesize", "message": message_str}
    print(json.dumps(request), flush=True)
    sys.exit(0)


def continue_analysis(results: dict, next_step: str = ""):
    """Signal that more analysis iterations are needed.

    Use this when you have gathered some data but need to make additional
    tool calls based on those results. The parent process will re-invoke
    code generation with your results as context.

    Args:
        results: Current tool results to pass to next iteration (dict)
        next_step: Optional hint about what the next iteration should focus on
    """
    if not isinstance(results, dict):
        results = {"data": results}

    request = {
        "type": "continue",
        "results": json.dumps(results, ensure_ascii=False, default=str),
        "next_step": next_step
    }
    print(json.dumps(request), flush=True)
    sys.exit(0)



# ═══════ Agent Stub Classes ═══════

class limca:
    """Agent: Limca"""
    @staticmethod
    def index_codebase(**kwargs):
        return call_tool("limca.index_codebase", **kwargs)
    @staticmethod
    def find_symbol(**kwargs):
        return call_tool("limca.find_symbol", **kwargs)
    @staticmethod
    def trace_calls(**kwargs):
        return call_tool("limca.trace_calls", **kwargs)
    @staticmethod
    def find_references(**kwargs):
        return call_tool("limca.find_references", **kwargs)
    @staticmethod
    def get_file_snippet(**kwargs):
        return call_tool("limca.get_file_snippet", **kwargs)
    @staticmethod
    def get_class_hierarchy(**kwargs):
        return call_tool("limca.get_class_hierarchy", **kwargs)
    @staticmethod
    def find_imports(**kwargs):
        return call_tool("limca.find_imports", **kwargs)
    @staticmethod
    def generate_diagram(**kwargs):
        return call_tool("limca.generate_diagram", **kwargs)
    @staticmethod
    def generate_wiki(**kwargs):
        return call_tool("limca.generate_wiki", **kwargs)


# ═══════ LLM Generated Code ═══════

symbol_search_result = limca.find_symbol(query="RAG AGENT")
synthesize_response({
    "symbol_search_result": symbol_search_result
})