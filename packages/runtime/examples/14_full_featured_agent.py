"""Full-featured agent example.

Demonstrates a production-ready agent combining:
- Tools for external actions
- RAG for knowledge augmentation
- Memory (basic STM for V1)
- Guardrails for safety
- Middlewares for logging
- Storage for persistence

NOTE: PersistentFacts is disabled for V1 release.
"""

import asyncio

from astra import (
    Agent,
    AgentMemory,
    HuggingFaceEmbedder,
    HuggingFaceLocal,
    LanceDB,
    LibSQLStorage,
    # @TODO: Himanshu. PersistentFacts disabled for V1 release. Will be enabled later.
    # MemoryScope,
    # PersistentFacts,
    Pipeline,
    Rag,
    RagContext,
    tool,
)


# Define tools
@tool
async def get_current_time() -> str:
    """Get the current time.

    Returns:
        Current time as a string
    """
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool
async def calculate(expression: str) -> str:
    """Safely calculate a mathematical expression.

    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 2")

    Returns:
        Result of the calculation
    """
    try:
        # Safe evaluation of simple math expressions
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Error: {e!s}"


@tool
async def web_search(query: str) -> str:
    """Search the web for information.

    Args:
        query: Search query

    Returns:
        Search results summary
    """
    # Simulated web search
    return f"Simulated search results for: {query}"


async def main():
    """
    Production-ready agent with all features enabled.

    This demonstrates a fully-featured agent suitable for real applications.
    """

    print("=== Full-Featured Astra Agent ===\n")

    # 1. Setup Storage
    print("🗄️  Initializing storage...")
    storage = LibSQLStorage(url="sqlite+aiosqlite:///./full_featured_agent.db")
    await storage.connect()
    print("✅ Storage connected\n")

    # 2. Setup RAG
    print("📚 Setting up RAG system...")
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="./full_featured_kb", embedder=embedder)

    # Create RAG context
    rag_context = RagContext(embedder=embedder, vector_db=vector_db, config={"default_top_k": 5})

    # Create pipelines
    from astra import ChunkStage, EmbedStage, ReadStage, RetrieveStage, StoreStage

    ingest_pipeline = Pipeline(
        name="ingest",
        stages=[
            ReadStage(),
            ChunkStage(),
            EmbedStage(),
            StoreStage(),
        ],
    )

    query_pipeline = Pipeline(name="query", stages=[RetrieveStage(top_k=5)])

    # Create RAG with all required parameters
    rag = Rag(
        context=rag_context,
        ingest_pipeline=ingest_pipeline,
        query_pipeline=query_pipeline,
    )

    # Ingest some knowledge
    knowledge = [
        "Astra is an AI framework for building agents in Python.",
        "The framework supports tools, RAG, memory, and teams.",
        "Agents can be deployed in embedded mode or as a server.",
    ]

    for doc in knowledge:
        await rag.ingest(doc)

    print("✅ RAG initialized with knowledge base\n")

    # 3. Setup Memory
    print("🧠 Configuring memory...")
    memory = AgentMemory()

    # @TODO: Himanshu. PersistentFacts disabled for V1 release. Will be enabled later.
    # facts = PersistentFacts(storage=storage)
    # await facts.add(
    #     key="framework_name",
    #     value="Astra",
    #     scope=MemoryScope.GLOBAL,
    # )
    print("✅ Memory configured (basic STM for V1)\n")

    # 4. Configure Tools
    print("🔧 Loading tools...")
    tools = [
        get_current_time,
        calculate,
        web_search,
    ]
    print(f"✅ Loaded {len(tools)} tools\n")

    # 5. Create Full-Featured Agent
    print("🤖 Creating agent with all features...\n")

    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="""You are a highly capable AI assistant with:
        
        - Access to tools for time, calculations, and web search
        - Knowledge base via RAG for framework information
        - Memory for conversation history
        - Storage for persistence
        
        Use your tools when needed. Consult your knowledge base
        for questions about Astra.""",
        name="full-featured-assistant",
        storage=storage,
        tools=tools,
        rag_pipeline=rag,
        memory=memory,
        # @TODO: Himanshu. PersistentFacts disabled for V1 release. Will be enabled later.
        # persistent_facts=facts
    )

    print("=" * 60)
    print("✅ Agent Ready!")
    print("=" * 60)
    print("\n📋 Features enabled:")
    print(f"   ✓ Tools: {len(tools)} available")
    print(f"   ✓ RAG: {len(knowledge)} documents indexed")
    print("   ✓ Memory: Conversation history tracking")
    print("   ✓ Storage: LibSQL database")
    print("   ℹ️  PersistentFacts: Disabled for V1")
    print()

    # 6. Demonstrate Usage
    print("=" * 60)
    print("Demonstration")
    print("=" * 60 + "\n")

    # Example 1: Using tools
    print("Example 1: Using Tools")
    print("👤 User: What time is it?")
    response = await agent.invoke("What time is it?")
    print(f"🤖 Agent: {response}\n")

    print("👤 User: Calculate 125 * 37")
    response = await agent.invoke("Calculate 125 * 37")
    print(f"🤖 Agent: {response}\n")

    # Example 2: Using RAG
    print("\nExample 2: Using RAG Knowledge Base")
    print("👤 User: What is Astra?")
    response = await agent.invoke("What is Astra?")
    print(f"🤖 Agent: {response}\n")

    # Example 3: Memory
    print("\nExample 3: Using Memory")
    print("👤 User: My name is Alex")
    response = await agent.invoke("My name is Alex")
    print(f"🤖 Agent: {response}\n")

    print("👤 User: What's my name?")
    response = await agent.invoke("What's my name?")
    print(f"🤖 Agent: {response}\n")

    # Example 4: Complex query using multiple features
    print("\nExample 4: Complex Query (Multiple Features)")
    print("👤 User: Search for 'Python AI frameworks' and tell me if Astra is one of them")
    response = await agent.invoke(
        "Search for 'Python AI frameworks' and search your knowledge base to tell me if Astra is one"
    )
    print(f"🤖 Agent: {response}\n")

    print("=" * 60)
    print("✅ Full-Featured Agent Demonstration Complete!")
    print("=" * 60)

    # Cleanup
    await storage.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
