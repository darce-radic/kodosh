import streamlit as st
import os
import logging
from datetime import date, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from rag_agent import RagAgent
from pinecone_utility import PineconeUtility
from utility import authorize_gmail_api, authenticate_user, switch_account
from safe_constants import SCOPES
from render_mail import render_most_relevant_mails
from subscriptions import view_subscriptions, extract_subscriptions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

try:
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
        st.session_state.start_date = date.today() - timedelta(days=365)

    if "end_date" not in st.session_state:
        st.session_state.end_date = date.today()

    def logout(is_from_login_func=False):
        st.experimental_set_query_params()
        st.session_state.user_email = None
        st.session_state.creds = None

        if os.path.exists("token.json"):
            os.remove("token.json")
        if not is_from_login_func:
            st.success("Logged out successfully!")

    def login():
        logout(is_from_login_func=True)
        authorize_gmail_api()

    if st.experimental_get_query_params().get('code', None):
        authenticate_user()

    if not st.session_state.creds or not st.session_state.user_email:
        st.warning("Please log in to continue.")
        if st.button("Login"):
            login()
        st.stop()

    if st.button("Logout"):
        logout()
        st.experimental_rerun()

    if st.session_state.creds and st.session_state.user_email:
        st.write("## Query for specific emails (returns specific emails you are looking for)")
        prompt = st.text_input("Enter what emails you are looking for")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Get specific mails by content"):
                if prompt == "":
                    st.error("Please enter a valid query")
                else:
                    st.session_state.rag_response = None
                    mails = rag_agent.find_most_relevant_emails(prompt, top_k=K_MAILS_TO_RETURN)
                    if mails and len(mails) > 0:
                        st.session_state.most_relevant_mails = mails
                        st.session_state.selected_mail = mails[0]
                        st.session_state.selected_mail_index = 0
                        st.experimental_rerun()
        with col2:
            if st.button("Ask general questions regarding emails"):
                if prompt == "":
                    st.error("Please enter a valid query")
                else:
                    response_text, mails = rag_agent.run_rag(prompt, K_MAILS_TO_RETURN)
                    if response_text and len(response_text) > 0 and mails and len(mails) > 0:
                        st.session_state.rag_response = response_text
                        st.session_state.most_relevant_mails = mails

        if st.button("Upload mail contents"):
            st.info("Uploading emails...")
            result_boolean = pinecone_utility.upload_email_content(index, user_emails=[st.session_state.user_email], sheet_url=os.getenv("GOOGLE_SHEET_URL"))
            if result_boolean:
                st.success("Emails uploaded successfully")

        st.write("Specify the date range for fetching emails:")

        start_date = st.date_input("Start date", value=st.session_state.start_date, key='start_date')
        end_date = st.date_input("End date", value=st.session_state.end_date, key='end_date')

        if st.session_state.rag_response:
            st.write("## RAG response")
            st.write(st.session_state.rag_response)

        if st.session_state.most_relevant_mails is not None:
            st.write("## Most relevant emails")
            st.write(f"Emails listed in descending order of relevance for query: '{prompt}'")
            render_most_relevant_mails()

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
            <a href="" target="_blank">
                <button class="button">Buy me a coffee</button>
            </a>
            """
        st.markdown(button_html, unsafe_allow_html=True)

        if "tokens" in st.session_state:
            account_list = list(st.session_state.tokens.keys())
            selected_account = st.selectbox("Select Gmail Account", account_list)
            if st.button("Switch Account"):
                switch_account(selected_account)
        else:
            st.write("No accounts available. Please log in.")

        st.sidebar.header("Email Query Settings")
        start_date = st.sidebar.date_input("Start Date", value=st.session_state.start_date)
        end_date = st.sidebar.date_input("End Date", value=st.session_state.end_date)

        if start_date and end_date:
            if start_date > end_date:
                st.sidebar.error("Start date must be before end date.")
            else:
                st.session_state.start_date = start_date
                st.session_state.end_date = end_date

        if st.sidebar.button("View Subscriptions"):
            view_subscriptions()

        if st.sidebar.button("Extract Subscriptions"):
            extract_subscriptions(pinecone_utility)

        if st.sidebar.button("View Potential Subscriptions"):
            st.experimental_set_query_params(page="subscriptions_page")

        if st.sidebar.button("Manage Gmail Accounts"):
            st.experimental_set_query_params(page="manage_accounts")

        if st.sidebar.button("Upload Bank CSV"):
            st.experimental_set_query_params(page="upload_bank_csv")
except Exception as e:
    st.error(f"An error occurred: {e}")
    logger.error(f"An error occurred: {e}")
