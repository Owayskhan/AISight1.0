# Citation Count API - Setup & Quick Start Guide

Get your brand citation analysis running in 5 minutes, or dive into detailed installation and configuration.

## 🚀 Quick Start (5 Minutes)

### What You'll Need
- Your brand name (e.g., "Nike", "Apple", "Acme Corp")
- Your website URL (e.g., "https://yourcompany.com")
- Product category (e.g., "athletic shoes", "smartphones", "skincare")
- OpenAI API key (required)

### 1. Get Your OpenAI API Key
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-` or `sk-`)

### 2. Quick Test (Skip Installation)
Use this simple test to see if the API works for you:

```bash
curl -X POST "https://your-api-endpoint.com/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "brand_name": "Your Brand Name",
    "brand_url": "https://yourwebsite.com",
    "url_type": "website",
    "product_category": "Your Product Category",
    "k": 5,
    "api_keys": {
      "openai_api_key": "sk-proj-your-actual-key-here"
    }
  }'
```

**What this does:**
- Analyzes your entire website
- Generates 5 realistic customer questions
- Tests how often AI assistants mention your brand
- Takes 5-10 minutes to complete

### Understanding Your Results

**Overall Brand Visibility Scores:**
- **60-100%**: Excellent visibility - your brand appears frequently in AI responses
- **30-60%**: Good visibility - your brand appears regularly but has room for improvement  
- **10-30%**: Moderate visibility - your brand appears occasionally
- **0-10%**: Low visibility - your brand rarely appears in AI responses

---

## 💻 Full Installation

### System Requirements

#### Minimum Requirements
- **Python**: 3.12 or higher
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB free space
- **Internet**: Stable connection for API calls
- **OS**: Linux, macOS, or Windows

#### Recommended Setup
- **Python**: 3.12+ with virtual environment
- **RAM**: 16GB for large website analysis
- **CPU**: Multi-core processor for concurrent processing
- **Storage**: SSD for better performance

### Installation Steps

#### 1. Clone the Repository
```bash
git clone https://github.com/your-org/conversions-digital.git
cd conversions-digital
```

#### 2. Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies
```bash
pip install -r api/requirements.txt
```

#### 4. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys
nano .env  # or use your preferred editor
```

#### 5. Configure API Keys
Edit the `.env` file with your actual API keys:

```env
# Required
OPENAI_API_KEY=sk-proj-your-actual-openai-key-here

# Optional (but recommended)
GOOGLE_API_KEY=AIzaSy-your-actual-google-key-here
PERPLEXITY_API_KEY=pplx-your-actual-perplexity-key-here

# Optional: Pinecone for better performance
PINECONE_API_KEY=pcsk_your-actual-pinecone-key-here
PINECONE_INDEX_NAME=citation-analysis

# Optional: Azure Web PubSub for real-time updates
AZURE_WEBPUBSUB_HUB_NAME=your-hub-name
AZURE_WEBPUBSUB_CONNECTION_STRING=Endpoint=https://your-endpoint.azure.com;...
```

#### 6. Start the API Server
```bash
cd api
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at: `http://localhost:8000`

---

## 🔑 API Key Setup Guide

### Required API Keys

