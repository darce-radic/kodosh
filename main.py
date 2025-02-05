import streamlit as st
import os
import logging
from datetime import date, timedelta, datetime
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI
from pinecone import Pinecone
from rag_agent import RagAgent  # Ensure this path is correct
from pinecone_utility import PineconeUtility  # Ensure this path is correct
from utility import authorize_gmail_api, authenticate_user, switch_account, get_user_info
from safe_constants import SCOPES  # Ensure this module is available
from render_mail import render_most_relevant_mails
from subscriptions import view_subscriptions, extract_subscriptions
import mitosheet
import html  # To escape special characters
import json

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

pc = Pinecone(api_key=PINECONE_API_KEY)
client = OpenAI()

index = pc.Index("mails")
rag_agent = RagAgent(index)
pinecone_utility = PineconeUtility(index)

K_MAILS_TO_RETURN = 10

if "user_email" in st.session_state and st.session_state.user_email is not None:
    st.title(f"Hello {st.session_state.user_email}")
else:
    st.title("Welcome to the Email Assistant")

if "creds" not in st.session_state:
    st.session_state.creds = None

if "user_email" not in st.session_state:
    st.session_state.user_email = None

if "most_relevant_mails" not in st.session_state:
    st.session_state.most_relevant_mails = None

if "selected_mail" not in st.session_state:
    st.session_state.selected_mail = None

if "flow" not in st.session_state:
    st.session_state.flow = None

if "rag_response" not in st.session_state:
    st.session_state.rag_response = None

if "selected_mail_index" not in st.session_state:
    st.session_state.selected_mail_index = 0

if "start_date" not in st.session_state:
    st.session_state.start_date = datetime(2024, 1, 1).date()

if "end_date" not in st.session_state:
    st.session_state.end_date = date.today()

def logout(is_from_login_func=False):
    """Logs the user out by deleting the token and clearing session data."""
    logger.debug("INSIDE LOGOUT")
    st.query_params.clear()
    st.session_state.user_email = None
    st.session_state.creds = None

    if os.path.exists("token.json"):
        os.remove("token.json")
    if not is_from_login_func:
        st.success("Logged out successfully!")

def login():
    logout(is_from_login_func=True)
    authorize_gmail_api()

if st.query_params.get('code', None):
    authenticate_user()

if st.button("Login"):
    login()

if st.button("Logout"):
    logout()
    st.rerun()

st.write("Specify the date range for fetching emails:")
start_date = st.date_input("Start date", value=st.session_state.start_date, key='start_date_input')
end_date = st.date_input("End date", value=st.session_state.end_date, key='end_date_input')

if st.button("Upload mail contents"):
    st.info("Uploading emails within the specified date range")
    result_boolean = pinecone_utility.upload_email_content(index, user_email=st.session_state.user_email, start_date=start_date, end_date=end_date)
    if result_boolean:
        st.success("Emails uploaded successfully")

st.write("## Query for specific emails (returns specific emails you are looking for)")
prompt = st.text_input("Enter what emails you are looking for")

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Get specific mails by content"):
        if st.session_state.creds is None or st.session_state.user_email is None:
            st.error("Please login first")
        elif prompt == "":
            st.error("Please enter a valid query")
        else:
            st.session_state.rag_response = None
            mails = rag_agent.find_most_relevant_emails(prompt, top_k=K_MAILS_TO_RETURN)
            if mails and len(mails) > 0:
                st.session_state.most_relevant_mails = mails
                st.session_state.selected_mail = mails[0]  # select the first mail by default (most similar)
                st.session_state.selected_mail_index = 0
                st.rerun()
