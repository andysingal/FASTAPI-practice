"""Main application file for the FastAPI app."""

import os

import openai
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from llama_index.core import PromptTemplate, get_response_synthesizer
from llama_index.core.indices.vector_store.base import VectorStoreIndex
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from pydantic import BaseModel
from qdrant_client import QdrantClient

# Load environmental variables from .env file
load_dotenv()

# FastAPI initialization
app = FastAPI()

# Configuration parameters from environment variables
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# Set OpenAI API key
if OPENAI_API_KEY is None:
    raise ValueError("Please set the OPENAI_API_KEY environment variable.")

# Initialize Qdrant client
client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)

# Initialize OpenAIEmbedding embedding model
embed_model = OpenAIEmbedding(openai_api_key=OPENAI_API_KEY)

# Define the query model
class QueryRequest(BaseModel):

    """Request model for querying the vector store."""

    query: str

# Initialize Qdrant Vector Store
vector_store = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME, embed_model=embed_model)

# Initialize Vector Store Index
index = VectorStoreIndex.from_vector_store(vector_store=vector_store, embed_model=embed_model)

# Define the prompt template for querying
qa_prompt_tmpl_str = """\
Context information is below.
---------------------
{context_str}
---------------------

Given the context information and not prior knowledge, \
answer the query. Please be concise, and complete. \
If the context does not contain an answer to the query \
respond with I don't know!

Query: {query_str}
Answer: \
"""
qa_prompt = PromptTemplate(qa_prompt_tmpl_str)

# Initialize Retriever
retriever = VectorIndexRetriever(index=index)

# Initialize Response Synthesizer
response_synthesizer = get_response_synthesizer(
    text_qa_template=qa_prompt,
)

# Initialize Sentence Reranker for query response
rerank = SentenceTransformerRerank(
    model="cross-encoder/ms-marco-MiniLM-L-2-v2", top_n=3
)

# Initialize RetrieverQueryEngine for query processing
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    response_synthesizer=response_synthesizer,
    node_postprocessors=[rerank]
)

@app.post("/query/")
async def query_vector_store(request: QueryRequest):
    """
    Endpoint for querying the vector store.

    Args:
    ----
    request (QueryRequest): The query request model.

    Returns:
    -------
    str: Cleaned response to the query from the vector store.

    Raises:
    ------
    HTTPException:
        If no response is found.

    """
    query = request.query
    response = query_engine.query(query)
    if not response:
        raise HTTPException(status_code=404, detail="No response found")

    # Remove newline characters from the response
    cleaned_response = response.response.replace("\n", "")

    return cleaned_response

@app.get("/")
def read_root():
    """Root endpoint returning a simple message."""
    return {"message": "GKE App V0"}

# Run the app using `uvicorn` if this file is executed directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
