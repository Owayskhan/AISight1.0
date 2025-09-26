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


def get_user_intent_distribution(total_queries: int, user_intent: List[str]) -> Dict[str, int]:
    """
    Get query distribution based on user-specified intents.
    Distributes queries evenly across specified intent types.
    
    Args:
        total_queries: Total number of queries to generate
        user_intent: List of intent types to generate queries for
        
    Returns:
        Dict with query count per intent category
        
    Examples:
        user_intent=['informational', 'commercial'] (k=30): 
        {"informational": 15, "commercial": 15, others: 0}
    """
    if not user_intent:
        raise ValueError("user_intent list cannot be empty")
    
    # Initialize all intents to 0
    all_intents = ["navigational", "informational", "commercial", "transactional", "awareness", "consideration"]
    distribution = {intent: 0 for intent in all_intents}
    
    # Distribute queries evenly across specified intents
    queries_per_intent = total_queries // len(user_intent)
    remaining_queries = total_queries % len(user_intent)
    
    for i, intent in enumerate(user_intent):
        distribution[intent] = queries_per_intent
        # Distribute remaining queries to first few intents
        if i < remaining_queries:
            distribution[intent] += 1
    
    return distribution


def analyze_intent_coverage(queries: List[Dict], user_intent: List[str]) -> Dict:
    """
    Analyze what intents are covered by provided queries vs requested intents.
    
    Args:
        queries: List of query dictionaries with 'intent' field
        user_intent: List of requested intent types
        
    Returns:
        Dict with coverage analysis including missing intents and distribution
    """
    # Count intents in provided queries
    provided_intent_counts = {}
    for query in queries:
        intent = query.get('intent', '').lower()
        provided_intent_counts[intent] = provided_intent_counts.get(intent, 0) + 1
    
    # Identify missing intents
    provided_intents = set(provided_intent_counts.keys())
    requested_intents = set(user_intent)
    missing_intents = requested_intents - provided_intents
    
    # Calculate coverage stats
    total_provided = len(queries)
    coverage_percentage = len(provided_intents & requested_intents) / len(requested_intents) * 100 if requested_intents else 100
    
    return {
        "provided_intent_counts": provided_intent_counts,
        "requested_intents": list(requested_intents),
        "missing_intents": list(missing_intents),
        "covered_intents": list(provided_intents & requested_intents),
        "total_provided_queries": total_provided,
        "coverage_percentage": round(coverage_percentage, 1),
        "needs_generation": len(missing_intents) > 0
    }


def calculate_missing_intent_distribution(missing_intents: List[str], remaining_k: int) -> Dict[str, int]:
    """
    Calculate how to distribute remaining queries across missing intents.
    
    Args:
        missing_intents: List of intent types that need queries generated
        remaining_k: Number of additional queries to generate
        
    Returns:
        Dict with query count per missing intent
    """
    if not missing_intents or remaining_k <= 0:
        return {}
    
    # Initialize all intents to 0
    all_intents = ["navigational", "informational", "commercial", "transactional", "awareness", "consideration"]
    distribution = {intent: 0 for intent in all_intents}
    
    # Distribute remaining queries evenly across missing intents
    queries_per_intent = remaining_k // len(missing_intents)
    extra_queries = remaining_k % len(missing_intents)
    
    for i, intent in enumerate(missing_intents):
        distribution[intent] = queries_per_intent
        # Distribute extra queries to first few intents
        if i < extra_queries:
            distribution[intent] += 1
    
    return distribution


def get_smart_query_distribution(total_queries: int, 
                                user_intent: List[str] = None, 
                                provided_queries: List[Dict] = None) -> Dict:
    """
    Get smart query distribution that handles provided queries + user_intent combinations.
    
    Args:
        total_queries: Target total number of queries (k parameter)
        user_intent: User-specified intent types
        provided_queries: Pre-defined queries from user
        
    Returns:
        Dict with distribution info and generation strategy
    """
    # Case 1: Both provided queries and user_intent (HYBRID MODE)
    if provided_queries and user_intent:
        coverage = analyze_intent_coverage(provided_queries, user_intent)
        
        if coverage["needs_generation"]:
            # Calculate how many more queries to generate
            remaining_k = max(0, total_queries - coverage["total_provided_queries"])
            missing_distribution = calculate_missing_intent_distribution(
                coverage["missing_intents"], remaining_k
            )
            
            return {
                "mode": "hybrid",
                "provided_queries": len(provided_queries),
                "needs_generation": remaining_k,
                "missing_intents": coverage["missing_intents"],
                "generation_distribution": missing_distribution,
                "coverage_analysis": coverage,
                "final_total": len(provided_queries) + remaining_k
            }
        else:
            # All requested intents are covered
            return {
                "mode": "provided_only",
                "provided_queries": len(provided_queries),
                "needs_generation": 0,
                "coverage_analysis": coverage,
                "final_total": len(provided_queries)
            }
    
    # Case 2: Only provided queries (use as-is, maybe generate more if k > provided)
    elif provided_queries and not user_intent:
        if len(provided_queries) < total_queries:
            additional_needed = total_queries - len(provided_queries)
            # Use all intent types for additional queries
            additional_distribution = get_query_distribution(additional_needed)
            
            return {
                "mode": "provided_plus_all",
                "provided_queries": len(provided_queries),
                "needs_generation": additional_needed,
                "generation_distribution": additional_distribution,
                "final_total": total_queries
            }
        else:
            return {
                "mode": "provided_only",
                "provided_queries": len(provided_queries),
                "needs_generation": 0,
                "final_total": len(provided_queries)
            }
    
    # Case 3: Only user_intent (existing behavior)
    elif user_intent and not provided_queries:
        distribution = get_user_intent_distribution(total_queries, user_intent)
        return {
            "mode": "user_intent_only",
            "provided_queries": 0,
            "needs_generation": total_queries,
            "generation_distribution": distribution,
            "final_total": total_queries
        }
    
    # Case 4: Neither (all intent types generation)
    else:
        distribution = get_query_distribution(total_queries)
        return {
            "mode": "all_intents",
            "provided_queries": 0,
            "needs_generation": total_queries,
            "generation_distribution": distribution,
            "final_total": total_queries
        }


