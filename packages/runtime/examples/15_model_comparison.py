"""Model comparison example - SIMPLIFIED DEMO

Shows different model providers and their characteristics.
Only runs HuggingFace by default (no API keys required).
"""

import asyncio
import os

from astra import Agent, Gemini, HuggingFaceLocal


async def main():
    """
    Compare different model providers.
    """
    
    print("=== Astra Model Provider Comparison ===\n")
    
    test_prompt = "Explain what an AI agent is in one sentence."
    
    print(f"📝 Test Prompt: '{test_prompt}'\n")
    print("=" * 60 + "\n")
    
    # 1. HuggingFace Local Model (always runs)
    print("🤗 HuggingFace Local Model")
    print("-" * 60)
    
    hf_agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are concise and clear.",
        name="hf-agent",
    )
    
    print("Configuration:")
    print("  - Provider: HuggingFace")
    print("  - Model: Qwen/Qwen2.5-0.5B-Instruct")
    print("  - Deployment: Local (on device)")
    print("  - Cost: Free\n")
    
    print("Benefits:")
    print("  ✓ Complete privacy (all local)")
    print("  ✓ No API costs")
    print("  ✓ Offline capability")
    print("  ✓ Full control\n")
    
    print("Querying...")
    try:
        hf_response = await hf_agent.invoke(test_prompt)
        print(f"Response: {hf_response}\n")
    except Exception as e:
        print(f"Error: {e}\n")
    
    # 2. Google Gemini (if API key available)
    print("\n" + "=" * 60 + "\n")
    print("🔷 Google Gemini")
    print("-" * 60)
    
    if os.getenv("GOOGLE_API_KEY"):
        gemini_agent = Agent(
            model=Gemini("gemini-1.5-flash"),
            instructions="You are concise and clear.",
            name="gemini-agent",
        )
        
        print("Configuration:")
        print("  - Provider: Google")
        print("  - Model: Gemini 1.5 Flash")
        print("  - Deployment: Cloud API")
        print("  - Cost: Pay per token\n")
        
        print("Benefits:")
        print("  ✓ State-of-the-art performance")
        print("  ✓ Fast responses")
        print("  ✓ No hardware requirements\n")
        
        print("Querying...")
        try:
            gemini_response = await gemini_agent.invoke(test_prompt)
            print(f"Response: {gemini_response}\n")
        except Exception as e:
            print(f"Error: {e}\n")
    else:
        print("⚠️  Skipped: GOOGLE_API_KEY not set")
        print("To use Gemini, set: export GOOGLE_API_KEY='your-key'\n")
    
    # Comparison Summary
    print("\n" + "=" * 60)
    print("Provider Comparison Summary")
    print("=" * 60 + "\n")
    
    print("┌─────────────┬──────────────┬──────────┬────────────┬────────────┐")
    print("│ Provider    │ Deployment   │ Cost     │ Privacy    │ Performance│")
    print("├─────────────┼──────────────┼──────────┼────────────┼────────────┤")
    print("│ HuggingFace │ Local        │ Free     │ Complete   │ Good       │")
    print("│ Gemini      │ Cloud API    │ Pay/use  │ Shared     │ Excellent  │")
    print("│ Bedrock     │ AWS Cloud    │ Pay/use  │ Enterprise │ Excellent  │")
    print("└─────────────┴──────────────┴──────────┴────────────┴────────────┘")
    
    print("\n💡 Recommendations:")
    print("  - Development: HuggingFace Local (free, fast)")
    print("  - Production: Gemini or Bedrock (performance)")


if __name__ == "__main__":
    asyncio.run(main())
