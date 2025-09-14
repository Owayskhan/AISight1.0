import requests
import json

# API endpoint
url = "http://localhost:8000/analyze"

# Test request data - REPLACE WITH YOUR ACTUAL API KEYS
real_test_data = {
    "brand_name": "Novo Shoes",
    "brand_url": "https://www.novoshoes.com.au",
    "url_type": "website",
    "product_category": "fashion shoes",
    "k": 5,
    "api_keys": {
        "openai_api_key": "your-openai-key-here",
        "gemini_api_key": "your-gemini-key-here",
        "perplexity_api_key": "your-perplexity-key-here"
    }
}

# Test request data for website analysis
website_test_data = {
    "brand_name": "Novo Shoes",
    "brand_url": "https://www.novoshoes.com.au",
    "url_type": "website",
    "product_category": "Women's Footwear",
    "k": 5,
    "api_keys": {
        "openai_api_key": "your-openai-key",
        "gemini_api_key": "your-gemini-key",
        "perplexity_api_key": "your-perplexity-key"
    }
}

# Test request data for single product analysis
product_test_data = {
    "brand_name": "Novo Shoes",
    "brand_url": "https://www.novoshoes.com.au/products/some-specific-shoe",
    "url_type": "product",
    "product_category": "Women's Heels",
    "k": 5,
    "api_keys": {
        "openai_api_key": "your-openai-key",
        "gemini_api_key": "your-gemini-key",
        "perplexity_api_key": "your-perplexity-key"
    },
    # Optional: provide product details to skip extraction
    "brand_summary": "Stylish high heel perfect for evening wear",
    "brand_products": "Available in multiple colors and sizes"
}

def test_api(test_data=website_test_data):
    try:
        print("Testing Citation Count API...")
        print(f"URL: {url}")
        print(f"Request data: {json.dumps(test_data, indent=2)}")
        
        # Make the request
        response = requests.post(url, json=test_data)
        
        # Check response
        if response.status_code == 200:
            print("\n✅ Success!")
            result = response.json()
            
            print(f"\n📊 Brand Profile:")
            print(json.dumps(result['brand_profile'], indent=2))
            
            print(f"\n🔍 Generated {len(result['queries'])} queries")
            
            print(f"\n📈 Citation Analysis Summary:")
            for query, analysis in result['citation_analysis'].items():
                print(f"\nQuery: {query}")
                print(f"Overall Visibility: {analysis['overall_citation_percentage']}%")
                print(f"Explanation: {analysis['explanation']}")
        else:
            print(f"\n❌ Error: {response.status_code}")
            print(response.json())
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Choose test type:")
    print("1. Website analysis (default)")
    print("2. Product analysis")
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        print("\n--- Testing Product Analysis ---")
        test_api(product_test_data)
    else:
        print("\n--- Testing Website Analysis ---")
        test_api(website_test_data)