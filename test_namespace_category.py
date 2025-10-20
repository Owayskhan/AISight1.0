#!/usr/bin/env python3
"""
Test script to verify namespace creation with category paths
"""

from core.utils.brand_sanitizer import (
    extract_category_path_from_url,
    sanitize_brand_with_category,
    sanitize_brand_name
)


def test_extract_category_path():
    """Test category path extraction from URLs"""
    print("\n=== Testing Category Path Extraction ===\n")

    test_cases = [
        ("https://nike.com/men/shoes", "men-shoes"),
        ("https://hm.com/us/women/dresses", "us-women-dresses"),
        ("https://example.com/category/electronics/laptops", "category-electronics-laptops"),
        ("https://example.com", ""),
        ("https://example.com/", ""),
        ("https://example.com/product/12345", ""),  # Should skip product ID
        ("https://zara.com/us/en/woman/dresses-c/12345", "us-en-woman-dresses-c"),  # Filter out numeric IDs
    ]

    for url, expected in test_cases:
        result = extract_category_path_from_url(url)
        status = "✅" if result == expected else "❌"
        print(f"{status} {url}")
        print(f"   Expected: '{expected}'")
        print(f"   Got:      '{result}'")
        print()


def test_sanitize_brand_with_category():
    """Test namespace creation with brand + category"""
    print("\n=== Testing Namespace Creation with Categories ===\n")

    test_cases = [
        ("Nike", "https://nike.com/men/shoes", "brand-nike-men-shoes"),
        ("Nike", "https://nike.com/women/clothing", "brand-nike-women-clothing"),
        ("H&M", "https://hm.com/us/women/dresses", "brand-hm-us-women-dresses"),
        ("Nike", None, "brand-nike"),  # No URL provided
        ("Nike", "https://nike.com", "brand-nike"),  # No category path in URL
        ("Zara & Co.", "https://zara.com/us/women", "brand-zara-co-us-women"),
    ]

    for brand, url, expected in test_cases:
        result = sanitize_brand_with_category(brand, url)
        status = "✅" if result == expected else "❌"
        print(f"{status} Brand: '{brand}', URL: {url}")
        print(f"   Expected: '{expected}'")
        print(f"   Got:      '{result}'")
        print()


def test_backward_compatibility():
    """Test backward compatibility with old sanitize_brand_name function"""
    print("\n=== Testing Backward Compatibility ===\n")

    test_cases = [
        ("Nike", "brand-nike"),
        ("H&M", "brand-hm"),
        ("Zara & Co.", "brand-zara-co"),
    ]

    for brand, expected in test_cases:
        # Old function
        old_result = sanitize_brand_name(brand)
        # New function without URL
        new_result = sanitize_brand_with_category(brand, None)

        status = "✅" if old_result == new_result == expected else "❌"
        print(f"{status} Brand: '{brand}'")
        print(f"   Old function: '{old_result}'")
        print(f"   New function: '{new_result}'")
        print(f"   Expected:     '{expected}'")
        print()


def test_length_limits():
    """Test that namespaces respect Pinecone's 100 character limit"""
    print("\n=== Testing Length Limits ===\n")

    # Test with very long brand name and URL
    long_brand = "VeryLongBrandNameThatExceedsTheNormalLengthLimitations"
    long_url = "https://example.com/very/long/category/path/that/goes/on/and/on"

    result = sanitize_brand_with_category(long_brand, long_url)

    print(f"Long brand: '{long_brand}'")
    print(f"Long URL: '{long_url}'")
    print(f"Result: '{result}'")
    print(f"Length: {len(result)} (max 100)")

    if len(result) <= 100:
        print("✅ Length is within limits")
    else:
        print("❌ Length exceeds 100 characters!")
    print()


def test_real_world_scenarios():
    """Test with real-world brand and category URLs"""
    print("\n=== Testing Real-World Scenarios ===\n")

    scenarios = [
        ("Nike", "https://www.nike.com/w/mens-shoes-nik1zy7ok", "Nike men's shoes"),
        ("Adidas", "https://www.adidas.com/us/women-running", "Adidas women's running"),
        ("Zara", "https://www.zara.com/us/en/woman/dresses-l1066.html", "Zara women's dresses"),
        ("H&M", "https://www2.hm.com/en_us/men/products/jeans.html", "H&M men's jeans"),
    ]

    for brand, url, description in scenarios:
        result = sanitize_brand_with_category(brand, url)
        print(f"📦 {description}")
        print(f"   Brand: '{brand}'")
        print(f"   URL: {url}")
        print(f"   Namespace: '{result}'")
        print(f"   Length: {len(result)}")
        print()


if __name__ == "__main__":
    print("=" * 80)
    print("NAMESPACE CATEGORY PATH TESTING")
    print("=" * 80)

    test_extract_category_path()
    test_sanitize_brand_with_category()
    test_backward_compatibility()
    test_length_limits()
    test_real_world_scenarios()

    print("=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
