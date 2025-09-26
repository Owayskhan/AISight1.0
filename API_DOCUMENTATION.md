# Citation Analysis API Documentation

## Overview
The Citation Analysis API analyzes brand visibility across AI assistants (OpenAI GPT, Google Gemini, Perplexity) by generating relevant queries, retrieving context, and measuring how often the brand is mentioned in AI responses.

## Base URL
```
POST /analyze
```

## Authentication
API keys are provided in the request body for each AI service you want to analyze.

---

## Request Schema

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `brand_name` | string | Name of the brand to analyze |
| `brand_url` | string | Brand website URL or specific product URL |
| `product_category` | string | Product category for query generation |
| `api_keys` | object | API keys for different AI services |

### API Keys Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `openai_api_key` | string | Optional | OpenAI API key for GPT models |
| `gemini_api_key` | string | Optional | Google Gemini API key |
| `perplexity_api_key` | string | Optional | Perplexity API key |

**Note**: At least one API key must be provided.

### Optional Configuration Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url_type` | string | "website" | Type of URL: "website" or "product" |
| `sitemap_url` | string | null | Sitemap URL (auto-discovered if not provided) |
| `k` | integer | 30 | Number of queries to generate (6-100) |
| `audience_description` | string | null | Target audience/ICP description |
| `brand_summary` | string | null | Brand summary (skips brand profiling if provided) |
| `brand_products` | string | null | Brand products description |
| `product_description` | string | null | Product description (for product URLs) |
| `product_type` | string | null | Product type/category |
| `include_responses` | boolean | false | Include LLM responses in output |
| `group_name` | string | null | Azure Web PubSub group for real-time updates |
| `indexing_batch_size` | integer | 500 | Batch size for embedding operations (10-1000) |
| `use_concurrent_indexing` | boolean | true | Use concurrent indexing for performance |
| `use_pinecone` | boolean | true | Use Pinecone for persistent vector storage |
| `force_reindex` | boolean | false | Force re-indexing even if brand exists |
| `custom_query_generation_instructions` | string | null | Custom instructions for query generation |

### Query Control Fields

#### `user_intent` (Optional)
Control which intent types to generate queries for. By default, all intent types are used.

```json
{
  "user_intent": ["informational", "commercial", "awareness"]
}
```

**Valid Intent Types:**
- `"navigational"` - Direct brand/product searches
- `"informational"` - Educational and how-to queries  
- `"commercial"` - Product comparison and research
- `"transactional"` - Purchase-intent queries
- `"awareness"` - Problem recognition and discovery
- `"consideration"` - Solution evaluation and comparison

**Validation Rules:**
- Must be array of valid intent types
- No duplicate intents allowed
- When not provided, all 6 intent types are used by default

#### `queries` (Optional)
Provide pre-defined queries instead of generating them automatically.

```json
{
  "queries": [
    {
      "query": "how to choose the right shoes for work",
      "intent": "informational",
      "sub_intent": "sizing",
      "persona": "novice",
      "category": "women's shoes",
      "expected_brand_relevance": "medium",
      "locale": "en-AU",
      "notes": "Users want guidance on selecting comfortable and professional footwear for the workplace."
    }
  ]
}
```

**Required Fields per Query:**
- `query` (string) - The search query text
- `intent` (string) - One of the valid intent types above
- `sub_intent` (string) - Specific sub-category (e.g., "sizing", "care", "comparison")
- `persona` (string) - User type (e.g., "novice", "enthusiast", "budget_shopper")
- `category` (string) - Product category
- `expected_brand_relevance` (string) - "low", "medium", or "high"
- `locale` (string) - IETF language tag (e.g., "en-US", "en-AU")
- `notes` (string) - Description of why this query exists

**Validation Rules:**
- Maximum 100 pre-defined queries
- Cannot be empty array if provided
- When provided, skips query generation entirely

---

## Example Requests

### Basic Request
```json
{
  "brand_name": "Nike",
  "brand_url": "https://nike.com",
  "product_category": "athletic footwear",
  "api_keys": {
    "openai_api_key": "sk-...",
    "gemini_api_key": "AI..."
  }
}
```

### Using User Intent Control
```json
{
  "brand_name": "Nike",
  "brand_url": "https://nike.com",
  "product_category": "athletic footwear",
  "api_keys": {
    "openai_api_key": "sk-..."
  },
  "user_intent": ["informational", "commercial"],
  "k": 20
}
```

