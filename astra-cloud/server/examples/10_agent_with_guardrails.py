"""Agent with guardrails example - CONCEPT DEMONSTRATION

NOTE: This is a concept demonstration showing guardrail APIs.
Full guardrail functionality may require additional configuration.

Shows:
- Input PII filtering
- Prompt injection protection
- Output secret detection
- Content filtering
"""

import asyncio

from astra import Agent, PIIAction
from astra import HuggingFaceLocal


async def main():
    """
    Concept demonstration of guardrails for AI safety.
    """
    
    print("=== Astra Agent Guardrails (Concept Demo) ===\n")
    
    # Create basic agent
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful assistant.",
        name="guardrails-demo",
    )
    
    # Test basic interaction
    print("Test: Normal Query")
    print("👤 User: What's the weather like today?")
    response = await agent.invoke("What's the weather like today?")
    print(f"🤖 Agent: {response}\n")
    
    print("=" * 60)
    print("Guardrails Concept Overview")
    print("=" * 60)
    
    print("\n🛡️  **Input Guardrails**:")
    print("  - InputPIIFilter: Detect/redact PII (email, phone, SSN, credit cards)")
    print("    * Actions: BLOCK or REDACT")
    print("    * Types: email, phone, credit_card, ssn")
    print("  - PromptInjectionFilter: Detect injection attempts")
    print("    * Patterns for common attack vectors")
    print("    * Customizable with additional patterns")
    
    print("\n🛡️  **Output Guardrails**:")
    print("  - OutputPIIFilter: Prevent PII leakage")
    print("  - SecretLeakageFilter: Block API keys, passwords, tokens")
    print("  - OutputContentFilter: Filter inappropriate content")
    
    print("\n📋 **How to use**:")
    print("""
    from astra import InputPIIFilter, PromptInjectionFilter, PIIAction
    
    # Configure input guardrails
    input_guardrails = [
        InputPIIFilter(action=PIIAction.REDACT, types=["email", "phone"]),
        PromptInjectionFilter(),
    ]
    
    # Create agent with guardrails
    agent = Agent(
        model=model,
        input_guardrails=input_guardrails,
    )
    """)
    
    print("\n✨ **Benefits**:")
    print("  ✓ Protect user privacy") 
    print("  ✓ Prevent prompt injection attacks")
    print("  ✓ Ensure regulatory compliance (HIPAA, GDPR)")
    print("  ✓ Filter inappropriate content")


if __name__ == "__main__":
    asyncio.run(main())
