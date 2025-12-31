#!/usr/bin/env python3
"""Test all imports from astra.embedded package.

This script verifies that all exported components can be imported successfully.
Run this to validate the embedded runtime package integrity.
"""

import sys


def test_imports():
    """Test importing all exported components."""
    
    print("=" * 70)
    print("Testing Astra Embedded Runtime Imports")
    print("=" * 70 + "\n")
    
    errors = []
    successful = []
    
    # Test categories
    tests = {
        "Core": [
            "Agent",
            "Tool",
            "tool",
        ],
        "Models": [
            "Model",
            "ModelResponse",
            "get_model",
            "Gemini",
            "Bedrock",
            "HuggingFaceLocal",
        ],
        "Storage": [
            "StorageBackend",
            "LibSQLStorage",
            "MongoDBStorage",
        ],
        "RAG - Core": [
            "Rag",
            "RagContext",
            "Pipeline",
            "StageState",
        ],
        "RAG - Components": [
            "Document",
            "Embedder",
            "HuggingFaceEmbedder",
            "LanceDB",
            "VectorDB",
            "Reader",
            "TextReader",
            "RecursiveChunking",
        ],
        "RAG - Stages": [
            "ReadStage",
            "ChunkStage",
            "EmbedStage",
            "StoreStage",
            "RetrieveStage",
        ],
        "Memory": [
            "AgentMemory",
            "MemoryScope",
            "PersistentFacts",
        ],
        "Middlewares": [
            "InputMiddleware",
            "OutputMiddleware",
            "MiddlewareContext",
        ],
        "Guardrails - Base": [
            "InputGuardrail",
            "OutputGuardrail",
            "SchemaGuardrail",
        ],
        "Guardrails - Filters": [
            "InputContentFilter",
            "OutputContentFilter",
            "ContentAction",
            "InputPIIFilter",
            "OutputPIIFilter",
            "PIIAction",
            "SecretLeakageFilter",
            "SecretAction",
            "PromptInjectionFilter",
        ],
        "Guardrails - Exceptions": [
            "InputGuardrailError",
            "OutputGuardrailError",
            "SchemaValidationError",
        ],
        "Teams": [
            "Team",
            "TeamMember",
            "TeamExecutionContext",
            "DELEGATION_TOOL",
            "TeamError",
            "DelegationError",
            "MemberNotFoundError",
            "TeamTimeoutError",
        ],
    }
    
    # Test each category
    for category, items in tests.items():
        print(f"📦 {category}")
        print("-" * 70)
        
        for item in items:
            try:
                exec(f"from astra import {item}")
                successful.append(f"{category}.{item}")
                print(f"  ✅ {item}")
            except ImportError as e:
                errors.append((category, item, str(e)))
                print(f"  ❌ {item} - {e}")
            except Exception as e:
                errors.append((category, item, f"Unexpected: {str(e)}"))
                print(f"  ⚠️  {item} - {e}")
        
        print()
    
    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"\n✅ Successful imports: {len(successful)}")
    print(f"❌ Failed imports: {len(errors)}\n")
    
    if errors:
        print("Failed Imports:")
        for category, item, error in errors:
            print(f"  - {category}.{item}: {error}")
        print()
        return False
    else:
        print("🎉 All imports successful!\n")
        return True


def test_top_level_imports():
    """Test that key imports work from top-level astra package."""
    
    print("=" * 70)
    print("Testing Top-Level Imports (from astra import ...)")
    print("=" * 70 + "\n")
    
    try:
        from astra import (
            Agent, Tool, tool,
            Gemini, HuggingFaceLocal,
            LibSQLStorage,
            Rag, RagContext, Pipeline,
            HuggingFaceEmbedder, LanceDB,
            AgentMemory, MemoryScope,
            InputMiddleware, OutputMiddleware,
            InputGuardrail, PIIAction,
            Team, TeamMember,
        )
        print("✅ Top-level imports successful!")
        print("\nSuccessfully imported:")
        print("  - Agent, Tool, tool")
        print("  - Gemini, HuggingFaceLocal")
        print("  - LibSQLStorage")
        print("  - Rag, RagContext, Pipeline")
        print("  - HuggingFaceEmbedder, LanceDB")
        print("  - AgentMemory, MemoryScope")
        print("  - InputMiddleware, OutputMiddleware")
        print("  - InputGuardrail, PIIAction")
        print("  - Team, TeamMember")
        print()
        return True
    except Exception as e:
        print(f"❌ Top-level import failed: {e}\n")
        return False


if __name__ == "__main__":
    print("\n")
    
    # Run tests
    top_level_ok = test_top_level_imports()
    all_imports_ok = test_imports()
    
    # Exit with appropriate code
    if top_level_ok and all_imports_ok:
        print("✅ All import tests passed!")
        sys.exit(0)
    else:
        print("❌ Some imports failed. See details above.")
        sys.exit(1)
