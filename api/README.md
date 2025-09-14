# Citation Count API

FastAPI endpoint that analyzes how often different LLMs mention a brand when answering queries.

## Installation

```bash
pip install -r requirements.txt
```

## Running the API

```bash
uvicorn api.main:app --reload
```

Or run directly:
```bash
python api/main.py
```

## API Endpoint

### POST /analyze

Analyzes citation counts for a brand across multiple LLMs. Supports both website-wide analysis and single product analysis.

#### Website Analysis
**Request Body:**
```json
{
  "brand_name": "Example Brand",
  "brand_url": "https://example.com",
  "url_type": "website",
  "product_category": "Electronics",
  "k": 10,
  "api_keys": {
    "openai_api_key": "sk-...",
    "gemini_api_key": "AIza...",
    "perplexity_api_key": "pplx-..."
  }
}
```

#### Single Product Analysis
**Request Body:**
```json
{
  "brand_name": "Example Product",
  "brand_url": "https://example.com/products/specific-product",
  "url_type": "product",
  "product_category": "Electronics",
  "k": 10,
  "api_keys": {
    "openai_api_key": "sk-...",
    "gemini_api_key": "AIza...",
    "perplexity_api_key": "pplx-..."
  }
}
```

#### Parameters:
- `url_type`: Either "website" or "product"
- `sitemap_url` (optional): Only for website type - will be auto-discovered if not provided
- `k` (optional, default=10): Number of queries to generate (1-50)
- `audience_description` (optional): Target audience description
- `brand_summary` (optional): Brand summary
- `brand_products` (optional): Brand products description

#### Query Intent Types:
All generated queries are classified into exactly one of these four intents:
- `awareness`: Discovery and learning queries
- `consideration`: Evaluation and comparison queries  
- `transactional`: Purchase-related queries
- `information`: Usage, specifications, and how-to queries

**Response:**
```json
{
  "brand_profile": {
    "icp": "Target audience description",
    "products": ["Product 1", "Product 2"],
    "summary": "Brand summary",
    "locales": ["en-US"],
    "is_international": false
  },
  "queries": [
    {
      "query": "What are the best hiking boots?",
      "intent": "consideration",
      "persona": "enthusiast",
      "expected_brand_relevance": "high"
    }
  ],
  "citation_analysis": {
    "What are the best hiking boots?": {
      "overall_citation_percentage": 67.0,
      "total_mentions": 3,
      "explanation": "2 out of 3 AI assistants mentioned YourBrand. ✅ Cited by: ChatOpenAI, ChatGoogleGenerativeAI. ❌ Not cited by: ChatPerplexity.",
      "llm_breakdown": {
        "ChatOpenAI": {
          "cited": true,
          "mention_count": 2,
          "visibility_score": 1.0,
          "response": "For hiking boots, I recommend...",
          "sentences_with_brand": ["YourBrand offers excellent durability."]
        },
        "ChatGoogleGenerativeAI": {
          "cited": true,
          "mention_count": 1,
          "visibility_score": 1.0,
          "response": "Great hiking boot options include...",
          "sentences_with_brand": ["YourBrand is highly rated."]
        },
        "ChatPerplexity": {
          "cited": false,
          "mention_count": 0,
          "visibility_score": 0.0,
          "response": "Top hiking boots include various brands...",
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

## Citation Count as Visibility Percentage

**Citation Logic:**
- Each LLM can contribute either 0 or 1 citation (binary)
- **Citation Percentage = (Number of LLMs mentioning brand / 3) × 100**
- Possible values: 0% (no LLMs), 33.3% (1 LLM), 66.7% (2 LLMs), 100% (all 3 LLMs)

**Key Metrics:**
- `overall_citation_percentage`: Visibility for this specific query (0-100%)
- `total_mentions`: Total number of brand mentions across all LLMs
- `explanation`: Human-readable summary of results
- `average_citation_percentage`: Brand visibility across all queries

## Flow

1. Extracts and indexes sitemap URLs
2. Generates brand profile using Tavily search + Gemini
3. Generates relevant queries based on product category
4. Retrieves context for each query from indexed URLs
5. Gets answers from multiple LLMs (OpenAI, Gemini, Perplexity)
6. Counts brand citations in each response