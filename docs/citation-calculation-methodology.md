# Citation Rate Calculation Methodology


## Core Concepts

### What is a Citation?

A **citation** occurs when an AI assistant mentions your brand name in its response to a user question. Citations are tracked at multiple levels:

1. **Individual LLM Level**: Did this specific AI assistant mention the brand?
2. **Query Level**: What percentage of AI assistants mentioned the brand for this question?
3. **Overall Level**: What's the average visibility across all questions?

### Binary Citation Model

Our system uses a **binary citation model** where each AI assistant either:
- ✅ **Cited** (1 point): Brand was mentioned at least once
- ❌ **Not Cited** (0 points): Brand was not mentioned at all

This approach ensures fair comparison across different AI assistant response styles and lengths.

## Calculation Process

### Step 1: Individual LLM Citation Detection

For each AI assistant response, we detect brand mentions:

```
Input: AI Response Text + Brand Name
Process: 
  1. Search for exact brand name matches (case-insensitive)
  2. Count total occurrences
  3. Extract sentences containing brand mentions
Output: 
  - cited: true/false (boolean)
  - mention_count: number of times brand appears
  - sentences_with_brand: array of sentences with brand
```

**Example:**
```
Response: "For running shoes, I recommend Nike and Adidas. Nike offers great cushioning."
Brand: "Nike"
Result: cited = true, mention_count = 2
```

### Step 2: Query-Level Visibility Calculation

For each customer question, we calculate the percentage of AI assistants that mentioned the brand:

```
Visibility Percentage = (Number of AIs that cited brand / Total AIs tested) × 100
```

**Formula:**
```
Query Visibility = (Cited LLMs / 3) × 100%
```

**Possible Values:**
- **0%**: No AI assistants mentioned the brand
- **33.3%**: One out of three AI assistants mentioned the brand
- **66.7%**: Two out of three AI assistants mentioned the brand
- **100%**: All three AI assistants mentioned the brand

**Example:**
```
Query: "What are the best running shoes?"
- ChatGPT: Mentioned brand ✅
- Gemini: Did not mention brand ❌
- Perplexity: Mentioned brand ✅

Visibility = (2/3) × 100 = 66.7%
```

### Step 3: Overall Brand Visibility Metrics

Across all queries tested, we calculate aggregate metrics:

#### Average Citation Percentage
```
Average Visibility = Sum of all query visibility percentages / Number of queries
```

**Example:**
```
Query 1: 100% (all 3 AIs mentioned brand)
Query 2: 66.7% (2 out of 3 AIs mentioned brand)
Query 3: 0% (no AIs mentioned brand)
Query 4: 33.3% (1 out of 3 AIs mentioned brand)
Query 5: 100% (all 3 AIs mentioned brand)

Average = (100 + 66.7 + 0 + 33.3 + 100) / 5 = 60%
```

#### Queries with Citations
```
Citation Coverage = Number of queries with at least one citation / Total queries
```

This metric shows how many questions resulted in at least one brand mention.

#### LLM Performance Breakdown

For each AI assistant, we track:
```
Citation Rate = (Queries where this AI cited brand / Total queries) × 100%
Total Mentions = Sum of all brand mentions by this AI
```

## Detailed Calculation Example

### Scenario: Athletic Shoe Brand Analysis

**Test Setup:**
- Brand: "RunFast Shoes"
- 5 test queries about running shoes
- 3 AI assistants tested

**Query 1: "Best running shoes for beginners?"**
- ChatGPT: "For beginners, I recommend RunFast Shoes..." ✅ (1 mention)
- Gemini: "Great options include RunFast Shoes..." ✅ (1 mention)
- Perplexity: "Popular brands include Nike, Adidas..." ❌ (0 mentions)
- **Query 1 Visibility: 66.7%**

**Query 2: "Where to buy affordable running shoes?"**
- ChatGPT: "Check out RunFast Shoes online store..." ✅ (1 mention)
- Gemini: "Many retailers sell running shoes..." ❌ (0 mentions)
- Perplexity: "RunFast Shoes often has sales..." ✅ (1 mention)
- **Query 2 Visibility: 66.7%**

**Query 3: "Running shoe features to look for?"**
- ChatGPT: "Look for cushioning, support..." ❌ (0 mentions)
- Gemini: "Important features include..." ❌ (0 mentions)
- Perplexity: "Key features are stability..." ❌ (0 mentions)
- **Query 3 Visibility: 0%**

**Query 4: "Compare RunFast to Nike?"**
- ChatGPT: "RunFast Shoes offers... compared to Nike..." ✅ (2 mentions)
- Gemini: "RunFast Shoes and Nike both..." ✅ (1 mention)
- Perplexity: "RunFast Shoes provides... while Nike..." ✅ (2 mentions)
- **Query 4 Visibility: 100%**

**Query 5: "Best shoes for marathon training?"**
- ChatGPT: "Top choices include..." ❌ (0 mentions)
- Gemini: "RunFast Shoes marathon line..." ✅ (1 mention)
- Perplexity: "Professional runners often choose..." ❌ (0 mentions)
- **Query 5 Visibility: 33.3%**

