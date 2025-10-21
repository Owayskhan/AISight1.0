#!/usr/bin/env python3
"""
Simple standalone test for namespace creation logic
"""

import re
from urllib.parse import urlparse
from typing import Optional


def extract_category_path_from_url(url: str) -> str:
    """Extract category path from URL for namespace identification"""
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        if not path:
            return ''

        segments = path.split('/')
        filtered_segments = []
        skip_patterns = ['product', 'p', 'item', 'detail', 'pd']

        for segment in segments:
            if not segment:
                continue
            if segment.isdigit() or len(segment) > 30:
                continue
            if segment.lower() in skip_patterns:
                continue
            if '?' in segment or '#' in segment:
                continue
            filtered_segments.append(segment)

        if not filtered_segments:
            return ''

        category_path = '-'.join(filtered_segments)
        category_path = re.sub(r'[^a-zA-Z0-9\-]', '', category_path.lower())
        category_path = re.sub(r'-+', '-', category_path)
        category_path = category_path.strip('-')
        category_path = category_path[:40].rstrip('-')

        return category_path

    except Exception:
        return ''


def sanitize_brand_with_category(brand_name: str, brand_url: Optional[str] = None) -> str:
    """Create a Pinecone namespace that includes both brand name and category path"""
    if not brand_name or not brand_name.strip():
        raise ValueError("Brand name cannot be empty")

    brand_sanitized = re.sub(r'[^a-zA-Z0-9\s\-]', '', brand_name.lower())
    brand_sanitized = re.sub(r'\s+', ' ', brand_sanitized).strip()
    brand_sanitized = brand_sanitized.replace(' ', '-')
    brand_sanitized = re.sub(r'-+', '-', brand_sanitized)
    brand_sanitized = brand_sanitized.strip('-')

    if not brand_sanitized:
        brand_sanitized = 'unknown'

    category_path = ''
    if brand_url:
        category_path = extract_category_path_from_url(brand_url)

    if category_path:
        namespace = f"brand-{brand_sanitized}-{category_path}"
    else:
        namespace = f"brand-{brand_sanitized}"

    if len(namespace) > 100:
        available_for_category = 100 - len(f"brand-{brand_sanitized}-")
        if available_for_category > 0:
            category_path = category_path[:available_for_category].rstrip('-')
            namespace = f"brand-{brand_sanitized}-{category_path}"
        else:
            max_brand_length = 100 - len('brand-')
            brand_sanitized = brand_sanitized[:max_brand_length].rstrip('-')
            namespace = f"brand-{brand_sanitized}"

    return namespace


def run_tests():
    print("=" * 80)
    print("NAMESPACE CATEGORY PATH TESTING")
    print("=" * 80)

    # Test 1: Extract category paths
    print("\n=== Test 1: Extract Category Paths ===\n")
    test_urls = [
        ("https://nike.com/men/shoes", "men-shoes"),
        ("https://hm.com/us/women/dresses", "us-women-dresses"),
        ("https://example.com", ""),
        ("https://zara.com/women/clothing/dresses", "women-clothing-dresses"),
    ]

    for url, expected in test_urls:
        result = extract_category_path_from_url(url)
        status = "✅" if result == expected else "❌"
        print(f"{status} {url}")
        print(f"   Expected: '{expected}' | Got: '{result}'")

    # Test 2: Create namespaces with categories
    print("\n=== Test 2: Create Namespaces with Categories ===\n")
    test_cases = [
        ("Nike", "https://nike.com/men/shoes", "brand-nike-men-shoes"),
        ("Nike", "https://nike.com/women/clothing", "brand-nike-women-clothing"),
        ("H&M", "https://hm.com/us/women/dresses", "brand-hm-us-women-dresses"),
        ("Nike", None, "brand-nike"),
        ("Zara", "https://zara.com", "brand-zara"),
    ]

    for brand, url, expected in test_cases:
        result = sanitize_brand_with_category(brand, url)
        status = "✅" if result == expected else "❌"
        print(f"{status} Brand: '{brand}' | URL: {url}")
        print(f"   Expected: '{expected}'")
        print(f"   Got:      '{result}'")

    # Test 3: Different categories, same brand
    print("\n=== Test 3: Different Categories, Same Brand ===\n")
    nike_urls = [
        "https://nike.com/men/shoes",
        "https://nike.com/women/clothing",
        "https://nike.com/kids/accessories",
    ]

    namespaces = []
    for url in nike_urls:
        ns = sanitize_brand_with_category("Nike", url)
        namespaces.append(ns)
        print(f"URL: {url}")
        print(f"Namespace: {ns}\n")

    # Check uniqueness
    if len(namespaces) == len(set(namespaces)):
        print("✅ All namespaces are unique!")
    else:
        print("❌ Duplicate namespaces found!")

    # Test 4: Length limits
    print("\n=== Test 4: Length Limits (max 100 chars) ===\n")
    long_brand = "VeryLongBrandNameThatExceedsNormalLengthLimitations"
    long_url = "https://example.com/very/long/category/path/that/goes/on"
    result = sanitize_brand_with_category(long_brand, long_url)
    print(f"Brand: {long_brand}")
    print(f"URL: {long_url}")
    print(f"Namespace: {result}")
    print(f"Length: {len(result)} {'✅' if len(result) <= 100 else '❌'}")

    print("\n" + "=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
