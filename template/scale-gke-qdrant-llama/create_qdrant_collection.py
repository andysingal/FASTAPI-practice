"""Script for creating a Qdrant collection."""

import os
from uuid import uuid4

import openai
from dotenv import load_dotenv
from github import Github
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.readers.github import GithubClient, GithubRepositoryReader
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.models import Distance, PointStruct, VectorParams

# Load environmental variables from a .env file
load_dotenv()

QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL')
COLLECTION_NAME = os.getenv('COLLECTION_NAME')
GITHUB_USERNAME  = os.getenv('GITHUB_USERNAME')
ACCESS_TOKEN  = os.getenv('ACCESS_TOKEN')

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY


def get_code_file_list(github_token, github_username):
    """
    Fetch all repositories for a given GitHub user.

    Args:
    ----
    github_token (str): GitHub access token.
    github_username (str): GitHub username.

    Returns:
    -------
    list: List of documents fetched from the user's repositories.

    """
    try:
        # Initialize Github client
        g = Github(github_token)

        # Fetch all repositories for the user
        repos = g.get_user(github_username).get_repos()

        github_client = GithubClient(github_token=github_token, verbose=True)

        all_documents = []

        for repo in repos:
            repo_name = repo.full_name
            print(f"Loading files from {repo_name}")

            # Check if the repository belongs to the user
            if repo.owner.login != github_username:
                print(f"Skipping repository {repo_name} as it does not belong to the user.")
                continue

            try:
                # Determine the default branch
                default_branch = repo.default_branch

                # Load documents from the repository
                documents = GithubRepositoryReader(
                    github_client=github_client,
                    owner=github_username,
                    repo=repo.name,
                    use_parser=False,
                    verbose=False,
                    filter_file_extensions=(
                        [".py"],
                        GithubRepositoryReader.FilterType.INCLUDE,
                    ),
                ).load_data(branch=default_branch)

                # Ensure each document has text content
                for doc in documents:
                    if doc.text and doc.text.strip():
                        all_documents.append(doc)
                    else:
                        print(f"Skipping empty document: {doc.metadata['file_path']}")

            except Exception as e:
                print(f"Failed to load {repo_name}: {e}")

    except Exception as e:
        print(f"Error fetching repositories: {e}")

    return all_documents


def split_documents_into_nodes(all_documents):
    """
    Split documents into nodes using SentenceSplitter.

    Args:
    ----
    all_documents (list): List of Document objects.

    Returns:
    -------
    list: List of nodes extracted from documents.

    """
    try:
        splitter = SentenceSplitter(
            chunk_size=1500,
            chunk_overlap=200
        )

        nodes = splitter.get_nodes_from_documents(all_documents)

        return nodes

    except Exception as e:
        print(f"Error splitting documents into nodes: {e}")
        return []

def create_collection_if_not_exists(client, collection_name):
    """
    Create a Qdrant collection if it does not already exist.

    Args:
    ----
    client (QdrantClient): The Qdrant client instance.
    collection_name (str): The name of the collection.

    """
    try:
        collections = client.get_collections()
        if collection_name not in [col.name for col in collections.collections]:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
            )

            print(f"Collection '{collection_name}' created.")
        else:
            print(f"Collection '{collection_name}' already exists.")
    except ResponseHandlingException as e:
        print(f"Error checking or creating collection: {e}")


def chunked_nodes(data, client, collection_name):
    """
    Process and upsert chunked metadata into Qdrant.

    Args:
    ----
    data (list): The list of document chunks.
    client (QdrantClient): The Qdrant client instance.
    collection_name (str): The name of the collection.

    """
    chunked_nodes = []

    for item in data:
        qdrant_id = str(uuid4())
        document_id = item.id_
        code_text = item.text
        source = item.metadata["url"]
        file_name = item.metadata["file_name"]

        content_vector = embed_model.get_text_embedding(code_text)

        payload = {
            "text": code_text,
            "document_id": document_id,
            "metadata": {
                            "qdrant_id": qdrant_id,
                            "source": source,
                            "file_name": file_name,
                            }
                }


        metadata = PointStruct(id=qdrant_id, vector=content_vector, payload=payload)

        chunked_nodes.append(metadata)

    if chunked_nodes:
        client.upsert(
            collection_name=collection_name,
            wait=True,
            points=chunked_nodes
        )

    print(f"{len(chunked_nodes)} Chunked metadata upserted.")


if __name__ == "__main__":
    # Fetch documents from GitHub repositories
    all_documents = get_code_file_list(ACCESS_TOKEN, GITHUB_USERNAME)

    if all_documents:
        # Split documents into nodes
        nodes = split_documents_into_nodes(all_documents)

        # Initialize embedding model
        embed_model = OpenAIEmbedding(openai_api_key=OPENAI_API_KEY)

        # Initialize Qdrant client
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

        # Create collection if it does not exist
        create_collection_if_not_exists(client, COLLECTION_NAME)

        # Upsert documents in vector store
        chunked_nodes(nodes[:2], client, COLLECTION_NAME)
    else:
        print("No documents to process.")