### Using Pre-defined Queries
```json
{
  "brand_name": "Nike",
  "brand_url": "https://nike.com",
  "product_category": "athletic footwear",
  "api_keys": {
    "openai_api_key": "sk-..."
  },
  "queries": [
    {
      "query": "best running shoes for beginners",
      "intent": "informational",
      "sub_intent": "comparison",
      "persona": "novice",
      "category": "athletic footwear",
      "expected_brand_relevance": "high",
      "locale": "en-US",
      "notes": "New runners seeking guidance on shoe selection"
    },
    {
      "query": "Nike vs Adidas running shoes",
      "intent": "commercial",
      "sub_intent": "comparison",
      "persona": "enthusiast",
      "category": "athletic footwear",
      "expected_brand_relevance": "high",
      "locale": "en-US",
      "notes": "Direct brand comparison for purchase decision"
    }
  ]
}
```

### Product-Specific Analysis
```json
{
  "brand_name": "Nike Air Max 270",
  "brand_url": "https://nike.com/t/air-max-270-mens-shoes",
  "url_type": "product",
  "product_category": "athletic footwear",
  "api_keys": {
    "openai_api_key": "sk-...",
    "gemini_api_key": "AI...",
    "perplexity_api_key": "pplx-..."
  },
  "k": 50
}
```

---

## Response Schema

### Success Response (200)

```json
{
  "brand_name": "Nike",
  "brand_visibility_metrics": {
    "average_citation_percentage": 45.7,
    "total_queries_analyzed": 30,
    "queries_with_citations": 18,
    "llm_performance": {
      "ChatOpenAI": {
        "citation_rate": 43.3,
        "total_mentions": 52
      },
      "ChatGoogleGenerativeAI": {
        "citation_rate": 50.0,
        "total_mentions": 48
      }
    },
    "intent_visibility_breakdown": {
      "informational": {
        "total_queries": 15,
        "queries_with_citations": 8,
        "average_citation_percentage": 42.2,
        "citation_rate": 53.3
      },
      "awareness": {
        "total_queries": 15,
        "queries_with_citations": 10,
        "average_citation_percentage": 49.1,
        "citation_rate": 66.7
      }
    }
  },
  "query_analyses": {
    "best running shoes for beginners": {
      "overall_citation_percentage": 66.7,
      "total_mentions": 3,
      "llm_breakdown": {
        "ChatOpenAI": {
          "cited": true,
          "mention_count": 2,
          "visibility_score": 1.0,
          "response": "When choosing running shoes...",
          "sentences_with_brand": [
            "Nike offers excellent options for beginners.",
            "The Nike Air Zoom series is particularly recommended."
          ]
        }
      },
      "explanation": "2 out of 3 AI assistants mentioned Nike."
    }
  },
  "timing_breakdown": {
    "total_duration_seconds": 45.23,
    "sitemap_discovery": 2.1,
    "content_indexing": 8.5,
    "query_generation": 5.2,
    "context_retrieval": 12.4,
    "llm_analysis": 15.8,
    "citation_analysis": 1.23
  }
}
```

### Response Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| `brand_name` | string | The analyzed brand name |
| `brand_visibility_metrics` | object | Overall visibility statistics |
| `query_analyses` | object | Per-query citation analysis results |
| `timing_breakdown` | object | Performance timing for each step |

#### Brand Visibility Metrics

| Field | Type | Description |
|-------|------|-------------|
| `average_citation_percentage` | number | Average visibility across all queries (0-100) |
| `total_queries_analyzed` | integer | Number of queries processed |
| `queries_with_citations` | integer | Queries where at least one LLM mentioned the brand |
| `llm_performance` | object | Per-LLM citation statistics |
| `intent_visibility_breakdown` | object | Visibility breakdown by intent type |

#### Query Analysis Object

| Field | Type | Description |
|-------|------|-------------|
| `overall_citation_percentage` | number | Percentage of LLMs that mentioned the brand (0-100) |
| `total_mentions` | integer | Total brand mentions across all LLMs |
| `llm_breakdown` | object | Detailed results per LLM |
| `explanation` | string | Human-readable summary |

#### LLM Breakdown Object

| Field | Type | Description |
|-------|------|-------------|
| `cited` | boolean | Whether this LLM mentioned the brand |
| `mention_count` | integer | Number of times brand was mentioned |
| `visibility_score` | number | 1.0 if cited, 0.0 if not |
| `response` | string | Full LLM response (if `include_responses: true`) |
| `sentences_with_brand` | array | Sentences containing brand mentions |

---

## Error Response Formats

### Validation Errors (422)

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "user_intent"],
      "msg": "Invalid intent types: ['invalid_intent']. Valid values: ['navigational', 'informational', 'commercial', 'transactional', 'awareness', 'consideration']",
      "input": ["invalid_intent"]
    }
  ]
}
```

### Common Validation Error Types

#### Invalid Intent Types
```json
{
  "detail": [
    {
      "type": "value_error", 
      "loc": ["body", "user_intent"],
      "msg": "Invalid intent types: ['shopping', 'buying']. Valid values: ['navigational', 'informational', 'commercial', 'transactional', 'awareness', 'consideration']"
    }
  ]
}
```

#### Duplicate Intent Types
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "user_intent"], 
      "msg": "Duplicate intent types are not allowed"
    }
  ]
}
```

