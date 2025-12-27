"""
Example 11: Embedders Demo
Demonstrates different embedders and their output.
"""

import asyncio

from framework.KnowledgeBase import HuggingFaceEmbedder


async def main():
    """Test embedders and show output."""

    print("=" * 60)
    print("Embedders Demo")
    print("=" * 60)

    # Test HuggingFaceEmbedder
    print("\n📊 Testing HuggingFaceEmbedder")
    print("-" * 40)

    embedder = HuggingFaceEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
    print(f"Model: {embedder.model}")
    print(f"Dimension: {embedder.dimension}")

    # Test single text
    print("\n🔤 Embedding single text...")
    texts = ["Hello, world!"]
    embeddings = await embedder.embed(texts)

    print(f"Input: '{texts[0]}'")
    print(f"Embedding shape: [{len(embeddings)}][{len(embeddings[0])}]")
    print(f"First 10 values: {embeddings[0][:10]}")
    print(f"Last 10 values: {embeddings[0][-10:]}")

    # Test multiple texts
    print("\n🔤 Embedding multiple texts...")
    texts = [
        "Python is a programming language.",
        "Machine learning is a subset of AI.",
        "Vectors are used for similarity search.",
    ]

    embeddings = await embedder.embed(texts)
    print(f"Input texts: {len(texts)}")
    print(f"Output embeddings: {len(embeddings)}")

    for i, (text, emb) in enumerate(zip(texts, embeddings)):
        print(f"\n  Text {i + 1}: '{text[:40]}...'")
        print(f"  Dimension: {len(emb)}")
        print(f"  Sample values: [{emb[0]:.4f}, {emb[1]:.4f}, ... {emb[-1]:.4f}]")

    # Test similarity (cosine)
    print("\n📐 Testing embedding similarity...")

    similar_texts = [
        "Python is great for AI development.",
        "Python is excellent for machine learning.",
    ]
    different_text = "The weather is sunny today."

    all_texts = similar_texts + [different_text]
    all_embeddings = await embedder.embed(all_texts)

    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot_product / (norm_a * norm_b)

    sim_1_2 = cosine_similarity(all_embeddings[0], all_embeddings[1])
    sim_1_3 = cosine_similarity(all_embeddings[0], all_embeddings[2])
    sim_2_3 = cosine_similarity(all_embeddings[1], all_embeddings[2])

    print(f"  Text 1: '{similar_texts[0]}'")
    print(f"  Text 2: '{similar_texts[1]}'")
    print(f"  Text 3: '{different_text}'")
    print(f"\n  Similarity (1↔2): {sim_1_2:.4f} (should be high - similar topic)")
    print(f"  Similarity (1↔3): {sim_1_3:.4f} (should be low - different topic)")
    print(f"  Similarity (2↔3): {sim_2_3:.4f} (should be low - different topic)")

    if sim_1_2 > sim_1_3 and sim_1_2 > sim_2_3:
        print("\n  ✅ Embeddings correctly identify similar texts!")
    else:
        print("\n  ⚠️ Similarity scores unexpected")

    # Test different models dimensions
    print("\n📏 Testing model dimensions...")
    models = [
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/all-mpnet-base-v2",
        "BAAI/bge-small-en-v1.5",
    ]

    for model_name in models:
        emb = HuggingFaceEmbedder(model=model_name)
        print(f"  {model_name}: {emb.dimension} dimensions")

    print("\n" + "=" * 60)
    print("✅ Embedders demo completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
