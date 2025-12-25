"""
Example 10: RAG with Streaming Responses
Demonstrates using knowledge base with streaming agent responses.
"""

import asyncio

from framework.KnowledgeBase import HuggingFaceEmbedder, KnowledgeBase, LanceDB, RecursiveChunking
from framework.agents import Agent
from framework.models import Gemini


async def main():
    """Streaming RAG example."""

    print("=" * 60)
    print("Example 10: RAG with Streaming Responses")
    print("=" * 60)

    # Setup knowledge base (using HuggingFace - no API key needed)
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="examples/rag/data/lancedb_streaming", embedder=embedder)

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=400),
    )

    print("\n📚 Adding content to knowledge base...")

    # Add technical content
    await knowledge_base.add_content(
        text="""
        Artificial Intelligence (AI) is the simulation of human intelligence processes by machines.
        These processes include learning (acquiring information and rules for using it), reasoning
        (using rules to reach approximate or definite conclusions), and self-correction.
        
        Key types of AI include:
        - Narrow AI: Designed for specific tasks like voice assistants
        - General AI: Theoretical AI with human-like reasoning
        - Super AI: Hypothetical AI surpassing human intelligence
        
        Common AI applications: Speech recognition, image processing, recommendation systems,
        autonomous vehicles, and natural language processing.
        """,
        name="AI Overview",
        metadata={"topic": "ai", "type": "overview"},
    )

    await knowledge_base.add_content(
        text="""
        Deep Learning is a subset of machine learning based on artificial neural networks.
        It uses multiple layers of processing to progressively extract higher-level features
        from raw input. Deep learning models can learn representations of data with multiple
        levels of abstraction.

        Popular deep learning architectures:
        - Convolutional Neural Networks (CNNs): Image recognition
        - Recurrent Neural Networks (RNNs): Sequence data
        - Transformers: NLP, attention mechanisms
        - GANs: Generative models
        Deep learning requires large amounts of data and computational power, often using
        GPUs or TPUs for training.
        """,
        name="Deep Learning Guide",
        metadata={"topic": "ai", "type": "deep_learning"},
    )

    await knowledge_base.add_content(
        text="""
        Retrieval-Augmented Generation (RAG) combines information retrieval with text generation.
        It works by:
        1. Retrieving relevant documents from a knowledge base
        2. Augmenting the prompt with retrieved context
        3. Generating a response based on the augmented prompt

        Benefits of RAG:
        - Reduces hallucinations by grounding responses in factual data
        - Enables access to up-to-date information
        - Provides source attribution for answers
        - More cost-effective than fine-tuning for domain knowledge
        """,
        name="RAG Explanation",
        metadata={"topic": "rag", "type": "explanation"},
    )

    print("✅ Knowledge base populated\n")

    # Create agent with streaming enabled
    agent = Agent(
        name="StreamingRAGAssistant",
        instructions="""You are an AI assistant with access to a knowledge base about AI technologies.
        When answering questions:
        1. Use the search_knowledge tool to find relevant information
        2. Synthesize information from the knowledge base
        3. Provide clear, accurate answers
        4. Mention the sources when relevant""",
        model=Gemini("gemini-2.5-flash"),
        knowledge_base=knowledge_base,
        stream_enabled=True,  # Enable streaming by default
    )

    # Test questions
    questions = [
        "What is AI and what are its types?",
        "How does deep learning work?",
        "Explain RAG and its benefits",
    ]

    for question in questions:
        print(f"\n{'─' * 60}")
        print(f"❓ Question: {question}")
        print(f"{'─' * 60}")
        print("🤖 Response (streaming): ", end="", flush=True)

        # Stream the response
        chunk_count = 0
        full_response = ""

        async for chunk in agent.stream(question):
            chunk_count += 1
            full_response += chunk
            print(chunk, end="", flush=True)

        print(f"\n\n📊 Stats: {chunk_count} chunks, {len(full_response)} characters")

    print("\n" + "=" * 60)
    print("✅ Streaming RAG demo completed!")
    print("=" * 60)


async def test_stream_vs_invoke():
    """Compare streaming vs non-streaming responses."""

    print("\n" + "=" * 60)
    print("Test: Stream vs Invoke Comparison with RAG")
    print("=" * 60)

    # Setup knowledge base
    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    vector_db = LanceDB(uri="examples/rag/data/lancedb_stream_test", embedder=embedder)

    knowledge_base = KnowledgeBase(
        vector_db=vector_db,
        embedder=embedder,
        chunking=RecursiveChunking(chunk_size=300),
    )

    # Add simple content
    await knowledge_base.add_content(
        text="Python is a programming language created by Guido van Rossum in 1991.",
        name="Python Info",
    )

    agent = Agent(
        name="TestAgent",
        instructions="Use search_knowledge to find information. Be concise.",
        model=Gemini("gemini-2.5-flash"),
        knowledge_base=knowledge_base,
    )

    question = "When was Python created?"

    # Test invoke (non-streaming)
    print("\n📝 Testing invoke (non-streaming)...")
    invoke_response = await agent.invoke(question)
    print(f"Response: {invoke_response[:200]}...")

    # Test stream
    print("\n📝 Testing stream...")
    stream_response = ""
    async for chunk in agent.stream(question):
        stream_response += chunk
    print(f"Response: {stream_response[:200]}...")

    print("\n✅ Both methods work correctly!")


if __name__ == "__main__":
    asyncio.run(main())
    # Optionally run comparison test:
    # asyncio.run(test_stream_vs_invoke())
