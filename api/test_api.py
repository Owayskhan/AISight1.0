import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API endpoint
url = "http://localhost:8000/analyze"

# Get API keys from environment variables
def get_api_keys():
    """Get API keys from environment variables with validation."""
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GOOGLE_API_KEY")  # Note: Using GOOGLE_API_KEY for Gemini
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not openai_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    
    # At least OpenAI key is required, others are optional
    return {
        "openai_api_key": openai_key,
        "gemini_api_key": gemini_key,
        "perplexity_api_key": perplexity_key
    }

def create_test_data():
    """Create test data with API keys from environment variables."""
    try:
        api_keys = get_api_keys()
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("Please set the required environment variables in your .env file")
        exit(1)
    
    # Test request data for website analysis
    website_test_data = {
        "brand_name": "Novo Shoes",
        "brand_url": "https://www.novoshoes.com.au",
        "url_type": "website",
        "product_category": "Women's Footwear",
        "k": 5,
        "api_keys": api_keys
    }

    # Test request data for single product analysis
    product_test_data = {
        "brand_name": "Novo Shoes",
        "brand_url": "https://www.novoshoes.com.au/products/some-specific-shoe",
        "url_type": "product",
        "product_category": "Women's Heels",
        "k": 5,
        "api_keys": api_keys,
        # Optional: provide product details to skip extraction
        "brand_summary": "Stylish high heel perfect for evening wear",
        "brand_products": "Available in multiple colors and sizes"
    }
    
    return website_test_data, product_test_data

def test_api(test_data):
    """Test the Citation Count API with the provided data."""
    try:
        print("Testing Citation Count API...")
        print(f"URL: {url}")
        
        # Create a safe copy of test data for display (hide API keys)
        display_data = test_data.copy()
        display_data["api_keys"] = {
            "openai_api_key": "***" if test_data["api_keys"]["openai_api_key"] else None,
            "gemini_api_key": "***" if test_data["api_keys"]["gemini_api_key"] else None, 
            "perplexity_api_key": "***" if test_data["api_keys"]["perplexity_api_key"] else None
        }
        print(f"Request data: {json.dumps(display_data, indent=2)}")
        
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
    print("🔧 Citation Count API Test Script")
    print("=" * 40)
    
    # Create test data with environment variables
    website_data, product_data = create_test_data()
    
    print("Choose test type:")
    print("1. Website analysis (default)")
    print("2. Product analysis") 
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        print("\n--- Testing Product Analysis ---")
        test_api(product_data)
    else:
        print("\n--- Testing Website Analysis ---")
        test_api(website_data)