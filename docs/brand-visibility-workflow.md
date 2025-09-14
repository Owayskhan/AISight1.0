# Brand Visibility Calculation Workflow Documentation



## Architecture Diagram

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Brand Website  │────▶│ Sitemap Crawler  │────▶│  FAISS Vector   │
│                 │     │                  │     │     Store       │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                           │
                        ┌──────────────────┐               ▼
                        │ Query Generator  │     ┌─────────────────┐
                        │   (LLM-based)    │────▶│ Query-Context   │
                        └──────────────────┘     │    Matching     │
                                                 └────────┬────────┘
                                                          │
┌─────────────────┐     ┌──────────────────┐             ▼
│  LLM Engines    │◀────│ Answer Generator │◀────────────────────────
│ • OpenAI        │     │   (Multi-LLM)    │
│ • Gemini        │     └────────┬─────────┘
│ • Perplexity    │              │
└─────────────────┘              ▼
                        ┌──────────────────┐     ┌─────────────────┐
                        │ Citation Counter │────▶│ Metrics Calc    │
                        │                  │     │ • OMR           │
                        └──────────────────┘     │ • Content Lift  │
                                                 └─────────────────┘
```

## Core Components

### 1. Website Crawling & Indexing

#### Purpose
Indexes the brand's website content to create a searchable knowledge base for retrieval-augmented generation (RAG).

#### Implementation
```python
# Fetch sitemap URLs
def get_sitemap_urls(url):
    response = requests.get(url)
    root = ET.fromstring(response.content)
    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = []
    for url_element in root.findall('.//ns:loc', namespace):
        urls.append(url_element.text)
    return urls

# Create vector store for semantic search
sitemap_docs = []
for url in sitemap:
    doc = Document(page_content=url, metadata={"source": url})
    sitemap_docs.append(doc)

sitemap_vector_store = FAISS(
    embedding_function=embeddings,
    index=index,
    docstore=InMemoryDocstore(),
    index_to_docstore_id={},
)
```

#### Key Features
- Parses XML sitemaps to extract all brand URLs
- Uses OpenAI embeddings (text-embedding-3-small) for semantic similarity
- Stores URLs in FAISS vector database for fast retrieval
- Supports both single page and bulk crawling

### 2. Query Generation System

#### Purpose
Generates realistic user queries that potential customers might ask AI assistants about products in the brand's category.

#### Implementation
```python
query_generation_system_prompt = """
You are a marketing research copilot that generates realistic user queries...
PRIMARY PRINCIPLE
- You ONLY receive PRODUCT_CATEGORIES, AUDIENCE/ICP information, and optional LOCALES.
- You DO NOT know any brand name, website, or product catalog.
- Generate queries that a real user matching the given ICP would ask...
"""

class QueryItem(BaseModel):
    query: str
    intent: str  # e.g., "product comparison", "buying decision"
    persona: str  # e.g., "budget_shopper", "eco_conscious"
    category: str
    expected_brand_relevance: str  # "high", "medium", "low"
    locale: str
    notes: str
```

#### Query Characteristics
- **No brand names**: Ensures unbiased testing
- **Diverse personas**: novice, enthusiast, pro, budget_shopper, eco_conscious, etc.
- **Multiple intents**: discovery, comparison, purchase, troubleshooting
- **Realistic constraints**: budget, sustainability, sizing, region, materials
- **12-20 queries per category**

#### Example Queries
- "What are the best durable shoes for urban commuting?"
- "Comfortable waterproof sneakers under $150"
- "Eco-friendly running shoes for beginners"

### 3. Context Retrieval System

#### Purpose
Matches generated queries with relevant pages from the brand's website to provide context for answer generation.

#### Implementation
```python
retriever = sitemap_vector_store.as_retriever(
    search_type="similarity", 
    search_kwargs={"k": 3}
)

retrived = []
for query in queries.queries:
    # Retrieve top 3 relevant URLs
    context = await retriever.ainvoke(query.query)
    
    # Load full page content
    loaded_pages = [doc.page_content for doc in context]
    loaders = [WebBaseLoader(page) for page in loaded_pages]
    full_docs = []
    for loader in loaders:
        docs = loader.load()
        full_docs.extend(docs)
    
    retrived.append({
        "query": query,
        "context": full_docs
    })
```

#### Key Features
- Semantic similarity search using embeddings
- Retrieves top 3 most relevant pages per query
- Loads complete page content for comprehensive context
- Maintains query-context pairs for downstream processing

### 4. Answer Generation System

#### Purpose
Generates responses to queries using multiple LLM providers, both with and without brand context.

#### Implementation
```python
# Brand RAG prompt (with context)
brand_rag_system_prompt = """
Answer the following query: {query}
Using these web pages extracted from {brand_name}'s main website as context: {context}
"""

# Neutral prompt (without context)
system_prompt_neutral = """
You are a helpful, neutral assistant.
Provide a concise, accurate, and impartial answer.
If brands are relevant, include 2–5 plausible options from your general knowledge.
"""

# Multiple LLM support
openai_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
perplexity_llm = ChatPerplexity(model="sonar", temperature=0)
```

#### Answer Types
1. **Neutral/Organic**: LLM answers without any brand context
2. **Brand RAG**: LLM answers with brand website context
3. **Mixed RAG**: LLM answers with brand + competitor context

### 5. Citation Analysis System

#### Purpose
Analyzes LLM responses to count brand mentions and extract relevant sentences.

#### Implementation
```python
class CitationsCount(BaseModel):
    count: int
    sentences: list[str]

citations_count_prompt = """
Analyse the following response and count how many times 
the brand name {brand_name} is mentioned.
Return the count as an integer and verbatim sentences 
where the brand name is mentioned.
"""

