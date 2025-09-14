import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS
import os
from langchain_openai import OpenAIEmbeddings
from core.website_crawler.crawler import load_sitemap_documents





def create_vector_store(sitemap_docs,api_key):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small",api_key=api_key)

    index = faiss.IndexFlatL2(len(embeddings.embed_query("hello world")))

    sitemap_vector_store = FAISS(
        embedding_function=embeddings,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )

    from uuid import uuid4

    uuids = [str(uuid4()) for _ in range(len(sitemap_docs))]

    sitemap_vector_store.add_documents(documents=sitemap_docs, ids=uuids)

    return sitemap_vector_store

def get_retriever(sitemap_url, api_key, k=4):

    sitemap_docs = load_sitemap_documents(sitemap_url)
    sitemap_vector_store = create_vector_store(sitemap_docs, api_key)
    return sitemap_vector_store.as_retriever(search_type="similarity", search_kwargs={"k":k})