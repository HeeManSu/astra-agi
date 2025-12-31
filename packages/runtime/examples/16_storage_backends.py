"""Storage backends example - SIMPLIFIED DEMO

Shows different storage backend options.
Only LibSQL demo runs by default (no MongoDB setup required).
"""

import asyncio
import os

from astra import Agent, LibSQLStorage
from astra import HuggingFaceLocal


async def libsql_example():
    """Demonstrate LibSQL (SQLite) storage."""
    
    print("=" * 60)
    print("LibSQL Storage (SQLite)")
    print("=" * 60 + "\n")
    
    print("Configuration:")
    print("  - Backend: SQLite")
    print("  - File: ./agent_storage.db\n")
    
    print("Benefits:")
    print("  ✓ Zero configuration")
    print("  ✓ Perfect for development")
    print("  ✓ Single file database")
    print("  ✓ No external dependencies\n")
    
    # Create storage
    storage = LibSQLStorage(url="sqlite+aiosqlite:///./agent_storage.db")
    await storage.connect()
    
    print("✅ Storage connected\n")
    
    # Create agent with storage
    agent = Agent(
        model=HuggingFaceLocal("Qwen/Qwen2.5-0.5B-Instruct"),
        instructions="You are a helpful assistant.",
        name="storage-demo",
        storage=storage,
    )
    
    # Have a conversation
    print("💬 Starting conversation...\n")
    
    print("👤 User: Hello, I'm learning about Astra")
    response = await agent.invoke(
        "Hello, I'm learning about Astra",
        thread_id="demo-thread-1"
    )
    print(f"🤖 Agent: {response}\n")
    
    print("👤 User: Can you remember that?")
    response = await agent.invoke(
        "Can you remember that?",
        thread_id="demo-thread-1"
    )
    print(f"🤖 Agent: {response}\n")
    
    print("💾 Conversation automatically saved to storage!")
    
    print("\n📊 Storage features:")
    print("  - Thread ID: demo-thread-1")
    print("  - Messages: Automatically persisted")
    print("  - Storage file: ./agent_storage.db")
    
    await storage.disconnect()
    print("\n✅ LibSQL example complete\n")


async def mongodb_example():
    """Show MongoDB storage info."""
    
    print("=" * 60)
    print("MongoDB Storage")
    print("=" * 60 + "\n")
    
    if not os.getenv("MONGODB_URI"):
        print("⚠️  MongoDB not configured")
        print("\nTo use MongoDB storage:")
        print("  1. Install MongoDB or use MongoDB Atlas")
        print("  2. Set: export MONGODB_URI='mongodb://localhost:27017'\n")
        
        print("Configuration example:")
        print("  - Backend: MongoDB")
        print("  - Database: astra_db\n")
        
        print("Benefits:")
        print("  ✓ Production-ready")
        print("  ✓ Scalable")
        print("  ✓ Cloud hosting (Atlas)")
        print("  ✓ High performance\n")
        return
    
    print("✅ MongoDB URI configured")
    print(f"URI: {os.getenv('MONGODB_URI')}\n")
    print("Note: Full MongoDB example requires additional setup\n")


async def storage_comparison():
    """Compare storage backends."""
    
    print("=" * 60)
    print("Storage Backend Comparison")
    print("=" * 60 + "\n")
    
    print("┌──────────┬──────────────┬────────────┬────────────┬──────────┐")
    print("│ Backend  │ Use Case     │ Setup      │ Scale      │ Cost     │")
    print("├──────────┼──────────────┼────────────┼────────────┼──────────┤")
    print("│ LibSQL   │ Development  │ Zero       │ Single app │ Free     │")
    print("│ (SQLite) │ Testing      │            │            │          │")
    print("├──────────┼──────────────┼────────────┼────────────┼──────────┤")
    print("│ MongoDB  │ Production   │ Easy       │ Millions   │ Free tier│")
    print("│          │ Multi-user   │            │ of threads │ then paid│")
    print("└──────────┴──────────────┴────────────┴────────────┴──────────┘")
    
    print("\n💡 Recommendations:")
    print("\n📚 Development & Testing:")
    print("  → Use LibSQL (SQLite)")
    print("  → Zero setup, perfect for local dev")
    
    print("\n🚀 Production:")
    print("  → Use MongoDB")
    print("  → Handles high traffic")
    print("  → Easy to scale\n")


async def main():
    """Run all storage examples."""
    
    print("\n=== Astra Storage Backends ===\n")
    
    await libsql_example()
    await mongodb_example()
    await storage_comparison()
    
    print("=" * 60)
    print("✅ Storage Examples Complete")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