# Example output
CitationsCount(
    count=3,
    sentences=[
        "From Novo Shoes's offerings, while they have urban-style footwear...",
        "...rather than fashion-focused shoes like those from Novo Shoes."
    ]
)
```

#### Features
- Exact brand name matching (including aliases)
- Verbatim sentence extraction
- Structured output for downstream analysis
- Handles multiple brand name variations

### 6. Metrics Calculation

#### Purpose
Calculates key performance indicators to measure brand visibility in AI responses.

#### Core Metrics

##### Organic Mention Rate (OMR)
- **Definition**: Percentage of queries where LLMs mention the brand without any provided context
- **Formula**: `OMR = (Queries with brand mention / Total queries) × 100`
- **Significance**: Measures unprompted brand awareness in AI systems

##### Content Lift (CL)
- **Definition**: Increase in mention rate when brand context is added vs competitor-only context
- **Formula**: `CL = Mention Rate (Brand+Competitor) - Mention Rate (Competitor Only)`
- **Significance**: Measures the effectiveness of brand content in influencing AI recommendations

## Workflow Execution

### Step 1: Initialize Brand Profile
```python
brand_info = {
    "name": "Novo Shoes",
    "url": "https://www.novoshoes.com.au",
    "sitemap": "https://www.novoshoes.com.au/sitemap/sitemap.xml",
    "categories": ["fashion shoes", "women's footwear"],
    "target_audience": "fashion-forward women, urban professionals"
}
```

### Step 2: Index Brand Content
```python
# Fetch and index sitemap
sitemap_urls = get_sitemap_urls(brand_info["sitemap"])
# Create vector store with URLs
sitemap_vector_store = create_vector_store(sitemap_urls)
```

### Step 3: Generate Test Queries
```python
queries = await query_generation_chain.ainvoke({
    "product_category": brand_info["categories"],
    "audience_description": brand_info["target_audience"],
    "locales": ["en-US", "en-AU"]
})
```

### Step 4: Run Visibility Tests
```python
for query in queries:
    # Test 1: Organic response (no context)
    organic_response = neutral_chain.invoke({"query": query})
    
    # Test 2: Brand RAG response
    brand_context = retrieve_context(query)
    brand_response = brand_rag_chain.invoke({
        "query": query,
        "context": brand_context,
        "brand_name": brand_info["name"]
    })
    
    # Count citations
    citations = count_brand_mentions(brand_response, brand_info["name"])
```

### Step 5: Calculate Metrics
```python
# Calculate OMR
organic_mentions = sum(1 for r in organic_responses if has_brand_mention(r))
omr = (organic_mentions / len(queries)) * 100

# Calculate Content Lift
brand_context_mentions = sum(1 for r in brand_responses if has_brand_mention(r))
competitor_only_mentions = sum(1 for r in competitor_responses if has_brand_mention(r))
content_lift = brand_context_mentions - competitor_only_mentions
```

## Configuration Requirements

### Environment Variables
```bash
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
PERPLEXITY_API_KEY=your_perplexity_key
TAVILY_API_KEY=your_tavily_key
```

### Dependencies
```python
# Core libraries
langchain
langchain-openai
langchain-google-genai
langchain-perplexity
langchain-community

# Vector store
faiss-cpu

# Web crawling
crawl4ai
requests
beautifulsoup4

# Data processing
pydantic
pandas
numpy
```

## Usage Example

```python
# Initialize the brand visibility analyzer
analyzer = BrandVisibilityAnalyzer(
    brand_name="Novo Shoes",
    brand_url="https://www.novoshoes.com.au",
    categories=["fashion shoes", "women's footwear"],
    competitors=["Nike", "Adidas", "Clarks"]
)

# Run full analysis
results = await analyzer.run_analysis(
    num_queries=20,
    test_llms=["openai", "gemini", "perplexity"]
)

# Display metrics
print(f"Organic Mention Rate: {results['omr']:.1f}%")
print(f"Content Lift: {results['content_lift']:.1f}%")
print(f"Top performing queries: {results['top_queries']}")
```

## Best Practices

### 1. Query Generation
- Ensure queries reflect real user language and concerns
- Include diverse personas and use cases
- Avoid leading questions that favor any brand
- Test across multiple locales and languages

### 2. Context Retrieval
- Index comprehensive brand content (not just product pages)
- Include educational content, guides, and FAQs
- Regularly update the index as website changes

### 3. LLM Testing
- Use consistent temperature settings (0 for reproducibility)
- Test multiple LLM providers to understand platform differences
- Run multiple iterations to account for variability

### 4. Metrics Interpretation
- OMR < 5%: Low brand visibility, needs awareness building
- OMR 5-15%: Moderate visibility, competitive positioning
- OMR > 15%: Strong visibility, market leader potential
- Positive Content Lift: Brand content effectively influences recommendations
- Negative Content Lift: Competitor content may be more compelling

## Limitations & Considerations

1. **LLM Training Data**: Results depend on when LLMs were last trained
2. **Query Bias**: Generated queries may not perfectly represent all user segments
3. **Context Quality**: Results sensitive to website content quality and structure
4. **Temporal Factors**: Brand visibility can change as LLMs are updated
5. **Regional Variations**: Results may vary significantly by locale

## Future Enhancements

1. **Competitor Analysis**: Detailed comparison with competitor mention rates
2. **Sentiment Analysis**: Understand if mentions are positive, neutral, or negative
3. **Category Benchmarking**: Compare visibility across product categories
4. **Historical Tracking**: Monitor visibility changes over time
5. **A/B Testing**: Test different content strategies for improving visibility