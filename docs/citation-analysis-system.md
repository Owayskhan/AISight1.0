# Brand Citation Analysis System

## Overview

The Brand Citation Analysis System is a tool that measures how often different AI assistants mention your brand when answering customer questions. This helps you understand your brand's "visibility" in AI-powered search results, which is becoming increasingly important as more people use AI assistants for product research and purchasing decisions.

## What It Does

The system simulates real customer behavior by:

1. **Generating realistic customer questions** about your products or industry
2. **Asking multiple AI assistants** (ChatGPT, Google Gemini, and Perplexity) these questions
3. **Analyzing the responses** to see which AI assistants mention your brand
4. **Calculating visibility scores** to show how prominently your brand appears in AI recommendations

## Key Features

### Brand Visibility Measurement
- **Visibility Percentage**: Shows what percentage of AI assistants mention your brand for each question (0-100%)
- **Overall Performance**: Provides average visibility across all questions tested
- **AI Assistant Breakdown**: Shows which specific AI assistants mention your brand most often

### Two Analysis Modes

#### Website Analysis Mode
- Analyzes your entire website to understand your brand and products
- Automatically discovers and indexes your website content
- Generates questions relevant to your product categories
- Best for: Comprehensive brand visibility analysis across your full product range

#### Product Analysis Mode  
- Focuses on a specific product page
- Breaks down the product page into logical sections for better analysis
- Generates questions specific to that individual product
- Best for: Testing visibility of specific products or new launches

### Intelligent Question Generation
- Creates realistic questions that real customers would ask
- Covers different stages of the customer journey:
  - **Awareness**: "What are the best options for [product type]?"
  - **Consideration**: "How does [product A] compare to [product B]?"
  - **Purchase**: "Where can I buy [product type] online?"
  - **Usage**: "How do I set up [product type]?"

### Automated Content Processing
- Automatically extracts key information from your website or product pages
- Converts content into searchable format for AI assistants
- No manual data entry required

## How It Works

### Step 1: Content Analysis
The system examines your website or product page to understand:
- What products you offer
- Who your target customers are
- Key features and benefits
- Your brand positioning

### Step 2: Question Generation
Based on your content, the system creates realistic customer questions that might lead to AI recommendations, such as:
- "What are the best running shoes for beginners?"
- "Which laptop brands offer the best value for money?"
- "Where can I find eco-friendly skincare products?"

### Step 3: AI Assistant Testing
The system asks each generated question to three major AI assistants:
- **ChatGPT** (OpenAI)
- **Google Gemini** (Google)
- **Perplexity** (Perplexity AI)

### Step 4: Citation Analysis
For each AI response, the system:
- Identifies whether your brand was mentioned
- Counts how many times it was mentioned
- Records the specific sentences where your brand appeared

### Step 5: Visibility Scoring
Results are calculated as percentages:
- **0%**: No AI assistants mentioned your brand
- **33.3%**: One out of three AI assistants mentioned your brand
- **66.7%**: Two out of three AI assistants mentioned your brand
- **100%**: All three AI assistants mentioned your brand

## Understanding Your Results

### Visibility Percentage
This is the most important metric. It shows what percentage of AI assistants mentioned your brand when answering a specific question. Higher percentages indicate better AI visibility.

### Citation Breakdown
For each question, you'll see:
- **Which AI assistants mentioned your brand** (✅ Cited)
- **Which AI assistants didn't mention your brand** (❌ Not cited)
- **The exact sentences** where your brand was mentioned
- **Total mention count** across all responses

### Overall Performance Metrics
- **Average Citation Percentage**: Your brand's overall visibility across all questions
- **Questions with Citations**: How many questions resulted in at least one brand mention
- **AI Assistant Performance**: Which AI assistants mention your brand most consistently

## Use Cases

### Brand Monitoring
- Track how often your brand appears in AI recommendations
- Monitor changes in AI visibility over time
- Compare your visibility across different product categories

### Competitive Analysis
- Understand which brands dominate AI recommendations in your space
- Identify opportunities where competitors have low AI visibility
- Benchmark your performance against industry standards

### Content Strategy
- Identify topics where your brand has low AI visibility
- Optimize website content to improve AI discoverability
- Test the impact of content changes on AI recommendations

### Product Launch Support
- Measure AI visibility for new products before and after launch
- Identify which product features get mentioned by AI assistants
- Optimize product descriptions for better AI discovery

## Getting Started

### Required Information
To use the system, you need:
- **Brand name**: Your company or product brand name
- **Website URL or Product URL**: Link to analyze
- **Product category**: General category (e.g., "athletic footwear", "smartphones")
- **API keys**: Access credentials for the AI services

### Optional Information
You can also provide:
- **Target audience description**: Who your ideal customers are
- **Brand summary**: Brief description of your brand
- **Product details**: Specific product descriptions and types

### Analysis Types
Choose between:
- **Website Analysis**: Comprehensive analysis of your entire brand presence
- **Product Analysis**: Focused analysis of a specific product

## Understanding Limitations

