#!/usr/bin/env python3
"""
Test XML sitemap parsing
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_xml_detection():
    """Test that XML URLs are detected correctly"""
    from core.website_crawler.crawler import load_sitemap_documents_parallel

    test_urls = [
        "https://www.dior.com/sitemap.xml",
        "https://example.com/sitemap.xml.gz",
        "https://example.com/sitemap_index.xml",
    ]

    print("=" * 80)
    print("Testing XML Sitemap Detection")
    print("=" * 80)

    for url in test_urls:
        is_xml = url.endswith('.xml') or url.endswith('.xml.gz') or 'sitemap' in url.lower()
        print(f"\nURL: {url}")
        print(f"Detected as XML: {is_xml}")

    print("\n" + "=" * 80)


async def test_dior_sitemap():
    """Test with actual Dior sitemap"""
    from core.website_crawler.crawler import load_sitemap_documents_parallel

    print("\n" + "=" * 80)
    print("Testing Dior Sitemap Parsing")
    print("=" * 80 + "\n")

    dior_sitemap = "https://www.dior.com/sitemap.xml"

    try:
        print(f"📡 Fetching sitemap: {dior_sitemap}")
        documents = await load_sitemap_documents_parallel(dior_sitemap, max_concurrent=10)

        print(f"\n✅ Successfully parsed sitemap!")
        print(f"📦 Total documents: {len(documents)}")

        if documents:
            print(f"\n📄 First 5 URLs:")
            for i, doc in enumerate(documents[:5], 1):
                url = doc.metadata.get('source', doc.page_content)
                print(f"  {i}. {url}")

            if len(documents) > 5:
                print(f"  ... and {len(documents) - 5} more")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    print("\n🧪 XML Sitemap Parser Test\n")

    # Run tests
    asyncio.run(test_xml_detection())
    asyncio.run(test_dior_sitemap())

    print("\n✅ Test complete!\n")
