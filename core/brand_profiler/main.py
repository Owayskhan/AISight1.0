from core.models.main import BrandProfile
from langchain.chat_models import init_chat_model
from langchain_tavily import TavilySearch
from dotenv import load_dotenv
load_dotenv(override=True)
from langchain_core.prompts import ChatPromptTemplate
import os
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import PydanticOutputParser

parser = PydanticOutputParser(pydantic_object=BrandProfile)

brand_profiler_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant that helps researching brand information for a brand. You have expertise in identifying the ICP of a brand and building a contextual profile for the brand."),
    ("user", "Research the brand {brand_name} using the website {brand_url} and build the brand's profile including ICP, products, summary, locale, and whether it is national or international."),
    ("user","format the output in this format: {format_instructions}")
]).partial(format_instructions=parser.get_format_instructions())

def research_brand_info(brand_name: str, brand_url, gemini_api_key: str, tavily_api_key: str = ""):
    model = init_chat_model("gemini-2.5-flash", model_provider="google_genai", api_key=gemini_api_key)
    
    if tavily_api_key:
        search = TavilySearch(max_results=2, tavily_api_key=tavily_api_key)
        model_with_tools = model.bind_tools([search])
        model_w_structured_output = model_with_tools.with_structured_output(BrandProfile)
    else:
        # Without Tavily, just use structured output
        model_w_structured_output = model.with_structured_output(BrandProfile)
    
    chain = brand_profiler_prompt | model_w_structured_output
    response = chain.invoke({"brand_name": brand_name, "brand_url": brand_url})

    return response