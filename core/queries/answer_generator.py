from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_perplexity import ChatPerplexity
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

async def run_query_answering_chain(query, context, brand_name,api_keys):

    brand_rag_system_prompt = """

    Answer the following query: {query}

    Here is the context:
    {context}

    """

    import asyncio
    
    llms = []
    
    # Only initialize LLMs for which we have API keys
    if api_keys.get("OPENAI_API_KEY"):
        openai_llm = ChatOpenAI(api_key=api_keys["OPENAI_API_KEY"], model="gpt-4o-mini", temperature=0)
        llms.append(openai_llm)

    if api_keys.get("GOOGLE_API_KEY"):
        gemini_llm =  ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            api_key=api_keys["GOOGLE_API_KEY"],
        )
        llms.append(gemini_llm)

    if api_keys.get("PERPLEXITY_API_KEY"):
        perplexity_llm = ChatPerplexity(temperature=0, pplx_api_key=api_keys["PERPLEXITY_API_KEY"], model="sonar")
        llms.append(perplexity_llm)
    
    if not llms:
        raise ValueError("No valid API keys provided for LLMs")

    # Create async tasks for all LLM calls to run concurrently
    async def call_llm(llm):
        brand_rag_prompt = ChatPromptTemplate.from_template(brand_rag_system_prompt).partial(brand_name=brand_name)
        brand_rag_chain = brand_rag_prompt | llm
        
        response = await brand_rag_chain.ainvoke({
            "query": query,
            "context": context
        })
        return llm.__class__.__name__, response
    
    # Run all LLM calls concurrently
    tasks = [call_llm(llm) for llm in llms]
    results = await asyncio.gather(*tasks)
    
    # Convert results to dictionary
    llm_responses = dict(results)
    return llm_responses