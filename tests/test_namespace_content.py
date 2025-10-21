"""Test script to check what's actually in the Pinecone namespace"""
import asyncio
import os
import sys

sys.path.insert(0, '/home/asmaa/projects/AISight1.0')

async def test_namespace():
    from core.indexer.pinecone_indexer import get_pinecone_manager
    from core.utils.brand_sanitizer import sanitize_brand_name
    from langchain_openai import OpenAIEmbeddings
    from langchain_pinecone import PineconeVectorStore

    print("=" * 80)
    print("TESTING PINECONE NAMESPACE CONTENT FOR H&M")
    print("=" * 80)

    # Get manager and initialize
    manager = get_pinecone_manager()
    await manager.initialize_index()

    brand_name = "H&M"
    namespace = sanitize_brand_name(brand_name)
    print(f"\n1. Brand Name: {brand_name}")
    print(f"   Namespace: {namespace}")

    # Check if namespace exists
    exists = await manager.namespace_exists(brand_name)
    print(f"\n2. Namespace Exists: {exists}")

    # Get index stats
    print("\n3. Index Stats:")
    index_stats = manager._index.describe_index_stats()
    print(f"   Total vectors: {index_stats.total_vector_count}")

    if hasattr(index_stats, 'namespaces') and index_stats.namespaces:
        print(f"\n4. Namespace Details:")
        for ns_name, ns_stats in index_stats.namespaces.items():
            print(f"   - {ns_name}: {ns_stats.vector_count} vectors")

    # Try to get a retriever and test it
    print(f"\n5. Creating Retriever:")
    try:
        retriever = await manager.get_retriever(
            brand_name=brand_name,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            k=10  # Try to get 10 documents
        )
        print(f"   ✅ Retriever created successfully")

        # Test queries
        test_queries = [
            "H&M fragrance",
            "perfume",
            "beauty products",
            "product"
        ]

        print(f"\n6. Testing Queries:")
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            try:
                results = await retriever.ainvoke(query)
                print(f"   Results: {len(results)} documents")

                if results:
                    print(f"\n   First result:")
                    print(f"   - Content length: {len(results[0].page_content)} characters")
                    print(f"   - Content preview: {results[0].page_content[:200]}...")
                    print(f"   - Metadata: {results[0].metadata}")
                else:
                    print(f"   ⚠️ No documents found!")
            except Exception as e:
                print(f"   ❌ Query failed: {str(e)}")

    except Exception as e:
        print(f"   ❌ Failed to create retriever: {str(e)}")

    # Try direct vector store query
    print(f"\n7. Direct Vector Store Query (bypassing retriever):")
    try:
        embeddings = manager.get_embeddings(os.getenv("OPENAI_API_KEY"), fresh=True)

        vector_store = PineconeVectorStore(
            index=manager._index,
            embedding=embeddings,
            namespace=namespace
        )

        # Try a very simple query
        results = await vector_store.asimilarity_search("product", k=10)
        print(f"   Results: {len(results)} documents")

        if results:
            print(f"\n   Sample documents:")
            for idx, doc in enumerate(results[:3]):
                print(f"\n   Document {idx + 1}:")
                print(f"   - Content length: {len(doc.page_content)} characters")
                print(f"   - Content preview: {doc.page_content[:200]}...")
                print(f"   - Metadata: {doc.metadata}")
        else:
            print(f"   ⚠️ No documents found in vector store!")
            print(f"\n   This means the namespace is EMPTY or vectors were indexed without content.")

    except Exception as e:
        print(f"   ❌ Direct query failed: {str(e)}")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_namespace())
