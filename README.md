# Citation Count API 🔍

**Measure your brand's visibility across AI assistants like ChatGPT, Google Gemini, and Perplexity**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 What This Does

The Citation Count API analyzes how often your brand appears in AI-generated responses when users ask relevant questions. As AI assistants become primary sources of information, understanding your brand's visibility in AI responses is crucial for modern marketing strategy.

### Key Features

- **Multi-LLM Analysis**: Test queries against ChatGPT, Google Gemini, and Perplexity simultaneously
- **Intelligent Query Generation**: Creates realistic customer queries based on your product category and audience
- **Customer Journey Mapping**: Analyzes brand visibility across different intent types (awareness, consideration, purchase)
- **Website & Product Analysis**: Supports both full website analysis and individual product page analysis
- **Real-time Progress**: Live updates during processing via WebSockets
- **Performance Optimized**: Pinecone integration for fast repeated analysis

## 🚀 Quick Start

### 1. Installation
```bash
git clone https://github.com/your-org/conversions-digital.git
cd conversions-digital

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r api/requirements.txt
```

### 2. Configure API Keys
```bash
cp .env.example .env
# Edit .env with your API keys
```

Required in `.env`:
```env
OPENAI_API_KEY=sk-proj-your-openai-key-here
GOOGLE_API_KEY=AIzaSy-your-google-key-here  # Optional but recommended
PERPLEXITY_API_KEY=pplx-your-perplexity-key-here  # Optional
```

### 3. Start the API
```bash
cd api
python -m uvicorn main:app --reload
```

### 4. Test Your Setup
```bash
curl http://localhost:8000/
```

## 📊 Usage Examples

### Website Analysis
```python
import requests

response = requests.post('http://localhost:8000/analyze', json={
    "brand_name": "Novo Shoes",
    "brand_url": "https://www.novoshoes.com.au", 
    "url_type": "website",
    "product_category": "Women's Footwear",
    "k": 30,
    "api_keys": {
        "openai_api_key": "sk-proj-...",
        "gemini_api_key": "AIza...",
        "perplexity_api_key": "pplx-..."
    }
})

result = response.json()
print(f"Overall brand visibility: {result['overall_brand_visibility']['average_citation_percentage']}%")
```

### Product Analysis
```python
response = requests.post('http://localhost:8000/analyze', json={
    "brand_name": "Novo Shoes",
    "brand_url": "https://www.novoshoes.com.au/products/stiletto-heels",
    "url_type": "product",
    "product_category": "High Heels",
    "k": 20,
    "api_keys": {
        "openai_api_key": "sk-proj-..."
    }
})
```

## 🧠 How It Works

### 1. **Content Analysis** 📝
- Crawls your website or analyzes product pages
- Creates vector embeddings for semantic search
- Uses Pinecone for persistent storage and fast retrieval

### 2. **Brand Profiling** 🎯
- Automatically generates brand profile (ICP, products, summary)
- Or uses provided brand information
- Identifies target markets and locales

### 3. **Query Generation** ❓
- Creates realistic customer queries using GPT-4
- Maps to customer journey stages:
  - **Awareness**: "best shoe brands for professionals"
  - **Consideration**: "Novo vs Wittner shoes comparison" 
  - **Purchase**: "where to buy Novo shoes online"

### 4. **Multi-LLM Testing** 🤖
- Runs queries against ChatGPT, Gemini, and Perplexity
- Uses semantic search to find relevant context
- Processes queries concurrently for speed

### 5. **Citation Analysis** 📈
- Analyzes each LLM response for brand mentions
- Counts exact brand references
- Calculates visibility scores and percentages

### 6. **Insights & Reporting** 📊
- Overall brand visibility percentage
- Performance by customer journey stage
- LLM-specific breakdown
- Query-level analysis with explanations

## 🎨 Sample Output

```json
{
  "overall_brand_visibility": {
    "average_citation_percentage": 45.5,
    "total_queries": 30,
    "queries_with_citations": 18,
    "intent_breakdown": {
      "commercial": {
        "citation_percentage": 62.5,
        "queries_count": 8,
        "citations_count": 5
      },
      "awareness": {
        "citation_percentage": 31.2,
        "queries_count": 8,
        "citations_count": 3
      }
    },
    "llm_breakdown": {
      "openai": {
        "citation_percentage": 56.7,
        "total_citations": 17,
        "queries_processed": 30
      },
      "gemini": {
        "citation_percentage": 43.3,
        "total_citations": 13,
        "queries_processed": 30
      },
      "perplexity": {
        "citation_percentage": 36.7,
        "total_citations": 11,
        "queries_processed": 30
      }
    }
  }
}
```

## 🔧 Architecture

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   FastAPI       │    │   Vector     │    │   Multi-LLM     │
│   Web Server    │───▶│   Storage    │───▶│   Query Engine  │
│                 │    │   (Pinecone) │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
         │                       │                    │
         ▼                       ▼                    ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Web Crawler   │    │   Embedding  │    │   Citation      │
│   & Content     │    │   Generator  │    │   Analyzer      │
│   Processor     │    │   (OpenAI)   │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## 📚 Documentation

- **[Complete API Documentation](docs/API_DOCUMENTATION.md)** - Full API reference with examples
- **[Setup & Installation Guide](docs/SETUP_GUIDE.md)** - Detailed installation instructions  
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Code structure and development guide
- **[Configuration Reference](docs/CONFIGURATION.md)** - Environment variables and settings

## 🚀 Performance & Scalability

### Optimizations
- **Concurrent Processing**: Parallel query execution and API calls
- **Vector Caching**: Pinecone integration for persistent storage
- **Batch Processing**: Efficient embedding operations
- **Adaptive Scaling**: Dynamic batch sizing based on system load


## 💰 Pricing & Plans

### Free Plan
- ✅ Informational and awareness queries only

### Paid Plan  
- ✅ All 6 intent types (complete customer journey)


## 🛠️ Development

### Project Structure
```
conversions-digital/
├── api/                    # FastAPI application
│   ├── main.py            # API endpoints
│   ├── requirements.txt   # Dependencies
│   └── test_api.py       # Test scripts
├── core/                  # Core business logic
│   ├── config.py         # Configuration constants
│   ├── indexer/          # Vector storage and retrieval
│   ├── queries/          # Query generation and processing  
│   ├── citation_counter/ # Citation analysis
│   └── website_crawler/  # Content extraction
├── docs/                 # Documentation
└── examples/             # Usage examples
```

### Contributing
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🐛 Troubleshooting

### Common Issues
- **API Key Errors**: Ensure all required keys are in `.env`
- **Memory Issues**: Reduce `indexing_batch_size` for large websites
- **Slow Performance**: Enable Pinecone for caching
- **Rate Limiting**: Check API quotas for external services

### Getting Help
- 📖 Check the [troubleshooting guide](docs/SETUP_GUIDE.md#troubleshooting)
- 🐛 [Report issues](https://github.com/your-org/conversions-digital/issues)
- 💬 Join our [community Discord](https://discord.gg/your-server)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 and text embeddings
- **Pinecone** for vector database infrastructure  
- **FastAPI** for the high-performance web framework
- **LangChain** for LLM orchestration tools

---

**Built with ❤️ for the future of AI-powered marketing**
