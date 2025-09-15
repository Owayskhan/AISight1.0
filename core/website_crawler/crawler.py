
from langchain_community.document_loaders import WebBaseLoader
import requests
from xml.etree import ElementTree as ET
from langchain.schema import Document
from urllib.parse import urljoin, urlparse
import re
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import json
import html2text
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_openai import ChatOpenAI
from core.models.main import ProductInfo

def find_sitemap_url(website_url: str) -> str:
    """
    Dynamically find the sitemap URL for a given website.
    Tries common sitemap locations in order.
    """
    # Ensure URL has proper scheme
    if not urlparse(website_url).scheme:
        website_url = f"https://{website_url}"
    
    # Common sitemap locations
    sitemap_paths = [
        '/sitemap.xml',
        '/sitemap_index.xml',
        '/sitemap-index.xml',
        '/sitemaps.xml',
        '/sitemap/',
        '/sitemap.txt',
        '/sitemap.xml.gz',
        '/robots.txt'  # Check robots.txt for sitemap reference
    ]
    
    for path in sitemap_paths:
        sitemap_url = urljoin(website_url, path)
        try:
            response = requests.get(sitemap_url, timeout=10)
            if response.status_code == 200:
                # Check if it's robots.txt
                if path == '/robots.txt':
                    # Parse robots.txt for sitemap URL
                    for line in response.text.splitlines():
                        if line.lower().startswith('sitemap:'):
                            return line.split(':', 1)[1].strip()
                else:
                    # Check if it's valid XML
                    try:
                        ET.fromstring(response.content)
                        return sitemap_url
                    except ET.ParseError:
                        continue
        except Exception:
            continue
    
    # If no sitemap found, raise exception
    raise ValueError(f"Could not find sitemap for {website_url}")

def load_sitemap_documents(sitemap_url: str):
    sitemap = get_sitemap_urls(sitemap_url)

    sitemap_docs = []
    for url in sitemap:
        doc = Document(
            page_content=url, metadata={"source": url}
        )
        sitemap_docs.append(doc)
    
    return sitemap_docs

async def extract_product_info_llm(page_content: str, openai_api_key: str) -> ProductInfo:
    """
    Extract product information using LLM with structured output
    """
    llm = ChatOpenAI(api_key=openai_api_key, model="gpt-4o-mini", temperature=0)
    
    prompt = f"""
    Analyze the following product page content and extract two pieces of information:
    
    1. Product Description: A brief 1-2 sentence description of what the product is and what it does
    2. Product Type: The category or type of product (e.g., 'sneakers', 'laptop', 'skincare cream', 'dress', 'headphones')
    
    Product Page Content:
    {page_content[:3000]}  # Limit content to avoid token limits
    
    Please provide a concise and accurate analysis.
    """
    
    try:
        result = await llm.with_structured_output(ProductInfo).ainvoke(prompt)
        return result
    except Exception as e:
        # Fallback if extraction fails
        return ProductInfo(
            product_description="Product description",
            product_type="product"
        )

async def load_single_product_document(product_url: str, openai_api_key: str, 
                                      product_description: Optional[str] = None, 
                                      product_type: Optional[str] = None) -> List[Document]:
    """Load a single product page and chunk it using markdown text splitter based on headers"""
    loader = WebBaseLoader(product_url)
    docs = loader.load()
    
    if not docs:
        return []
    
    # Extract product information - use provided info or extract with LLM
    html_content = docs[0].page_content
    if product_description and product_type:
        product_info = ProductInfo(
            product_description=product_description,
            product_type=product_type
        )
    else:
        product_info = await extract_product_info_llm(html_content, openai_api_key)
    
    # Convert HTML to markdown for better structure recognition
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    markdown_content = h.handle(html_content)
    
    # Define headers to split on (H1 through H6)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"), 
        ("###", "Header 3"),
        ("####", "Header 4"),
        ("#####", "Header 5"),
        ("######", "Header 6"),
    ]
    
    # Initialize the markdown splitter
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    try:
        # Split the markdown content based on headers
        md_header_splits = markdown_splitter.split_text(markdown_content)
        
        # Convert back to Document objects with proper metadata
        chunked_docs = []
        for i, split in enumerate(md_header_splits):
            doc = Document(
                page_content=split.page_content,
                metadata={
                    "content_type": "chunked_content",
                    "document_type": "product",
                    "source": product_url,
                    "chunk_index": i,
                    "chunk_type": "markdown_header",
                    **split.metadata  # Include header metadata from the splitter
                }
            )
            
            # Add extracted product information to metadata
            doc.metadata.update({
                "product_description": product_info.product_description,
                "product_type": product_info.product_type
            })
            
            chunked_docs.append(doc)
        
        # If no splits were made (no headers found), return the original content as a single chunk
        if not chunked_docs:
            doc = Document(
                page_content=markdown_content,
                metadata={
                    "content_type": "full_content",
                    "document_type": "product", 
                    "source": product_url,
                    "chunk_index": 0,
                    "chunk_type": "full_document"
                }
            )
            
            doc.metadata.update({
                "product_description": product_info.product_description,
                "product_type": product_info.product_type
            })
            
            chunked_docs = [doc]
        
        return chunked_docs
        
    except Exception as e:
        # Fallback to original content if markdown splitting fails
        doc = Document(
            page_content=html_content,
            metadata={
                "content_type": "full_content",
                "document_type": "product",
                "source": product_url,
                "chunk_index": 0,
                "chunk_type": "fallback",
                "split_error": str(e)
            }
        )
        
        doc.metadata.update({
            "product_description": product_info.product_description,
            "product_type": product_info.product_type
        })
        
        return [doc]

def get_sitemap_urls(url):
    response = requests.get(url)

    # Parse the XML
    root = ET.fromstring(response.content)

    namespace = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    urls = []

    for url_element in root.findall('.//ns:loc', namespace):
        urls.append(url_element.text)
    
    return urls




