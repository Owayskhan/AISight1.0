"""Quick script to check what's in the Pinecone namespace for H&M"""
import asyncio
import os
import sys

# Add the project root to the path
sys.path.insert(0, '/home/asmaa/projects/AISight1.0')

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass  # dotenv not required if env vars are already set

from core.indexer.pinecone_indexer import get_pinecone_manager
from core.utils.brand_sanitizer import sanitize_brand_name

async def check_namespace():
    print("=" * 80)
    print("CHECKING PINECONE NAMESPACE FOR H&M")
    print("=" * 80)

    # Get manager and initialize
    manager = get_pinecone_manager()
    await manager.initialize_index()

    # Check namespace
    brand_name = "H&M"
    namespace = sanitize_brand_name(brand_name)
    print(f"\n1. Brand Name: {brand_name}")
    print(f"   Sanitized Namespace: {namespace}")

    # Check if namespace exists
    exists = await manager.namespace_exists(brand_name)
    print(f"\n2. Namespace Exists: {exists}")

    # Get index stats
    print("\n3. Index Stats:")
    index_stats = manager._index.describe_index_stats()
    print(f"   Total vectors: {index_stats.total_vector_count}")
    print(f"   Dimension: {index_stats.dimension}")

    if hasattr(index_stats, 'namespaces') and index_stats.namespaces:
        print(f"\n4. Namespace Details:")
        for ns_name, ns_stats in index_stats.namespaces.items():
            print(f"   - {ns_name}: {ns_stats.vector_count} vectors")
            if ns_name == namespace:
                print(f"     ✅ Found our namespace!")

    # Try to query with a simple test
    print(f"\n5. Test Query:")
    try:
        retriever = await manager.get_retriever(
            brand_name=brand_name,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            k=4
        )

        test_query = "H&M clothing"
        print(f"   Query: {test_query}")
        results = await retriever.ainvoke(test_query)
        print(f"   Results: {len(results)} documents")

        if results:
            print(f"\n6. Sample Document:")
            print(f"   Content preview: {results[0].page_content[:200]}")
            print(f"   Metadata: {results[0].metadata}")
        else:
            print(f"\n6. No documents found!")
            print(f"   This means the namespace might be empty or there's no semantic match")
    except Exception as e:
        print(f"   ❌ Error during test query: {str(e)}")

    # Try to fetch a random vector to see what's actually stored
    print(f"\n7. Attempting to fetch random vectors from namespace:")
    try:
        # Try to query with very high k to see if anything exists
        from langchain_openai import OpenAIEmbeddings
        from langchain_pinecone import PineconeVectorStore

        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=os.getenv("OPENAI_API_KEY")
        )

        vector_store = PineconeVectorStore(
            index=manager._index,
            embedding=embeddings,
            namespace=namespace
        )

        # Try a very broad query
        broad_results = await vector_store.asimilarity_search("product", k=10)
        print(f"   Broad search results: {len(broad_results)} documents")

        if broad_results:
            print(f"\n   First result:")
            print(f"   - Content: {broad_results[0].page_content[:300]}")
            print(f"   - Metadata: {broad_results[0].metadata}")
    except Exception as e:
        print(f"   ❌ Error during broad search: {str(e)}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(check_namespace())
