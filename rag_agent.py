import streamlit as st
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI
from tqdm.auto import tqdm
from pinecone import Pinecone
from langchain_openai import ChatOpenAI
from typing import Optional
from dotenv import load_dotenv
from safe_constants import SCOPES

load_dotenv()

PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

pc = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

class RagAgent:
    def __init__(self, index):
        self.index = index
        self.llm = ChatOpenAI(
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model_name="gpt-4o-mini",
            temperature=0.0
        )

    def _query_pinecone_index(self, query_embedding: list, top_k: int = 2, include_metadata: bool = True) -> dict[str, any]:
        """
        Query a Pinecone index.

        Args:
        - query_embedding (List[float]): List of query vectors.
        - top_k (int): Number of nearest neighbors to retrieve (default: 2).
        - include_metadata (bool): Whether to include metadata in the query response (default: True).

        Returns:
        - query_response (Dict[str, Any]): Query response containing nearest neighbors.
        """
        if st.session_state.user_email is None:
            st.error("Please login first")
            return
        try:
            query_response = self.index.query(
                vector=query_embedding, top_k=top_k, include_metadata=include_metadata, filter={"user_email": st.session_state.user_email}
            )
            if len(query_response["matches"]) == 0:
                st.error("No emails found. Please upload emails first")
                return
            return query_response
        except Exception as e:
            st.error(f"Error querying Pinecone index: {e}")
            return None

    def find_most_relevant_emails(self, query, top_k=2, include_metadata: bool = True):
        query_embedding = self.get_embedding(query)
        query_response = self._query_pinecone_index(query_embedding, top_k=top_k, include_metadata=include_metadata)
        mails = self._extract_mail_metadata(query_response)
        return mails

    def _extract_mail_metadata(self, response) -> Optional[str]:
        """Extract data from mail objects to make a list of dictionaries with sender, date, subject, text."""
        if response is None:
            return None
        return [response["matches"][i]["metadata"] for i in range(len(response["matches"]))]

    def _extract_text_from_query_response(self, query_response: dict[str, any]) -> str:
        """
        Extract the text from the metadata in the query response to feed into LLM for response.

        Args:
        - query_response (Dict[str, Any]): Query response containing metadata.

        Returns:
        - text_answer (str): The extracted text from the query response.
        """
        texts = [doc['metadata']['text'] for doc in query_response['matches']]
        return texts

    def run_rag(self, query, top_k=2):
        """Run full RAG, so first embed query, then query Pinecone index, then extract text from response, then prompt GPT to answer question given context from Pinecone."""
        mails = self.find_most_relevant_emails(query, top_k=top_k)
        if mails is None:
            return None, None
        # Extract all the information to text
        full_email_text = ""
        for mail in mails:
            sender, date, subject, text = mail["sender"], mail["date"], mail["subject"], mail["text"]
            full_email_text += f"Sender: {sender}, Date: {date}, Subject: {subject}, Text: {text}\n"

        full_prompt = f"Given the following emails {full_email_text} what is the answer to the question: {query}"

        response = self.llm.invoke(full_prompt)
        return response.content, mails

    def get_embedding(self, text: str) -> list[float]:
        # Ensure the text length is within the allowed token limit
        max_tokens = 8192
        if len(text) > max_tokens:
            text = text[:max_tokens]

        response = openai_client.embeddings.create(input=[text], model="text-embedding-ada-002")
        return response.data[0].embedding

    def _identify_subscriptions(self, text: str) -> list[str]:
        # Implement the logic to identify subscriptions from the text
        # This is a placeholder implementation
        return ["subscription1", "subscription2"]