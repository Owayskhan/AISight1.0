import re
from typing import Optional


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