### Final Metrics

**Overall Results:**
```
Average Citation Percentage = (66.7 + 66.7 + 0 + 100 + 33.3) / 5 = 53.3%
Queries with Citations = 4 out of 5 = 80%
```

**Per-AI Performance:**
```
ChatGPT:
- Citation Rate: 3/5 queries = 60%
- Total Mentions: 4

Gemini:
- Citation Rate: 3/5 queries = 60%
- Total Mentions: 3

Perplexity:
- Citation Rate: 2/5 queries = 40%
- Total Mentions: 3
```

## Interpretation Guide

### Citation Percentage Ranges

**0-20%**: **Low Visibility**
- Brand rarely appears in AI recommendations
- Significant opportunity for improvement
- Focus on content optimization and brand awareness

**20-40%**: **Moderate Visibility**
- Brand appears occasionally but inconsistently
- Some AI assistants aware of brand
- Target specific gaps in coverage

**40-60%**: **Good Visibility**
- Brand regularly mentioned by AI assistants
- Solid presence in AI recommendations
- Continue optimization efforts

**60-80%**: **Strong Visibility**
- Brand frequently recommended by AI assistants
- Well-established AI presence
- Maintain and enhance position

**80-100%**: **Excellent Visibility**
- Brand dominates AI recommendations
- Top-of-mind for AI assistants
- Leader in category visibility

### Key Insights from Metrics

**High Average, Low Coverage**
- Example: 75% average but only 50% query coverage
- Meaning: Strong performance on some queries, invisible on others
- Action: Expand content to cover missed query types

**Low Average, High Coverage**
- Example: 25% average but 90% query coverage
- Meaning: Mentioned occasionally across many queries
- Action: Strengthen brand positioning and unique value props

**Consistent AI Performance**
- Example: All AIs at similar citation rates (±10%)
- Meaning: Uniform brand perception across platforms
- Action: Maintain consistency while improving overall rates

**Disparate AI Performance**
- Example: ChatGPT 80%, Perplexity 20%
- Meaning: Platform-specific visibility gaps
- Action: Investigate why certain AIs don't recommend brand

## Technical Implementation

### Citation Detection Algorithm

```python
# Simplified citation detection logic
def detect_citations(response_text, brand_name):
    # Case-insensitive search
    brand_pattern = re.compile(brand_name, re.IGNORECASE)
    
    # Find all mentions
    mentions = brand_pattern.findall(response_text)
    mention_count = len(mentions)
    
    # Extract sentences with brand
    sentences = response_text.split('.')
    sentences_with_brand = [
        s.strip() for s in sentences 
        if brand_pattern.search(s)
    ]
    
    return {
        'cited': mention_count > 0,
        'mention_count': mention_count,
        'sentences': sentences_with_brand
    }
```

### Visibility Calculation

```python
# Query-level visibility
def calculate_query_visibility(llm_results):
    cited_count = sum(1 for r in llm_results if r['cited'])
    total_llms = len(llm_results)
    
    visibility_percentage = (cited_count / total_llms) * 100
    
    return round(visibility_percentage, 1)

# Overall brand metrics
def calculate_brand_metrics(all_query_results):
    total_queries = len(all_query_results)
    
    # Average visibility
    total_percentage = sum(q['visibility'] for q in all_query_results)
    average_visibility = total_percentage / total_queries
    
    # Queries with citations
    queries_with_citations = sum(
        1 for q in all_query_results 
        if q['visibility'] > 0
    )
    
    return {
        'average_citation_percentage': round(average_visibility, 1),
        'queries_with_citations': queries_with_citations,
        'total_queries': total_queries
    }
```

## Best Practices for Improving Citation Rates

### Content Optimization
1. **Comprehensive Product Information**: Detailed descriptions improve AI understanding
2. **Unique Value Propositions**: Clear differentiators increase mention likelihood
3. **Structured Data**: Use schema markup for better AI comprehension
4. **Regular Updates**: Keep content fresh and relevant

### Query Alignment
1. **Understand User Intent**: Align content with query types
2. **Cover All Journey Stages**: From awareness to purchase
3. **Answer Common Questions**: FAQs and guides improve visibility
4. **Use Natural Language**: Match how users actually search

### Monitoring and Iteration
1. **Regular Analysis**: Track citation rates monthly
2. **Identify Patterns**: Find which queries get citations
3. **Test Changes**: Measure impact of optimizations
4. **Competitive Benchmarking**: Compare against competitors

## Limitations and Considerations

### What Citation Rates Measure
- ✅ Brand mention frequency in AI responses
- ✅ Relative visibility across AI platforms
- ✅ Coverage across different query types
- ✅ Competitive position in AI recommendations

### Next iteration:
- ❌ Quality or sentiment of mentions
- ❌ Conversion or purchase intent
- ❌ textual report summary

