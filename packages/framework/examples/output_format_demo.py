"""
Example demonstrating output format usage in Astra.

Shows PlainText, Markdown, JSON, and Pydantic formats with validation and repair.
"""
import asyncio
from framework.agents import Agent
from framework.models import Gemini
from framework.output import OutputFormat
from framework.output.exceptions import OutputValidationError, OutputRepairError


async def example_plain_text():
    """Example 1: Plain text output (default)."""
    print("=== Example 1: Plain Text (Default) ===\n")
    
    agent = Agent(
        name="SimpleAgent",
        model=Gemini("1.5-flash")
        # output_format defaults to PlainText
    )
    
    response = await agent.invoke("What is Python?")
    print(f"Response: {response['content'][:100]}...")
    print()


async def example_markdown():
    """Example 2: Markdown formatted output."""
    print("=== Example 2: Markdown Format ===\n")
    
    agent = Agent(
        name="MarkdownAgent",
        model=Gemini("1.5-flash"),
        output_format=OutputFormat.MARKDOWN()
    )
    
    response = await agent.invoke("Explain Python in markdown format")
    print(f"Markdown response: {response['content'][:150]}...")
    print()


async def example_json_schema():
    """Example 3: JSON Schema validation."""
    print("=== Example 3: JSON Schema ===\n")
    
    schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
            "email": {"type": "string"}
        },
        "required": ["name", "age"]
    }
    
    agent = Agent(
        name="JSONAgent",
        model=Gemini("1.5-flash"),
        output_format=OutputFormat.JSON(schema=schema)
    )
    
    try:
        response = await agent.invoke("Create a user profile for Alice, age 30, email alice@example.com")
        print(f"JSON response: {response['content']}")
        print(f"Parsed: {response.get('parsed', 'N/A')}")
    except (OutputValidationError, OutputRepairError) as e:
        print(f"Error: {e}")
    
    print()


async def example_pydantic():
    """Example 4: Pydantic model validation."""
    print("=== Example 4: Pydantic Model ===\n")
    
    try:
        from pydantic import BaseModel, Field
        
        class UserProfile(BaseModel):
            name: str
            age: int = Field(ge=0, le=150)
            email: str
            is_active: bool = True
        
        agent = Agent(
            name="TypedAgent",
            model=Gemini("1.5-flash"),
            output_format=OutputFormat.PYDANTIC(model=UserProfile)
        )
        
        response = await agent.invoke("Create user: Bob, 25, bob@example.com")
        print(f"JSON response: {response['content']}")
        
        # Access typed object
        if 'parsed' in response:
            user = response['parsed']
            print(f"Parsed user: {user}")
            print(f"Name: {user.name}, Age: {user.age}")
        
    except ImportError:
        print("⚠️  Pydantic not installed, skipping example")
    except (OutputValidationError, OutputRepairError) as e:
        print(f"Error: {e}")
    
    print()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Output Format System Examples")
    print("=" * 60)
    print()
    
    await example_plain_text()
    await example_markdown()
    await example_json_schema()
    await example_pydantic()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
