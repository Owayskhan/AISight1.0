import re
from typing import Optional
from urllib.parse import urlparse


def sanitize_brand_name(brand_name: str) -> str:
    """
    Sanitize brand name for use as Pinecone namespace
    
    Args:
        brand_name: Raw brand name from user input
        
    Returns:
        Sanitized namespace string suitable for Pinecone
        
    Rules:
        - Convert to lowercase
        - Remove special characters except spaces and hyphens
        - Replace spaces with hyphens
        - Limit to 50 characters
        - Add 'brand-' prefix
    """
    if not brand_name or not brand_name.strip():
        raise ValueError("Brand name cannot be empty")
    
    # Convert to lowercase and remove special characters except spaces
    sanitized = re.sub(r'[^a-zA-Z0-9\s\-]', '', brand_name.lower())
    
    # Replace multiple spaces with single space
    sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
    # Replace spaces with hyphens
    sanitized = sanitized.replace(' ', '-')
    
    # Remove multiple consecutive hyphens
    sanitized = re.sub(r'-+', '-', sanitized)
    
    # Remove leading/trailing hyphens
    sanitized = sanitized.strip('-')
    
    # Limit length and add prefix
    max_length = 50 - len('brand-')  # Reserve space for prefix
    sanitized = sanitized[:max_length]
    
    # Remove trailing hyphen if truncation created one
    sanitized = sanitized.rstrip('-')
    
    # Ensure we have something left
    if not sanitized:
        sanitized = 'unknown'
    
    return f"brand-{sanitized}"


def validate_namespace(namespace: str) -> bool:
    """
    Validate if a namespace string is valid for Pinecone
    
    Args:
        namespace: Namespace string to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not namespace:
        return False
    
    # Check length (Pinecone allows up to 100 characters)
    if len(namespace) > 100:
        return False
    
    # Check allowed characters (alphanumeric, hyphens, underscores)
    if not re.match(r'^[a-zA-Z0-9\-_]+$', namespace):
        return False
    
    return True


def extract_brand_from_namespace(namespace: str) -> Optional[str]:
    """
    Extract original brand name from namespace

    Args:
        namespace: Pinecone namespace (e.g., 'brand-apple-inc')

    Returns:
        Reconstructed brand name or None if invalid format
    """
    if not namespace or not namespace.startswith('brand-'):
        return None

    # Remove 'brand-' prefix
    brand_part = namespace[6:]  # len('brand-') = 6

    # Replace hyphens with spaces and title case
    brand_name = brand_part.replace('-', ' ').title()

    return brand_name if brand_name else None


def extract_category_path_from_url(url: str) -> str:
    """
    Extract category path from URL for namespace identification

    Args:
        url: Full URL (e.g., 'https://nike.com/men/shoes/running')

    Returns:
        Sanitized category path (e.g., 'men-shoes-running')
        Returns empty string if no meaningful path found

    Examples:
        'https://nike.com/men/shoes' -> 'men-shoes'
        'https://hm.com/us/women/dresses' -> 'us-women-dresses'
        'https://example.com' -> ''
        'https://example.com/' -> ''
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.strip('/')

        if not path:
            return ''

        # Split path and filter out common non-category segments
        segments = path.split('/')

        # Filter out common patterns that aren't category paths
        filtered_segments = []
        skip_patterns = ['product', 'p', 'item', 'detail', 'pd']

        for segment in segments:
            # Skip empty segments
            if not segment:
                continue
            # Skip if it looks like a product ID (all numbers or very long alphanumeric)
            if segment.isdigit() or len(segment) > 30:
                continue
            # Skip common product detail patterns
            if segment.lower() in skip_patterns:
                continue
            # Skip if segment contains query parameters or fragments
            if '?' in segment or '#' in segment:
                continue

            filtered_segments.append(segment)

        if not filtered_segments:
            return ''

        # Join segments and sanitize
        category_path = '-'.join(filtered_segments)

        # Remove special characters except hyphens
        category_path = re.sub(r'[^a-zA-Z0-9\-]', '', category_path.lower())

        # Remove multiple consecutive hyphens
        category_path = re.sub(r'-+', '-', category_path)

        # Remove leading/trailing hyphens
        category_path = category_path.strip('-')

        # Limit length to 40 characters to leave room for brand name
        category_path = category_path[:40].rstrip('-')

        return category_path

    except Exception:
        return ''


def sanitize_brand_with_category(brand_name: str, brand_url: Optional[str] = None) -> str:
    """
    Create a Pinecone namespace that includes both brand name and category path

    Args:
        brand_name: Raw brand name from user input
        brand_url: Optional URL to extract category path from

    Returns:
        Sanitized namespace string (e.g., 'brand-nike-men-shoes')

    Rules:
        - If brand_url is provided and contains a category path, include it
        - If brand_url is None or empty, fall back to brand-only namespace
        - Total length limited to 100 characters (Pinecone limit)
        - Format: 'brand-{sanitized_brand_name}-{category_path}'

    Examples:
        sanitize_brand_with_category('Nike', 'https://nike.com/men/shoes')
        -> 'brand-nike-men-shoes'

        sanitize_brand_with_category('H&M', 'https://hm.com/us/women/dresses')
        -> 'brand-hm-us-women-dresses'

        sanitize_brand_with_category('Nike', None)
        -> 'brand-nike'
    """
    if not brand_name or not brand_name.strip():
        raise ValueError("Brand name cannot be empty")

    # Sanitize brand name (without 'brand-' prefix)
    brand_sanitized = re.sub(r'[^a-zA-Z0-9\s\-]', '', brand_name.lower())
    brand_sanitized = re.sub(r'\s+', ' ', brand_sanitized).strip()
    brand_sanitized = brand_sanitized.replace(' ', '-')
    brand_sanitized = re.sub(r'-+', '-', brand_sanitized)
    brand_sanitized = brand_sanitized.strip('-')

    if not brand_sanitized:
        brand_sanitized = 'unknown'

    # Extract category path if URL provided
    category_path = ''
    if brand_url:
        category_path = extract_category_path_from_url(brand_url)

    # Combine brand and category
    if category_path:
        namespace = f"brand-{brand_sanitized}-{category_path}"
    else:
        namespace = f"brand-{brand_sanitized}"

    # Ensure total length doesn't exceed Pinecone's 100 character limit
    if len(namespace) > 100:
        # Truncate category path to fit
        available_for_category = 100 - len(f"brand-{brand_sanitized}-")
        if available_for_category > 0:
            category_path = category_path[:available_for_category].rstrip('-')
            namespace = f"brand-{brand_sanitized}-{category_path}"
        else:
            # Brand name itself is too long, truncate it
            max_brand_length = 100 - len('brand-')
            brand_sanitized = brand_sanitized[:max_brand_length].rstrip('-')
            namespace = f"brand-{brand_sanitized}"

    return namespace