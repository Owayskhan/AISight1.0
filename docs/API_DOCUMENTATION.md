# Citation Count API - Complete Documentation

## Overview

The Citation Count API analyzes brand visibility across multiple AI assistants (ChatGPT, Google Gemini, and Perplexity) to measure how often your brand appears in AI-generated responses. This helps businesses understand their brand presence in the AI-powered search landscape.

## Base URL
```
http://localhost:8000
```

## Authentication
The API uses API keys passed in request bodies. No header-based authentication is required.

---

## Endpoints

### POST /analyze
Analyzes brand citation patterns across multiple AI assistants.

#### Request Format
```http
POST /analyze
Content-Type: application/json

{
  "brand_name": "string",
  "brand_url": "string", 
  "url_type": "website|product",
  "product_category": "string",
  "api_keys": {
    "openai_api_key": "string",
    "gemini_api_key": "string (optional)",
    "perplexity_api_key": "string (optional)"
  },
  // ... additional parameters
}
```

#### Required Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `brand_name` | string | Name of the brand to analyze |
| `brand_url` | string | Website or product page URL |
| `url_type` | string | Either "website" or "product" |
| `product_category` | string | Product category for query generation |
| `api_keys` | object | API keys for external services |

##### API Keys Object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `openai_api_key` | string | Yes | OpenAI API key for embeddings and query generation |
| `gemini_api_key` | string | No | Google Gemini API key for brand profiling |
| `perplexity_api_key` | string | No | Perplexity API key for citation analysis |

#### Optional Parameters

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `k` | integer | 30 | 6-100 | Number of queries to generate |
| `sitemap_url` | string | null | - | Custom sitemap URL (auto-discovered if not provided) |
| `audience_description` | string | null | - | Target audience description |
| `brand_summary` | string | null | - | Brand description (skips auto-profiling) |
| `brand_products` | string | null | - | Product list (skips auto-profiling) |
| `product_description` | string | null | - | Product description for product analysis |
| `product_type` | string | null | - | Product type for product analysis |
| `include_responses` | boolean | false | - | Include full LLM responses in output |
| `group_name` | string | null | - | Azure Web PubSub group for real-time updates |
| `indexing_batch_size` | integer | 500 | 10-1000 | Batch size for embedding operations |
| `use_concurrent_indexing` | boolean | true | - | Enable concurrent indexing |
| `use_pinecone` | boolean | true | - | Use Pinecone for persistent vector storage |
| `force_reindex` | boolean | false | - | Force re-indexing of existing brand data |
| `custom_query_generation_instructions` | string | null | - | Custom instructions for query generation |
| `plan` | string | "free" | "free"|"paid" | Subscription plan affecting query types |

#### Request Examples

##### Website Analysis
```json
{
  "brand_name": "Novo Shoes",
  "brand_url": "https://www.novoshoes.com.au",
  "url_type": "website",
  "product_category": "Women's Footwear",
  "k": 30,
  "api_keys": {
    "openai_api_key": "sk-proj-...",
    "gemini_api_key": "AIza...",
    "perplexity_api_key": "pplx-..."
  },
  "audience_description": "Fashion-conscious women aged 25-40",
  "plan": "paid"
}
```

