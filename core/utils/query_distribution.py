from typing import Dict, List


def calculate_query_distribution(total_queries: int) -> Dict[str, int]:
    """
    Calculate how to distribute queries across the 6 intent categories.
    
    Ensures at least 1 query per category and distributes extras based on business priority:
    1. Transactional (highest business value - ready to buy)
    2. Commercial (high business value - researching to buy)
    3. Consideration (high business value - comparing options)
    4. Navigational (medium business value - looking for specific sites)
    5. Awareness (medium business value - discovery phase)
    6. Informational (lower business value - general information)
    
    Args:
        total_queries: Total number of queries to generate (minimum 6)
        
    Returns:
        Dict with query count per intent category
        
    Examples:
        k=6:  {"navigational": 1, "informational": 1, "commercial": 1, "transactional": 1, "awareness": 1, "consideration": 1}
        k=7:  {"navigational": 1, "informational": 1, "commercial": 1, "transactional": 2, "awareness": 1, "consideration": 1}
        k=12: {"navigational": 2, "informational": 2, "commercial": 2, "transactional": 2, "awareness": 2, "consideration": 2}
    """
    if total_queries < 6:
        raise ValueError("Minimum 6 queries required (one per intent category)")
    
    # Intent categories in order of business priority
    categories = ["navigational", "informational", "commercial", "transactional", "awareness", "consideration"]
    
    # Start with 1 query per category (minimum requirement)
    distribution = {category: 1 for category in categories}
    remaining_queries = total_queries - 6
    
    # Distribute remaining queries cyclically, prioritizing business value
    # Priority order: transactional > commercial > consideration > navigational > awareness > informational
    priority_order = ["transactional", "commercial", "consideration", "navigational", "awareness", "informational"]
    
    while remaining_queries > 0:
        for category in priority_order:
            if remaining_queries > 0:
                distribution[category] += 1
                remaining_queries -= 1
            else:
                break
    
    return distribution


def get_distribution_summary(distribution: Dict[str, int]) -> str:
    """
    Create a human-readable summary of the query distribution.
    
    Args:
        distribution: Query distribution dictionary
        
    Returns:
        Formatted string describing the distribution
    """
    total = sum(distribution.values())
    
    # Order for display (business priority order)
    display_order = ["transactional", "commercial", "consideration", "navigational", "awareness", "informational"]
    
    parts = []
    for category in display_order:
        if category in distribution:
            count = distribution[category]
            percentage = round((count / total) * 100, 1)
            parts.append(f"{category}: {count} ({percentage}%)")
    
    return f"Total {total} queries distributed as: " + ", ".join(parts)


def validate_and_adjust_distribution(
    distribution: Dict[str, int], 
    target_total: int
) -> Dict[str, int]:
    """
    Validate and adjust distribution to ensure it matches the target total.
    
    Args:
        distribution: Query distribution dictionary
        target_total: Target total number of queries
        
    Returns:
        Adjusted distribution dictionary
    """
    current_total = sum(distribution.values())
    
    if current_total == target_total:
        return distribution
    
    # If totals don't match, recalculate using the main function
    return calculate_query_distribution(target_total)


# Predefined distributions for common values for quick lookup
COMMON_DISTRIBUTIONS = {
    6:  {"navigational": 1, "informational": 1, "commercial": 1, "transactional": 1, "awareness": 1, "consideration": 1},
    7:  {"navigational": 1, "informational": 1, "commercial": 1, "transactional": 2, "awareness": 1, "consideration": 1},
    8:  {"navigational": 1, "informational": 1, "commercial": 2, "transactional": 2, "awareness": 1, "consideration": 1},
    9:  {"navigational": 1, "informational": 1, "commercial": 2, "transactional": 2, "awareness": 1, "consideration": 2},
    10: {"navigational": 1, "informational": 1, "commercial": 2, "transactional": 2, "awareness": 2, "consideration": 2},
    12: {"navigational": 2, "informational": 2, "commercial": 2, "transactional": 2, "awareness": 2, "consideration": 2},
    15: {"navigational": 2, "informational": 2, "commercial": 3, "transactional": 3, "awareness": 2, "consideration": 3},
    18: {"navigational": 3, "informational": 3, "commercial": 3, "transactional": 3, "awareness": 3, "consideration": 3},
    20: {"navigational": 3, "informational": 3, "commercial": 4, "transactional": 4, "awareness": 3, "consideration": 3},
    24: {"navigational": 4, "informational": 4, "commercial": 4, "transactional": 4, "awareness": 4, "consideration": 4},
    25: {"navigational": 4, "informational": 4, "commercial": 5, "transactional": 5, "awareness": 3, "consideration": 4},
    30: {"navigational": 5, "informational": 5, "commercial": 5, "transactional": 5, "awareness": 5, "consideration": 5},
}


def get_query_distribution(total_queries: int, use_cache: bool = True) -> Dict[str, int]:
    """
    Get query distribution, using cache for common values if available.
    
    Args:
        total_queries: Total number of queries to generate
        use_cache: Whether to use predefined distributions for common values
        
    Returns:
        Dict with query count per intent category
    """
    if use_cache and total_queries in COMMON_DISTRIBUTIONS:
        return COMMON_DISTRIBUTIONS[total_queries].copy()
    
    return calculate_query_distribution(total_queries)


def get_plan_filtered_distribution(total_queries: int, plan: str = "free") -> Dict[str, int]:
    """
    Get query distribution filtered by subscription plan.
    
    Args:
        total_queries: Total number of queries to generate
        plan: Subscription plan ('free' or 'paid')
        
    Returns:
        Dict with query count per intent category based on plan
        
    Examples:
        Free plan (k=30): {"informational": 15, "awareness": 15}
        Paid plan (k=30): {"navigational": 5, "informational": 5, "commercial": 5, 
                          "transactional": 5, "awareness": 5, "consideration": 5}
    """
    if plan == "free":
        # Free plan: only informational and awareness intents
        if total_queries < 2:
            raise ValueError("Minimum 2 queries required for free plan (one per allowed intent category)")
        
        # Split queries evenly between informational and awareness
        informational_count = total_queries // 2
        awareness_count = total_queries - informational_count  # Handle odd numbers
        
        return {
            "navigational": 0,
            "informational": informational_count,
            "commercial": 0,
            "transactional": 0,
            "awareness": awareness_count,
            "consideration": 0
        }
    else:
        # Paid plan: use existing distribution across all intent types
        return get_query_distribution(total_queries)