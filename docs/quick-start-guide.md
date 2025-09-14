# Quick Start Guide

## Getting Started in 5 Minutes

This guide will help you run your first brand citation analysis quickly and easily.

## What You'll Need

### Required Items
- Your brand name (e.g., "Nike", "Apple", "Acme Corp")
- Your website URL (e.g., "https://yourcompany.com")
- Product category (e.g., "athletic shoes", "smartphones", "skincare")
- API keys for AI services (see setup instructions below)

### API Key Setup
You'll need access to three AI services:

1. **OpenAI API Key**
   - Visit: https://platform.openai.com/api-keys
   - Create account and generate API key
   - Starts with "sk-..."

2. **Google Gemini API Key** 
   - Visit: https://makersuite.google.com/app/apikey
   - Create API key
   - Starts with "AIza..."

3. **Perplexity API Key**
   - Visit: https://www.perplexity.ai/settings/api
   - Generate API key
   - Starts with "pplx-..."

## Running Your First Analysis

### Option 1: Website Analysis (Recommended for First-Time Users)

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

### Option 2: Product Analysis (For Specific Products)

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

## Understanding Your Results

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

## Common Use Cases

### Brand Health Check
Run a website analysis with 10-15 questions to get a comprehensive view of your brand's AI visibility across your product range.

### New Product Testing  
Use product analysis to test how well AI assistants know about your latest product launches.

### Competitive Benchmarking
Run analysis for competitors' websites to understand the competitive landscape in AI recommendations.

### Content Impact Measurement
Run analysis before and after major website updates to measure the impact on AI visibility.

## Tips for Better Results

### Optimize Your Success
1. **Use clear product categories**: "running shoes" works better than "footwear products"
2. **Keep brand names simple**: Use the name customers actually search for
3. **Test regularly**: AI assistant knowledge updates frequently
4. **Start small**: Begin with 5 questions, then increase for more comprehensive analysis

### Troubleshooting Common Issues

**"No sitemap found" error**
- Your website might not have a sitemap
- Try using product analysis mode instead
- Contact your web developer to add a sitemap

**Low visibility scores**
- This is normal for new brands or products
- Focus on creating more comprehensive product information
- Consider SEO and content marketing improvements

**Analysis takes too long**
- Start with fewer questions (k=3 or k=5)
- Use product analysis for faster results
- Check your internet connection

## Next Steps

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

## Support and Resources

### Getting Help
- Check the full documentation for detailed explanations
- Review the API reference for technical details
- Test with small question counts first to avoid issues

### Best Practices
- Keep API keys secure and don't share them
- Monitor your API usage to avoid unexpected costs  
- Run analyses during business hours for better API performance
- Save your results for comparison over time

## Example Success Story

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

The citation analysis system provided the insights needed to make targeted improvements and measure their impact over time.