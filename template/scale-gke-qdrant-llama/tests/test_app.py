"""
Unit tests for the FastAPI application.

These tests verify the behavior of different endpoints.
"""

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)

def test_read_root():
    """
    Test the root endpoint ("/").

    Checks that the root endpoint returns a status code of 200 and a message.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "GKE App V0"}


def test_query_vector_store_valid():
    """
    Test the vector store query endpoint ("/query/").

    Checks that the endpoint returns a valid response for a valid query payload.
    """
    valid_payload = {"query": "Enter query string."}
    response = client.post("/query/", json=valid_payload)
    assert response.status_code == 200
    assert isinstance(response.json(), str)
