#!/usr/bin/env python3
"""
Test script to verify Pinecone "Session is closed" fix

Usage:
    python test_pinecone_fix.py

This script will:
1. Test basic Pinecone connectivity
2. Test concurrent query retrieval (the main issue area)
3. Report success/failure rates
"""

import asyncio
import os
import sys
from dotenv import load_dotenv
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.indexer.pinecone_indexer import get_pinecone_manager
from core.models.main import QueryItem, Queries

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)


async def test_pinecone_connection():
    """Test basic Pinecone connection"""
    logger.info("=" * 60)
    logger.info("TEST 1: Basic Pinecone Connection")
    logger.info("=" * 60)

    try:
        manager = get_pinecone_manager()
        await manager.initialize_index()
        logger.info("✅ PASSED: Successfully connected to Pinecone")
        return True
    except Exception as e:
        logger.error(f"❌ FAILED: Could not connect to Pinecone: {str(e)}")
        return False


async def test_namespace_check(brand_name: str = "test-brand"):
    """Test namespace existence check"""
    logger.info("=" * 60)
    logger.info("TEST 2: Namespace Existence Check")
    logger.info("=" * 60)

    try:
        manager = get_pinecone_manager()
        stats = await manager.get_namespace_stats(brand_name)
        logger.info(f"✅ PASSED: Retrieved namespace stats: {stats}")
        return True
    except Exception as e:
        logger.error(f"❌ FAILED: Could not check namespace: {str(e)}")
        return False


async def test_concurrent_retrieval(brand_name: str, num_queries: int = 10):
    """Test concurrent query retrieval (the main issue area)"""
    logger.info("=" * 60)
    logger.info(f"TEST 3: Concurrent Query Retrieval ({num_queries} queries)")
    logger.info("=" * 60)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("❌ FAILED: OPENAI_API_KEY not found in environment")
        return False

    try:
        # Get retriever
        manager = get_pinecone_manager()

        # Check if namespace exists
        stats = await manager.get_namespace_stats(brand_name)
        if not stats.get('exists') or stats.get('vector_count', 0) == 0:
            logger.warning(f"⚠️ Namespace '{brand_name}' does not exist or is empty")
            logger.warning("   Please provide a brand name that has been indexed")
            logger.warning("   Example: python test_pinecone_fix.py --brand 'Nike'")
            return False

        logger.info(f"📊 Namespace has {stats['vector_count']} vectors")

        # Get retriever with per_query_fresh enabled
        retriever = await manager.get_retriever(
            brand_name=brand_name,
            openai_api_key=openai_api_key,
            k=4,
            per_query_fresh=True  # This is the fix!
        )

        # Create test queries
        test_queries = [
            f"test query {i} about {brand_name}" for i in range(num_queries)
        ]

        # Execute queries concurrently
        logger.info(f"🚀 Executing {num_queries} concurrent queries...")
        start_time = asyncio.get_event_loop().time()

        async def query_with_tracking(query_text, idx):
            """Execute a single query and track success"""
            try:
                result = await retriever.ainvoke(query_text)
                logger.debug(f"   Query {idx + 1}/{num_queries} succeeded: {len(result)} docs")
                return True, None
            except Exception as e:
                error_msg = str(e)
                if "Session is closed" in error_msg:
                    logger.error(f"   ❌ Query {idx + 1}/{num_queries} failed with SESSION ERROR: {error_msg}")
                else:
                    logger.error(f"   ❌ Query {idx + 1}/{num_queries} failed: {error_msg}")
                return False, error_msg

        # Run all queries concurrently
        tasks = [query_with_tracking(query, i) for i, query in enumerate(test_queries)]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        duration = asyncio.get_event_loop().time() - start_time

        # Analyze results
        successes = sum(1 for success, _ in results if success)
        failures = num_queries - successes
        session_errors = sum(1 for success, error in results if not success and error and "Session is closed" in error)

        success_rate = (successes / num_queries) * 100

        logger.info("=" * 60)
        logger.info("TEST RESULTS:")
        logger.info("=" * 60)
        logger.info(f"Total Queries:      {num_queries}")
        logger.info(f"Successful:         {successes} ({success_rate:.1f}%)")
        logger.info(f"Failed:             {failures}")
        logger.info(f"Session Errors:     {session_errors}")
        logger.info(f"Duration:           {duration:.2f}s")
        logger.info(f"Avg per query:      {duration/num_queries:.2f}s")
        logger.info("=" * 60)

        # Determine test success
        if session_errors > 0:
            logger.error(f"❌ FAILED: {session_errors} queries had 'Session is closed' errors")
            logger.error("   The fix may not be working correctly!")
            return False
        elif success_rate < 95:
            logger.warning(f"⚠️ WARNING: Success rate {success_rate:.1f}% is below 95%")
            logger.warning("   Some queries failed, but no session errors detected")
            return True
        else:
            logger.info(f"✅ PASSED: All queries succeeded without session errors!")
            return True

    except Exception as e:
        logger.error(f"❌ FAILED: Test crashed with error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


async def run_all_tests(brand_name: str = None):
    """Run all tests"""
    logger.info("\n" + "=" * 60)
    logger.info("PINECONE SESSION FIX - TEST SUITE")
    logger.info("=" * 60 + "\n")

    results = []

    # Test 1: Basic connection
    result1 = await test_pinecone_connection()
    results.append(("Connection Test", result1))

    if not result1:
        logger.error("\n❌ Cannot proceed - basic connection failed")
        return False

    # Test 2: Namespace check
    test_brand = brand_name or "test-brand"
    result2 = await test_namespace_check(test_brand)
    results.append(("Namespace Check", result2))

    # Test 3: Concurrent retrieval (the main test)
    if brand_name:
        result3 = await test_concurrent_retrieval(brand_name, num_queries=10)
        results.append(("Concurrent Retrieval (10 queries)", result3))

        # Extra stress test with 20 queries
        if result3:
            logger.info("\n🔥 Running stress test with 20 queries...\n")
            result4 = await test_concurrent_retrieval(brand_name, num_queries=20)
            results.append(("Stress Test (20 queries)", result4))
    else:
        logger.warning("\n⚠️ No brand name provided - skipping concurrent retrieval tests")
        logger.warning("   Usage: python test_pinecone_fix.py --brand 'BrandName'")

    # Final summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        logger.info(f"{status}: {test_name}")

    all_passed = all(passed for _, passed in results)

    logger.info("=" * 60)
    if all_passed:
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("The Pinecone session fix is working correctly.")
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.error("Please review the errors above and check your configuration.")
    logger.info("=" * 60 + "\n")

    return all_passed


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Pinecone session fix")
    parser.add_argument("--brand", type=str, help="Brand name to test (must be already indexed)")
    parser.add_argument("--queries", type=int, default=10, help="Number of concurrent queries to test")

    args = parser.parse_args()

    # Run tests
    success = asyncio.run(run_all_tests(brand_name=args.brand))

    # Exit with appropriate code
    sys.exit(0 if success else 1)
