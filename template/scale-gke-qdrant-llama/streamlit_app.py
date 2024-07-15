"""Script for Streamlit UI."""

import requests
import streamlit as st

# Set the FastAPI endpoint
FASTAPI_ENDPOINT = "http://34.65.157.134:8000/query/"

# Streamlit app title
st.title("Find Your Code")

# Input field for the query
query = st.text_input("Query:")

# Button to submit the query
if st.button("Get Response"):
    if query:
        response = requests.post(FASTAPI_ENDPOINT, json={"query": query})
        if response.status_code == 200:
            st.write(response.text)
        else:
            st.write("Error:", response.status_code)
    else:
        st.write("Please enter a query.")


