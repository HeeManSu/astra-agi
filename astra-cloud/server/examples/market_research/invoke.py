"""
Invoke Market Research Agent via API

This script demonstrates how to call the agent using the HTTP API.
Make sure the server is running (python main.py) before running this script.

Usage:
    python invoke.py
"""

import json
import sys

import requests


BASE_URL = "http://127.0.0.1:8000"
AGENT_ID = "market-research"


def invoke_agent(message: str, thread_id: str | None = None, stream: bool = False) -> str | None:
    """
    Invoke the agent via API.

    Args:
        message: The message to send to the agent
        thread_id: Optional thread ID for conversation continuity
        stream: Whether to use streaming (SSE) or non-streaming endpoint
    """
    if stream:
        # Use streaming endpoint (Server-Sent Events)
        print(f"\n📡 Streaming request to agent '{AGENT_ID}'...")
        print(f"Message: {message}\n")
        print("Response (streaming):")
        print("-" * 60)

        url = f"{BASE_URL}/api/agents/{AGENT_ID}/stream"
        payload = {"message": message}
        if thread_id:
            payload["thread_id"] = thread_id

        try:
            response = requests.post(url, json=payload, stream=True, timeout=30)
            response.raise_for_status()

            full_response = ""
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # Remove "data: " prefix
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            if "error" in data:
                                print(f"\n❌ Error: {data['error']}")
                                return None
                            if "content" in data:
                                content = data["content"]
                                print(content, end="", flush=True)
                                full_response += content
                        except (json.JSONDecodeError, ValueError):
                            continue

            print("\n" + "-" * 60)
            print(f"\n✅ Streaming complete. Total length: {len(full_response)} characters")
            return full_response

        except requests.exceptions.RequestException as e:
            print(f"\n❌ Request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"Error details: {error_detail}")
                except (ValueError, json.JSONDecodeError):
                    print(f"Response text: {e.response.text}")
            return None
    else:
        # Use non-streaming endpoint
        print(f"\n📨 Sending request to agent '{AGENT_ID}'...")
        print(f"Message: {message}\n")

        url = f"{BASE_URL}/api/agents/{AGENT_ID}/chat"
        payload = {"message": message}
        if thread_id:
            payload["thread_id"] = thread_id

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()

            print("Response:")
            print("-" * 60)
            if "content" in result:
                print(result["content"])
            else:
                print(json.dumps(result, indent=2))
            print("-" * 60)

            return result.get("content", "")

        except requests.exceptions.RequestException as e:
            print(f"\n❌ Request failed: {e}")
            if hasattr(e, "response") and e.response is not None:
                try:
                    error_detail = e.response.json()
                    print(f"Error details: {error_detail}")
                except (ValueError, json.JSONDecodeError):
                    print(f"Response text: {e.response.text}")
            return None


def list_agents() -> None:
    """List all available agents."""
    print("\nListing available agents...")
    try:
        response = requests.get(f"{BASE_URL}/api/agents", timeout=10)
        response.raise_for_status()
        agents = response.json()

        if agents:
            print(f"\nFound {len(agents)} agent(s):")
            for agent in agents:
                print(f"  - {agent.get('name', 'Unknown')} (ID: {agent.get('id', 'Unknown')})")
                if agent.get("description"):
                    print(f"    Description: {agent.get('description')}")
                if agent.get("tools"):
                    print(f"    Tools: {', '.join(agent.get('tools', []))}")
        else:
            print("No agents found.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to list agents: {e}")


def check_server() -> bool:
    """Check if the server is running."""
    try:
        response = requests.get(f"{BASE_URL}/api/agents", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def main():
    """Main function to test the agent."""
    print("=" * 60)
    print("Market Research Agent - API Invocation Test")
    print("=" * 60)

    # Check if server is running
    if not check_server():
        print("\n❌ Server is not running!")
        print("Please start the server first:")
        print("  python main.py")
        print("\nOr run it in the background, then run this script.")
        sys.exit(1)

    # List available agents
    list_agents()

    # Test messages
    test_messages = [
        "What are the top 5 best-selling wireless earbuds on Amazon India?",
        "Analyze the market for fitness trackers under ₹5000 in India",
    ]

    # Ask user which message to use
    print("\n" + "=" * 60)
    print("Test Messages:")
    for i, msg in enumerate(test_messages, 1):
        print(f"  {i}. {msg}")
    print(f"  {len(test_messages) + 1}. Enter custom message")
    print(f"  {len(test_messages) + 2}. Exit")

    try:
        choice = input(f"\nSelect option (1-{len(test_messages) + 2}): ").strip()

        if choice == str(len(test_messages) + 2):
            print("Exiting...")
            return

        if choice == str(len(test_messages) + 1):
            message = input("Enter your message: ").strip()
            if not message:
                print("No message provided. Exiting...")
                return
        elif choice.isdigit() and 1 <= int(choice) <= len(test_messages):
            message = test_messages[int(choice) - 1]
        else:
            print("Invalid choice. Using first test message.")
            message = test_messages[0]

        # Ask for streaming preference
        stream_choice = input("\nUse streaming? (y/n, default: n): ").strip().lower()
        use_streaming = stream_choice in ("y", "yes")

        # Invoke the agent
        invoke_agent(message, stream=use_streaming)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user. Exiting...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