##### Product Analysis
```json
{
  "brand_name": "Novo Shoes",
  "brand_url": "https://www.novoshoes.com.au/products/stiletto-heels",
  "url_type": "product", 
  "product_category": "High Heels",
  "k": 20,
  "api_keys": {
    "openai_api_key": "sk-proj-..."
  },
  "product_description": "Elegant stiletto heels perfect for evening wear",
  "product_type": "footwear",
  "plan": "free"
}
```

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
      "intent": "string",
      "sub_intent": "string",
      "persona": "string",
      "category": "string",
      "expected_brand_relevance": "string",
      "locale": "string",
      "notes": "string"
    }
  ],
  "intent_distribution": {
    "navigational": integer,
    "informational": integer,
    "commercial": integer,
    "transactional": integer,
    "awareness": integer,
    "consideration": integer
  },
  "citation_analysis": {
    "query_text": {
      "overall_citation_percentage": float,
      "total_mentions": integer,
      "llm_breakdown": {
        "openai": {
          "cited": boolean,
          "mention_count": integer,
          "visibility_score": float,
          "response": "string",
          "sentences_with_brand": ["string"]
        },
        "gemini": { /* same structure */ },
        "perplexity": { /* same structure */ }
      },
      "explanation": "string"
    }
  },
  "overall_brand_visibility": {
    "average_citation_percentage": float,
    "total_queries": integer,
    "queries_with_citations": integer,
    "intent_breakdown": {
      "intent_name": {
        "citation_percentage": float,
        "queries_count": integer,
        "citations_count": integer
      }
    },
    "llm_breakdown": {
      "llm_name": {
        "citation_percentage": float,
        "total_citations": integer,
        "queries_processed": integer
      }
    }
  },
  "plan_used": "string"
}
```

#### Response Examples

##### Successful Analysis
```json
{
  "brand_profile": {
    "icp": "Fashion-forward women aged 25-45 seeking stylish, affordable footwear",
    "products": ["heels", "flats", "boots", "sandals"],
    "summary": "Australian fashion footwear brand offering trendy shoes for modern women",
    "locales": ["en-AU", "en-US"],
    "is_international": true
  },
  "queries": [
    {
      "query": "best women's heels for office wear",
      "intent": "commercial",
      "sub_intent": "product_comparison", 
      "persona": "professional_woman",
      "category": "Women's Footwear",
      "expected_brand_relevance": "high",
      "locale": "en-AU",
      "notes": "Professional seeking work-appropriate footwear"
    }
  ],
  "intent_distribution": {
    "awareness": 8,
    "consideration": 7,
    "commercial": 8,
    "transactional": 4,
    "informational": 3,
    "navigational": 0
  },
  "citation_analysis": {
    "best women's heels for office wear": {
      "overall_citation_percentage": 66.67,
      "total_mentions": 2,
      "llm_breakdown": {
        "openai": {
          "cited": true,
          "mention_count": 1,
          "visibility_score": 1.0,
          "response": "For office wear, consider Novo Shoes which offers stylish yet professional heels...",
          "sentences_with_brand": ["Novo Shoes offers excellent office heels with comfort features."]
        },
        "gemini": {
          "cited": true,
          "mention_count": 1,
          "visibility_score": 1.0,
          "response": "Novo shoes provides great options for professional footwear...",
          "sentences_with_brand": ["Novo shoes are known for their office-appropriate styles."]
        },
        "perplexity": {
          "cited": false,
          "mention_count": 0,
          "visibility_score": 0.0,
          "response": "Popular office heel brands include Cole Haan, Clarks, and Nine West...",
          "sentences_with_brand": []
        }
      },
      "explanation": "Brand mentioned by OpenAI and Gemini but not Perplexity (66.67% visibility)"
    }
  },
  "overall_brand_visibility": {
    "average_citation_percentage": 45.5,
    "total_queries": 30,
    "queries_with_citations": 18,
    "intent_breakdown": {
      "commercial": {
        "citation_percentage": 62.5,
        "queries_count": 8,
        "citations_count": 5
      }
    },
    "llm_breakdown": {
      "openai": {
        "citation_percentage": 56.7,
        "total_citations": 17,
        "queries_processed": 30
      }
    }
  },
  "plan_used": "paid"
}
```

#### Error Responses

##### 400 Bad Request - Invalid Parameters
```json
{
  "detail": "At least one API key must be provided (openai_api_key, gemini_api_key, or perplexity_api_key)"
}
```

##### 400 Bad Request - Sitemap Not Found
```json
{
  "detail": "Could not find sitemap for https://example.com"
}
```

##### 500 Internal Server Error - Processing Failed
```json
{
  "detail": "❌ Context retrieval failed: Session is closed"
}
```

### GET /
Returns API information and health status.

#### Response
```json
{
  "message": "Citation Count API - Analyze brand visibility across AI assistants",
  "version": "1.0.0",
  "endpoints": {
    "analyze": "POST /analyze - Analyze brand citations",
    "health": "GET / - API health check"
  }
}
```

---

## Query Intent Types

The API generates queries based on different customer journey stages:

| Intent | Description | Free Plan | Examples |
|--------|-------------|-----------|----------|
| `awareness` | Brand/category discovery | ✅ | "what are the best shoe brands", "types of women's footwear" |
| `informational` | Learning about products | ✅ | "how to choose heel height", "shoe care tips" |
| `consideration` | Comparing options | ❌ | "Novo vs Wittner shoes comparison", "best heel brands under $100" |
| `commercial` | Ready to purchase | ❌ | "where to buy Novo shoes", "Novo shoes discount code" |
| `transactional` | Purchase intent | ❌ | "buy Novo black heels online", "Novo shoes checkout" |
| `navigational` | Finding specific pages | ❌ | "Novo shoes website", "Novo store locations" |

## Subscription Plans

### Free Plan
- **Query Types**: Informational and awareness only
- **Query Count**: Up to 100 queries
- **Features**: Basic citation analysis, website/product analysis

### Paid Plan  
- **Query Types**: All 6 intent types
- **Query Count**: Unlimited
- **Features**: Complete customer journey analysis, advanced insights

---

## Real-time Progress Updates

The API supports real-time progress updates via Azure Web PubSub:

1. Provide a `group_name` in your request
2. Connect to the WebPubSub hub using the group name
3. Receive progress updates during processing

### Progress Stages
1. `starting` - Analysis initiated
2. `indexing_brand_data` - Processing website/product content
3. `collecting_brand_data` - Gathering brand information
4. `generating_queries` - Creating customer queries
5. `running_queries` - Testing queries against AI assistants
6. `generating_report` - Compiling results
7. `completed` - Analysis finished

---

## Rate Limits & Performance

### API Limits
- **Concurrent requests**: 5 per client
- **Query generation**: Up to 100 queries per request
- **Processing time**: 5-15 minutes depending on website size

### Performance Optimization
- **Pinecone caching**: Reuses indexed content for faster processing
- **Concurrent processing**: Parallel query execution
- **Batch processing**: Efficient embedding operations

### Usage Recommendations
- Use `use_pinecone=true` for faster repeat analysis
- Set appropriate `indexing_batch_size` (500 recommended)
- Enable `use_concurrent_indexing` for large websites
- Provide `brand_summary` to skip auto-profiling

---

## Error Handling & Troubleshooting

### Common Issues

1. **API Key Validation Failed**
   - Ensure API keys are valid and have sufficient credits
   - At least OpenAI key is required

2. **Sitemap Not Found**
   - Check if website has accessible sitemap.xml
   - Provide custom `sitemap_url` if needed
   - Consider using `url_type: "product"` for single pages

3. **Session Closed Errors**
   - Automatically handled with retry logic
   - Contact support if persistent

4. **Rate Limiting**
   - Built-in backoff and retry mechanisms
   - Monitor API quotas for external services

### Support
- GitHub Issues: [Repository Issues](https://github.com/your-org/conversions-digital/issues)
- Email: support@yourcompany.com

---

## SDK & Code Examples

### Python Example
```python
import requests

# Basic website analysis
response = requests.post('http://localhost:8000/analyze', json={
    "brand_name": "Your Brand",
    "brand_url": "https://yourbrand.com", 
    "url_type": "website",
    "product_category": "Your Category",
    "api_keys": {
        "openai_api_key": "sk-..."
    }
})

result = response.json()
print(f"Brand visibility: {result['overall_brand_visibility']['average_citation_percentage']}%")
```

### cURL Example
```bash
curl -X POST "http://localhost:8000/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Your Brand",
    "brand_url": "https://yourbrand.com",
    "url_type": "website", 
    "product_category": "Your Category",
    "api_keys": {
      "openai_api_key": "sk-..."
    }
  }'
```

---

## Changelog

### v1.0.0
- Initial API release
- Website and product analysis
- Multi-LLM citation analysis
- Real-time progress updates
- Pinecone integration for performance
- Free and paid plan support