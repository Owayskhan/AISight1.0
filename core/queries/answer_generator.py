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

    openai_llm = ChatOpenAI(api_key=api_keys["OPENAI_API_KEY"], model="gpt-4o-mini", temperature=0)

    gemini_llm =  ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        api_key=api_keys["GOOGLE_API_KEY"],
    )

    perplexity_llm = ChatPerplexity(temperature=0, pplx_api_key=api_keys["PERPLEXITY_API_KEY"], model="sonar")

    llms = [openai_llm, gemini_llm, perplexity_llm]

    llm_responses = {}
    for llm in llms:
        brand_rag_prompt = ChatPromptTemplate.from_template(brand_rag_system_prompt).partial(brand_name=brand_name)
        brand_rag_chain = brand_rag_prompt | llm

        response = await brand_rag_chain.ainvoke({
            "query": query,
            "context": context
        })
        llm_responses[llm.__class__.__name__] = response

    return llm_responses