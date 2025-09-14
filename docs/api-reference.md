# API Reference

## Base URL
```
http://localhost:8000
```

## Authentication
This API requires API keys for external AI services. No authentication is required for the API itself.

## Endpoints

### POST /analyze
Analyzes brand citation patterns across multiple AI assistants.

#### Request Body

```json
{
  "brand_name": "string",
  "brand_url": "string", 
  "url_type": "website|product",
  "product_category": "string",
  "api_keys": {
    "openai_api_key": "string",
    "gemini_api_key": "string", 
    "perplexity_api_key": "string"
  },
  "k": 10,
  "sitemap_url": "string (optional)",
  "audience_description": "string (optional)",
  "brand_summary": "string (optional)", 
  "brand_products": "string (optional)",
  "product_description": "string (optional)",
  "product_type": "string (optional)"
}
```

#### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `brand_name` | string | Yes | Name of the brand to analyze |
| `brand_url` | string | Yes | Website URL or specific product URL |
| `url_type` | string | Yes | Either "website" or "product" |
| `product_category` | string | Yes | Product category for query generation |
| `api_keys` | object | Yes | API keys for AI services |
| `k` | integer | No | Number of queries to generate (1-50, default: 10) |
| `sitemap_url` | string | No | Sitemap URL (auto-discovered if not provided) |
| `audience_description` | string | No | Target audience description |
| `brand_summary` | string | No | Brand summary |
| `brand_products` | string | No | Brand products description |
| `product_description` | string | No | Product description (product mode only) |
| `product_type` | string | No | Product type (product mode only) |

#### API Keys Object

```json
{
  "openai_api_key": "sk-...",
  "gemini_api_key": "AIza...",
  "perplexity_api_key": "pplx-..."
}
```

#### URL Types

**Website Mode (`url_type: "website"`)**
- Analyzes entire website through sitemap
- Generates category-based queries
- Longer processing time but comprehensive results

**Product Mode (`url_type: "product"`)** 
- Analyzes single product page
- Generates product-specific queries
- Faster processing, focused results
- Content is chunked using markdown headers

#### Response Format

```json
{
  "brand_profile": {
    "icp": "string",
    "products": ["string"],
    "summary": "string", 
    "locales": ["string"],
    "is_international": boolean
  },
  "queries": [
    {
      "query": "string",
      "intent": "awareness|consideration|transactional|information",
      "sub_intent": "string",
      "persona": "string", 
      "category": "string",
      "expected_brand_relevance": "high|medium|low",
      "locale": "string",
      "notes": "string"
    }
  ],
  "citation_analysis": {
    "query_text": {
      "overall_citation_percentage": 66.7,
      "total_mentions": 3,
      "explanation": "string",
      "llm_breakdown": {
        "ChatOpenAI": {
          "cited": true,
          "mention_count": 2,
          "visibility_score": 1.0,
          "response": "string",
          "sentences_with_brand": ["string"]
        },
        "ChatGoogleGenerativeAI": {
          "cited": true, 
          "mention_count": 1,
          "visibility_score": 1.0,
          "response": "string",
          "sentences_with_brand": ["string"]
        },
        "ChatPerplexity": {
          "cited": false,
          "mention_count": 0, 
          "visibility_score": 0.0,
          "response": "string",
          "sentences_with_brand": []
        }
      }
    }
  },
  "overall_brand_visibility": {
    "average_citation_percentage": 45.2,
    "total_queries_analyzed": 10,
    "queries_with_citations": 7,
    "llm_performance": {
      "ChatOpenAI": {
        "citation_rate": 60.0,
        "total_mentions": 15
      },
      "ChatGoogleGenerativeAI": {
        "citation_rate": 40.0,
        "total_mentions": 8  
      },
      "ChatPerplexity": {
        "citation_rate": 30.0,
        "total_mentions": 5
      }
    }
  }
}
```

#### Response Fields

**Brand Profile**
- `icp`: Ideal customer profile description
- `products`: List of product types offered
- `summary`: Brand summary 
- `locales`: Target markets/locales
- `is_international`: Whether brand operates internationally

**Queries Array**
- `query`: The generated customer question
- `intent`: Customer journey stage (awareness, consideration, transactional, information)
- `sub_intent`: Specific query type (compare, features, pricing, etc.)
- `persona`: Customer type (novice, enthusiast, pro, etc.)
- `category`: Product category
- `expected_brand_relevance`: How relevant the brand should be for this query
- `locale`: Language/region code
- `notes`: Explanation of why this query would be asked

