import streamlit as st
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
        self.llm = ChatOpenAI(api_key=OPENAI_API_KEY)

    def find_most_relevant_emails(self, query, top_k=2):
        query_response = self.index.query(query, top_k=top_k)
        if len(query_response["matches"]) == 0:
            st.error("No emails found. Please upload emails first")
            return None
        return query_response

    def _extract_mail_metadata(self, response) -> Optional[str]:
        if response is None:
            return None
        return [response["matches"][i]["metadata"] for i in range(len(response["matches"]))]

    def _extract_text_from_query_response(self, query_response: dict) -> str:
        texts = [doc['metadata']['text'] for doc in query_response['matches']]
        return texts

    def run_rag(self, query, top_k=2):
        mails = self.find_most_relevant_emails(query, top_k=top_k)
        if mails is None:
            return None, None
        full_email_text = ""
        for mail in mails:
            sender, date, subject, text = mail["sender"], mail["date"], mail["subject"], mail["text"]
            full_email_text += f"Sender: {sender}, Date: {date}, Subject: {subject}, Text: {text}\n"

        full_prompt = f"Given the following emails {full_email_text} what is the answer to the question: {query}"

        response = self.llm.invoke(full_prompt)
        return response.content, mails

    def get_embedding(self, text: str) -> list[float]:
        response = openai_client.Embedding.create(input=text, model="text-embedding-ada-002")
        return response['data'][0]['embedding']