#### OpenAI API Key (Required)
1. Visit [OpenAI Platform](https://platform.openai.com/api-keys)
2. Sign in or create account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-proj-` or `sk-`)
5. Add to `.env` as `OPENAI_API_KEY`

**Cost Estimate**: $0.50-5.00 per analysis depending on website size

### Optional API Keys (For Better Results)

#### Google Gemini API Key (Recommended)
1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Create or select a project
3. Click "Create API Key"
4. Copy the key (starts with `AIza`)
5. Add to `.env` as `GOOGLE_API_KEY`

**Usage**: Used for brand profiling when brand information isn't provided

#### Perplexity API Key (Optional)
1. Visit [Perplexity API](https://www.perplexity.ai/settings/api)
2. Sign up for API access
3. Generate API key
4. Copy the key (starts with `pplx-`)
5. Add to `.env` as `PERPLEXITY_API_KEY`

**Usage**: Adds Perplexity to citation analysis (3 LLMs instead of 2)

#### Pinecone API Key (Recommended for Production)
1. Visit [Pinecone Console](https://app.pinecone.io/)
2. Create account and project
3. Go to API Keys section
4. Copy the API key (starts with `pcsk_`)
5. Add to `.env` as `PINECONE_API_KEY`

**Benefits**: Persistent vector storage, faster repeated analysis

---

## ✅ Testing Your Installation

### 1. Health Check
```bash
curl http://localhost:8000/
```

Expected response:
```json
{
  "message": "Citation Count API - Analyze brand visibility across AI assistants",
  "version": "1.0.0"
}
```

### 2. Run Test Script
```bash
cd api
python test_api.py
```

Follow the prompts to test website or product analysis.

### 3. Your First Analysis

#### Option 1: Website Analysis (Recommended for First-Time Users)
```json
{
  "brand_name": "Your Brand Name",
  "brand_url": "https://yourwebsite.com",
  "url_type": "website",
  "product_category": "Your Product Category",
  "k": 5,
  "api_keys": {
    "openai_api_key": "your-openai-key",
    "gemini_api_key": "your-gemini-key", 
    "perplexity_api_key": "your-perplexity-key"
  }
}
```

**What this does:**
- Analyzes your entire website
- Generates 5 realistic customer questions
- Tests how often AI assistants mention your brand
- Takes 5-10 minutes to complete

#### Option 2: Product Analysis (For Specific Products)
```json
{
  "brand_name": "Your Product Name",
  "brand_url": "https://yourwebsite.com/products/specific-product",
  "url_type": "product", 
  "product_category": "Product Type",
  "k": 5,
  "api_keys": {
    "openai_api_key": "your-openai-key",
    "gemini_api_key": "your-gemini-key",
    "perplexity_api_key": "your-perplexity-key"
  }
}
```

**What this does:**
- Focuses on one specific product page
- Generates product-specific questions
- Analyzes content in logical sections
- Takes 2-5 minutes to complete

---

## 📊 Understanding Your Results

### Key Metrics to Look For

**Overall Brand Visibility**
- **60-100%**: Excellent visibility - your brand appears frequently in AI responses
- **30-60%**: Good visibility - your brand appears regularly but has room for improvement  
- **10-30%**: Moderate visibility - your brand appears occasionally
- **0-10%**: Low visibility - your brand rarely appears in AI responses

**Questions with Citations**
- Shows how many of your test questions resulted in brand mentions
- Higher numbers indicate broader AI visibility across topics

**AI Assistant Breakdown**
- **ChatGPT**: Most widely used, high importance
- **Google Gemini**: Growing usage, integrated with Google services
- **Perplexity**: Popular for research queries

### Sample Results Explanation

```
Average Citation Percentage: 45.2%
Total Queries Analyzed: 5
Queries with Citations: 3 out of 5

AI Performance:
- ChatGPT: 60% citation rate (3 out of 5 questions)  
- Google Gemini: 40% citation rate (2 out of 5 questions)
- Perplexity: 20% citation rate (1 out of 5 questions)
```

**What this means:**
- Your brand was mentioned in 45% of all AI responses
- 3 out of 5 questions resulted in at least one brand mention
- ChatGPT mentions your brand most frequently
- Perplexity mentions your brand least frequently

---

## ⚙️ Configuration & Performance

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | - | OpenAI API key for embeddings and generation |
| `GOOGLE_API_KEY` | No | - | Google Gemini API key for brand profiling |
| `PERPLEXITY_API_KEY` | No | - | Perplexity API key for citation analysis |
| `PINECONE_API_KEY` | No | - | Pinecone API key for vector storage |
| `PINECONE_INDEX_NAME` | No | citation-analysis | Pinecone index name |
| `AZURE_WEBPUBSUB_HUB_NAME` | No | - | Azure Web PubSub hub name |
| `AZURE_WEBPUBSUB_CONNECTION_STRING` | No | - | Azure Web PubSub connection string |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Performance Tuning

#### Memory Optimization
```python
# For large websites, adjust batch sizes
{
  "indexing_batch_size": 200,  # Reduce if memory issues
  "k": 20                      # Reduce query count for testing
}
```

#### Concurrent Processing
```python
# Enable for better performance
{
  "use_concurrent_indexing": true,
  "use_pinecone": true  # Highly recommended
}
```

---

## 🐳 Docker Setup (Alternative)

### Using Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  citation-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - PERPLEXITY_API_KEY=${PERPLEXITY_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
    volumes:
      - ./.env:/app/.env
```

### Build and Run
```bash
docker-compose up --build
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Import Errors
**Problem**: `ModuleNotFoundError: No module named 'core'`
**Solution**: Ensure you're running from the correct directory:
```bash
cd /path/to/conversions-digital
cd api
python -m uvicorn main:app --reload
```

#### 2. API Key Errors
**Problem**: `At least one API key must be provided`
**Solution**: Check your `.env` file:
```bash
# Verify .env exists and has correct format
cat .env | grep OPENAI_API_KEY
```

#### 3. Memory Issues
**Problem**: Out of memory during large website analysis
**Solution**: Reduce batch sizes:
```json
{
  "indexing_batch_size": 100,
  "k": 10
}
```

#### 4. "No sitemap found" error
**Problem**: Your website might not have a sitemap
**Solutions**:
- Try using product analysis mode instead
- Contact your web developer to add a sitemap
- Provide custom sitemap URL:
```json
{
  "sitemap_url": "https://example.com/sitemap.xml"
}
```

#### 5. Low visibility scores
**Problem**: This is normal for new brands or products
**Solutions**:
- Focus on creating more comprehensive product information
- Consider SEO and content marketing improvements
- Add detailed product specifications to website

#### 6. Analysis takes too long
**Solutions**:
- Start with fewer questions (k=3 or k=5)
- Use product analysis for faster results
- Check your internet connection
- Enable Pinecone for persistent storage

### Debug Mode
Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
python -m uvicorn main:app --reload
```

---

## 🚀 Common Use Cases & Tips

### Use Cases

#### Brand Health Check
Run a website analysis with 10-15 questions to get a comprehensive view of your brand's AI visibility across your product range.

#### New Product Testing  
Use product analysis to test how well AI assistants know about your latest product launches.

#### Competitive Benchmarking
Run analysis for competitors' websites to understand the competitive landscape in AI recommendations.

#### Content Impact Measurement
Run analysis before and after major website updates to measure the impact on AI visibility.

### Tips for Better Results

#### Optimize Your Success
1. **Use clear product categories**: "running shoes" works better than "footwear products"
2. **Keep brand names simple**: Use the name customers actually search for
3. **Test regularly**: AI assistant knowledge updates frequently
4. **Start small**: Begin with 5 questions, then increase for more comprehensive analysis

### Best Practices
- Keep API keys secure and don't share them
- Monitor your API usage to avoid unexpected costs  
- Run analyses during business hours for better API performance
- Save your results for comparison over time

---

## 📈 Success Story Example

**Before Analysis:**
- Brand rarely appeared in AI responses
- Unclear which products were being discovered by AI
- No visibility into competitive AI landscape

**After Using the System:**
- Identified that product descriptions were too generic
- Discovered ChatGPT favored brands with detailed specifications  
- Improved website content with specific product features
- Increased average visibility from 15% to 65% over 3 months

**Key Actions Taken:**
1. Added detailed product specifications to website
2. Created FAQ sections for top products
3. Optimized product category descriptions
4. Regular monitoring and content updates

---

## 🏭 Production Deployment

### Recommended Stack
- **Server**: Ubuntu 20.04+ or similar
- **Process Manager**: Gunicorn with multiple workers
- **Reverse Proxy**: Nginx
- **Monitoring**: Prometheus + Grafana
- **Logging**: Centralized logging (ELK stack)

### Production Configuration
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Security Considerations
1. **Environment Variables**: Use secure secret management
2. **API Keys**: Rotate keys regularly
3. **HTTPS**: Always use SSL in production
4. **Rate Limiting**: Implement request rate limiting
5. **Monitoring**: Monitor API usage and costs

---

## 📚 Support & Resources

### Documentation
- [Complete API Documentation](./API_DOCUMENTATION.md)
- [Developer Guide](./DEVELOPER_GUIDE.md)
- [Configuration Reference](./CONFIGURATION.md)

### Getting Help
1. **GitHub Issues**: Report bugs and feature requests
2. **Documentation**: Check existing docs first
3. **Community**: Join our Discord/Slack community
4. **Enterprise Support**: Contact sales for dedicated support

### Useful Commands
```bash
# Check Python version
python --version

# List installed packages
pip list

# Check API server status
curl http://localhost:8000/

# View logs
tail -f citation-api.log

# Test API keys
python -c "import os; print('OpenAI:', bool(os.getenv('OPENAI_API_KEY')))"
```

## 🎯 Next Steps

### After Your First Analysis
1. **Review the generated questions** - Do they match real customer queries?
2. **Check citation patterns** - Which types of questions get more brand mentions?
3. **Identify gaps** - Where is your brand not being mentioned?

### Improving Your Results
1. **Content optimization** - Add more detailed product information to your website
2. **Regular monitoring** - Run monthly analyses to track improvements
3. **Expand testing** - Try different product categories and question types

### Advanced Usage
1. **Bulk analysis** - Test multiple products or categories
2. **Competitive analysis** - Compare your results with competitors
3. **Trend tracking** - Monitor changes over time

Once installation is complete:
1. Read the [Complete API Documentation](./API_DOCUMENTATION.md)
2. Try different analysis types and parameters
3. Explore the [Developer Guide](./DEVELOPER_GUIDE.md)
4. Set up monitoring and logging for production use