with col2:
    if st.button("Ask general questions regarding emails"):
        if st.session_state.creds is None or st.session_state.user_email is None:
            st.error("Please login first")
        elif prompt == "":
            st.error("Please enter a valid query")
        else:
            response_text, mails = rag_agent.run_rag(prompt, K_MAILS_TO_RETURN)
            if response_text and len(response_text) > 0 and mails and len(mails) > 0:
                st.session_state.rag_response = response_text
                st.session_state.most_relevant_mails = mails
                st.session_state.selected_mail = mails[0]  # select the first mail by default (most similar)
                st.session_state.selected_mail_index = 0
                st.rerun()

def render_mail(selected_mail):
    email_subject = html.escape(selected_mail["subject"])
    email_sender = html.escape(selected_mail["sender"])
    email_date = html.escape(selected_mail["date"])
    email_content = html.escape(selected_mail["text"])
    email_link = selected_mail["email_link"]  # Get the email link from the selected_mail dictionary

    # Custom CSS for styling the box and button
    st.markdown(
        """
        <style>
        .email-box {
            background-color: #f0f9ff;
            border: 1px solid #d1e7dd;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .email-content {
            color: #333333;
            font-size: 16px;
            margin-top: 10px;
        }
        .email-header {
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 5px;
        }
        .email-subheader {
            color: #6c757d;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .email-link {
            font-size: 16px;
            margin-top: 20px;
            display: inline-block;
            background-color: #ff8c00; /* Orange background */
            color: white !important; /* Ensure white text */
            padding: 10px 20px;
            text-align: center;
            border-radius: 8px;
            text-decoration: none;
            transition: background-color 0.3s ease; /* Smooth transition */
        }
        .email-link:hover {
            background-color: #e67600; /* Darker orange on hover */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Display the email inside a styled box with the clickable button link
    st.markdown(f"""
    <div class="email-box">
        <div class="email-header">Subject: <span>{email_subject}</span></div>
        <div class="email-subheader">From: <span>{email_sender}</span> | Date: <span>{email_date}</span></div>
        <a href="{email_link}" target="_blank" class="email-link">Open Email in Gmail</a>
        <div class="email-content"><span>{email_content}</span></div>
    </div>
    """, unsafe_allow_html=True)

def update_selected_mail():
    st.session_state.selected_mail = st.session_state.most_relevant_mails[st.session_state.selected_mail_index]

if 'selected_mail_index' not in st.session_state:
    st.session_state.selected_mail_index = 0  # Start at the most relevant email (index 0)

def render_most_relevant_mails():
    col1, col_mid, col2 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Previous"):
            if st.session_state.selected_mail_index == 0:
                st.warning("No more emails to show")
            else:
                st.session_state.selected_mail_index -= 1
                update_selected_mail()

    with col2:
        if st.button("Next →"):
            if st.session_state.selected_mail_index == len(st.session_state.most_relevant_mails) - 1:
                st.warning("No more emails to show")
            else:
                st.session_state.selected_mail_index += 1
                update_selected_mail()

    with col_mid:
        st.write(f"Email {st.session_state.selected_mail_index + 1}/{len(st.session_state.most_relevant_mails)}")

    # Update selected mail if not already set
    if "selected_mail" not in st.session_state:
        update_selected_mail()
    
    # Render the currently selected email
    if st.session_state.selected_mail:
        render_mail(st.session_state.selected_mail)

if st.session_state.rag_response:
    st.write("## RAG response")
    st.write(st.session_state.rag_response)

if st.session_state.most_relevant_mails is not None:
    st.write("## Most relevant emails")
    st.write(f"Emails listed in descending order of relevance for query: '{prompt}'")
    render_most_relevant_mails()

# Custom HTML for a green button
button_html = """
    <style>
    .button {
        background-color: #4CAF50; /* Green */
        border: none;
        color: white;
        padding: 15px 32px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        cursor: pointer;
        border-radius: 12px;
        margin: 20px 2px;
        margin-top: 100px;
    }
    </style>
    <a href="https://buymeacoffee.com/kjosbakken" target="_blank">
        <button class="button">Buy me a coffee</button>
    </a>
    """

# Display the button
st.markdown(button_html, unsafe_allow_html=True)
