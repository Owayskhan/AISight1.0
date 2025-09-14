# Testing the Citation Analysis API

## ⚠️ Important Security Notice

**NEVER commit real API keys to version control!** 

The test files in this repository use placeholder values like `"your-openai-key"`. You must replace these with your actual API keys before testing.

## Quick Setup

### 1. Get API Keys

You need API keys from these services:

- **OpenAI**: https://platform.openai.com/api-keys
- **Google Gemini**: https://makersuite.google.com/app/apikey  
- **Perplexity**: https://www.perplexity.ai/settings/api

### 2. Update Test File

Edit `api/test_api.py` and replace the placeholder values:

```python
"api_keys": {
    "openai_api_key": "sk-proj-YOUR_ACTUAL_OPENAI_KEY",
    "gemini_api_key": "AIza-YOUR_ACTUAL_GEMINI_KEY", 
    "perplexity_api_key": "pplx-YOUR_ACTUAL_PERPLEXITY_KEY"
}
```

### 3. Run Tests

```bash
# Start the API server
python api/main.py

# In another terminal, run tests
python api/test_api.py
```

## Test Options

The test file includes three test scenarios:

### Website Analysis (Default)
```python
website_test_data = {
    "brand_name": "Novo Shoes",
    "brand_url": "https://www.novoshoes.com.au", 
    "url_type": "website",
    "product_category": "Women's Footwear",
    "k": 5
}
```

### Product Analysis
```python
product_test_data = {
    "brand_name": "Novo Shoes",
    "brand_url": "https://www.novoshoes.com.au/products/some-specific-shoe",
    "url_type": "product", 
    "product_category": "Women's Heels",
    "k": 5
}
```

## Safety Tips

1. **Never commit real API keys**: Always use placeholders in committed code
2. **Use environment variables**: For production, load keys from environment variables
3. **Revoke compromised keys**: If you accidentally commit keys, revoke them immediately
4. **Use .gitignore**: Keep sensitive files out of version control

## Environment Variable Alternative

Instead of editing the test file, you can set environment variables:

```bash
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"
export PERPLEXITY_API_KEY="your-perplexity-key"
```

Then modify the test to use `os.getenv()`:

```python
import os

"api_keys": {
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    "gemini_api_key": os.getenv("GEMINI_API_KEY"), 
    "perplexity_api_key": os.getenv("PERPLEXITY_API_KEY")
}
```

## Troubleshooting

- **Connection Error**: Make sure the API server is running on port 8000
- **401 Unauthorized**: Check that your API keys are valid
- **Rate Limits**: Start with small test cases (k=3 or k=5)
- **Timeouts**: Reduce the number of queries if requests time out