### What This Measures
- How often AI assistants mention your brand in responses
- Which AI assistants are more likely to recommend your brand
- Your brand's relative visibility in AI-powered search

### What This Doesn't Measure
- Traditional search engine rankings
- Social media mentions or sentiment
- Direct sales attribution from AI recommendations
- Customer satisfaction or brand loyalty

### Important Considerations
- AI assistant responses can vary based on timing and updates to their training data
- Results represent a snapshot in time and may change
- Higher visibility doesn't guarantee sales, but indicates stronger AI discoverability
- The system tests specific question types and may not cover all possible customer queries

## System Architecture

### Technology Stack

**Backend Framework**
- **FastAPI**: High-performance Python web framework for the API
- **Pydantic**: Data validation and settings management
- **Asyncio**: Asynchronous programming for concurrent operations

**AI and ML Services**
- **OpenAI GPT-4o-mini**: Fast query generation and citation analysis
- **Google Gemini 2.5**: Brand profiling and answer generation
- **Perplexity AI Sonar**: Search-based response generation
- **LangChain**: AI workflow orchestration and prompt management

**Vector Database and Search**
- **Pinecone**: Vector database for persistent content storage
- **OpenAI Embeddings**: Text-to-vector conversion for semantic search
- **FAISS**: Local vector search capabilities

**Web Crawling and Content Processing**
- **Beautiful Soup**: HTML parsing and content extraction
- **aiohttp**: Asynchronous HTTP client for concurrent web requests
- **html2text**: HTML to markdown conversion
- **Sitemap discovery**: Automated website structure analysis

**Performance and Reliability**
- **Robust Session Manager**: Multi-strategy download system with fallback
- **Rate Limiting**: Token bucket algorithms for API compliance
- **Connection Pooling**: Optimized HTTP connection management
- **Progressive Concurrency**: Adaptive scaling based on network conditions

### System Components

#### 1. **Content Indexing Pipeline**
```
Website URL → Sitemap Discovery → Content Crawling → 
Text Extraction → Embedding Generation → Vector Storage
```

#### 2. **Query Generation System**
```
Brand Profiling → Intent Analysis → Parallel Generation → 
Query Validation → Distribution Balancing
```

#### 3. **Context Retrieval Engine**
```
Query Input → Vector Search → Content Retrieval → 
Session Management → Result Assembly
```

#### 4. **LLM Analysis Pipeline**
```
Query + Context → Concurrent LLM Calls → Response Collection → 
Citation Detection → Visibility Calculation
```

### Performance Optimizations

**Parallel Processing**
- Concurrent query generation by intent type (4x speed improvement)
- Parallel LLM calls across all providers
- Batch vector store operations with controlled concurrency

**Smart Caching**
- Pinecone namespace detection to avoid re-indexing
- Query context caching to eliminate duplicate API calls
- Connection pooling for reduced latency

**Adaptive Scaling**
- Progressive concurrency reduction for stability
- Automatic fallback strategies for failed downloads
- Rate limiting with exponential backoff

### Configuration and Deployment

**Environment Variables**
- API keys for all AI services
- Pinecone configuration (index, environment)
- Concurrency limits and timeout settings

**Docker Support**
- Containerized deployment with docker-compose
- Environment-specific configuration
- Scalable architecture for high-volume usage

**Monitoring and Logging**
- Comprehensive timing breakdowns for performance analysis
- Detailed error logging with request ID tracking
- Real-time progress updates via Azure Web PubSub

## Technical Requirements

### Supported Content Types
- Standard websites with HTML content
- Product pages with structured information
- Sites with accessible sitemaps
- JSON-LD structured data
- Meta tags and schema markup

### AI Services Integration
- **OpenAI GPT-4o-mini**: Query generation, citation analysis
- **Google Gemini 2.5-Flash**: Brand profiling, response generation
- **Perplexity AI Sonar**: Search-enhanced responses
- **Custom prompts**: Optimized for natural citation patterns

### Performance Specifications
- **Concurrent Limits**: 25 downloads, 50 OpenAI requests, 15 Gemini requests
- **Vector Operations**: 15-query batches for optimal Pinecone performance
- **Session Recovery**: 4-strategy fallback system for 99%+ reliability
- **Response Times**: 15-60 seconds typical, scales with query count

### Processing Time
- **Small Analysis** (k=6, free plan): 15-30 seconds
- **Medium Analysis** (k=30, paid plan): 30-60 seconds  
- **Large Analysis** (k=100, paid plan): 60-120 seconds
- **Time varies** based on website size, query complexity, and API response times

## Best Practices

### For Accurate Results
- Ensure your website content is up-to-date and comprehensive
- Use clear, descriptive product names and categories
- Provide detailed product descriptions and features
- Keep brand information consistent across your website

### For Actionable Insights
- Run analysis regularly to track changes over time
- Test different product categories to identify strengths and gaps
- Compare results before and after content updates
- Focus on questions relevant to your target customers' journey

### For Maximum Value
- Use results to guide content optimization efforts
- Share insights with marketing and product teams
- Integrate findings into broader digital marketing strategy
- Consider AI visibility alongside traditional SEO metrics