#### Missing Query Fields
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "queries"],
      "msg": "Query 1 missing required fields: ['intent', 'persona']"
    }
  ]
}
```

#### No API Keys Provided
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "api_keys"],
      "msg": "At least one API key must be provided (openai_api_key, gemini_api_key, or perplexity_api_key)"
    }
  ]
}
```

#### Invalid URL Type
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "url_type"],
      "msg": "url_type must be either 'website' or 'product'"
    }
  ]
}
```

#### Invalid Plan
```json
{
  "detail": [
    {
      "type": "value_error",
    }
  ]
}
```

#### Query Count Out of Range
```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "k"],
      "msg": "Input should be greater than or equal to 6"
    }
  ]
}
```

#### Too Many Pre-defined Queries
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "queries"],
      "msg": "Maximum 100 pre-defined queries allowed"
    }
  ]
}
```

#### Empty Queries Array
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "queries"],
      "msg": "queries field cannot be empty if provided"
    }
  ]
}
```

### Processing Errors (500)

#### Query Generation Failed
```json
{
  "error": "Query generation error",
  "message": "Failed to generate queries: OpenAI API key is invalid",
  "request_id": "req_abc123"
}
```

#### Context Retrieval Failed  
```json
{
  "error": "Context retrieval error",
  "message": "Session is closed",
  "request_id": "req_abc123"
}
```

#### LLM Analysis Failed
```json
{
  "error": "LLM analysis error", 
  "message": "All LLM calls failed: Rate limit exceeded",
  "request_id": "req_abc123"
}
```

#### External Service Error
```json
{
  "error": "External service error",
  "message": "Pinecone service unavailable",
  "request_id": "req_abc123"
}
```

---

## Query Generation Behavior

### Priority Order

1. **Pre-defined Queries** (`queries` field provided)
   - Skips generation entirely
   - Uses provided queries as-is
   - Validates required fields

2. **User Intent Control** (`user_intent` field provided)
   - Generates queries only for specified intents
   - Distributes `k` queries evenly across specified intents
   - Controls which intent types are generated

3. **All Intent Generation** (default)
   - Uses all 6 intent types with business-priority distribution

### Intent Distribution Examples

#### User Intent: `["informational", "commercial"]` with k=20
```json
{
  "navigational": 0,
  "informational": 10,
  "commercial": 10, 
  "transactional": 0,
  "awareness": 0,
  "consideration": 0
}
```

#### Free Plan with k=30
```json
{
  "navigational": 0,
  "informational": 15,
  "commercial": 0,
  "transactional": 0,
  "awareness": 15,
  "consideration": 0
}
```

#### Paid Plan with k=30
```json
{
  "navigational": 5,
  "informational": 5,
  "commercial": 5,
  "transactional": 5,
  "awareness": 5,
  "consideration": 5
}
```

---

## Rate Limits & Performance

### Concurrent Limits
- **OpenAI**: 50 concurrent requests
- **Gemini**: 15 concurrent requests  
- **Perplexity**: 8 concurrent requests
- **Context Downloads**: 50 concurrent connections

### Typical Response Times
- **Small Analysis** (k=6): 15-30 seconds
- **Medium Analysis** (k=30): 30-60 seconds
- **Large Analysis** (k=100): 60-120 seconds

### Performance Optimizations
- Parallel query generation by intent type
- Concurrent LLM calls across all providers
- Smart context retrieval with session recovery
- Pinecone namespace caching to avoid re-indexing

---

## Usage Tips

### For Best Results

1. **Use Specific Brand Names**: More specific brand names get better citation rates
2. **Provide Brand Context**: Include `brand_summary` and `brand_products` for better context
3. **Choose Relevant Categories**: Match `product_category` to your actual business
4. **Test Intent Types**: Different intents yield different citation patterns
5. **Monitor Timing**: Use `timing_breakdown` to identify bottlenecks

### Intent Selection Guide

- **Navigational**: High citation rate, direct brand searches
- **Commercial**: Medium citation rate, comparison contexts  
- **Informational**: Lower citation rate, educational content
- **Transactional**: High citation rate, purchase-focused
- **Awareness**: Low citation rate, problem discovery
- **Consideration**: Medium citation rate, solution evaluation

### Pre-defined Queries Best Practices

- Use realistic, natural search queries
- Include variety in query length and complexity
- Match `expected_brand_relevance` to actual query intent
- Use appropriate locale for target market
- Balance across different personas and sub-intents

---

## Support

For questions about API usage, integration, or troubleshooting, please refer to the error messages and response formats above. The API provides detailed error information to help debug issues quickly.