**Citation Analysis**
- `overall_citation_percentage`: Percentage of AI assistants that mentioned the brand (0-100)
- `total_mentions`: Total brand mentions across all AI responses
- `explanation`: Human-readable summary of results
- `llm_breakdown`: Per-AI-assistant detailed results

**LLM Breakdown Object**
- `cited`: Boolean indicating if brand was mentioned
- `mention_count`: Number of times brand was mentioned
- `visibility_score`: 1.0 if cited, 0.0 if not cited  
- `response`: Full AI assistant response
- `sentences_with_brand`: Array of sentences containing brand mentions

**Overall Brand Visibility**
- `average_citation_percentage`: Average visibility across all queries
- `total_queries_analyzed`: Number of queries processed
- `queries_with_citations`: Number of queries with at least one brand mention
- `llm_performance`: Performance statistics per AI assistant

#### Status Codes

- `200`: Success
- `400`: Bad request (invalid parameters or missing data)
- `500`: Internal server error

#### Error Response Format

```json
{
  "detail": "Error description"
}
```

## Query Intent Types

All generated queries are classified into exactly one of these customer journey stages:

- **awareness**: Discovery and learning queries about the product category
- **consideration**: Evaluation, comparison, and decision-making queries  
- **transactional**: Purchase-related queries (where to buy, pricing, deals)
- **information**: Usage, specifications, maintenance, and how-to queries

## Citation Percentage Calculation

The citation percentage represents brand visibility:

```
Citation Percentage = (Number of AI assistants mentioning brand / 3) × 100
```

Possible values:
- **0%**: No AI assistants mentioned the brand
- **33.3%**: One AI assistant mentioned the brand  
- **66.7%**: Two AI assistants mentioned the brand
- **100%**: All three AI assistants mentioned the brand

## Processing Flow

1. **Content Analysis**: Load and process website or product page content
2. **Brand Profiling**: Extract brand information and target audience (if not provided)
3. **Query Generation**: Create realistic customer questions using AI
4. **Context Retrieval**: Find relevant content for each query
5. **AI Response Generation**: Get responses from ChatGPT, Gemini, and Perplexity
6. **Citation Analysis**: Analyze each response for brand mentions
7. **Results Aggregation**: Calculate visibility metrics and performance statistics

## Rate Limits and Performance

- **Processing Time**: 2-15 minutes depending on analysis type and query count
- **API Limits**: Subject to limits of underlying AI services (OpenAI, Google, Perplexity)
- **Recommended Query Count**: Start with 5-10 queries for testing, up to 50 for comprehensive analysis
- **Concurrent Requests**: Process one analysis at a time for optimal performance

## Example Requests

### Basic Website Analysis
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Acme Corp",
    "brand_url": "https://acmecorp.com", 
    "url_type": "website",
    "product_category": "Software Tools",
    "k": 5,
    "api_keys": {
      "openai_api_key": "sk-...",
      "gemini_api_key": "AIza...",
      "perplexity_api_key": "pplx-..."
    }
  }'
```

### Product Analysis with Custom Description
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "SuperShoes Pro",
    "brand_url": "https://acmecorp.com/products/supershoes-pro",
    "url_type": "product", 
    "product_category": "Athletic Footwear",
    "product_description": "High-performance running shoes with advanced cushioning",
    "product_type": "running shoes",
    "k": 5,
    "api_keys": {
      "openai_api_key": "sk-...",
      "gemini_api_key": "AIza...", 
      "perplexity_api_key": "pplx-..."
    }
  }'
```

## Development Setup

### Running the API

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn api.main:app --reload

# Or run directly
python api/main.py
```

### Environment Variables
The API can optionally use environment variables for configuration:
- `OPENAI_API_KEY`: Default OpenAI API key
- `GOOGLE_API_KEY`: Default Google API key  
- `PERPLEXITY_API_KEY`: Default Perplexity API key

### Testing
```bash
# Run basic test
python api/test_api.py
```

## Troubleshooting

### Common Issues

**Sitemap Not Found**
- Ensure website has a publicly accessible sitemap.xml
- Try providing explicit sitemap URL
- Use product mode as alternative

**API Key Errors**  
- Verify API keys are valid and have sufficient credits
- Check API key format (OpenAI: sk-..., Gemini: AIza..., Perplexity: pplx-...)
- Ensure keys have required permissions

**Timeout Errors**
- Reduce query count (k parameter)  
- Check internet connection
- Verify external API services are operational

**Low Citation Rates**
- Normal for new or niche brands
- Indicates opportunities for content optimization
- Consider improving product descriptions and website content