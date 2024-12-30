import streamlit as st
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI
from tqdm.auto import tqdm
from pinecone import Pinecone
import json
import logging
from dotenv import load_dotenv
from safe_constants import SCOPES, MAIN_REDIRECT_URI, ALL_REDIRECT_URIS, ALL_JAVASCRIPT_ORIGINS, PROJECT_ID, AUTH_URI, TOKEN_URI, AUTH_PROVIDER_X509_CERT_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1' # avoids error being thrown for duplicate scopes (doesnt matter for this use case)

PINECONE_API_KEY = st.secrets["PINECONE_API_KEY"]
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]

pc = Pinecone(api_key=PINECONE_API_KEY)
openai_client = OpenAI()

CLIENT_ID = st.secrets["GMAIL_API_CREDENTIALS"]["CLIENT_ID"]
CLIENT_SECRET = st.secrets["GMAIL_API_CREDENTIALS"]["CLIENT_SECRET"]

CLIENT_CONFIG = {
     "web":{"client_id":CLIENT_ID,"project_id":PROJECT_ID,"auth_uri":AUTH_URI,"token_uri":TOKEN_URI,"auth_provider_x509_cert_url":AUTH_PROVIDER_X509_CERT_URL,"client_secret":CLIENT_SECRET,"redirect_uris": ALL_REDIRECT_URIS,"javascript_origins": ALL_JAVASCRIPT_ORIGINS}
     }


def get_user_info(creds):
    try:
        # Build the OAuth2 service to get user info
        oauth2_service = build('oauth2', 'v2', credentials=creds)
        
        # Get user info
        user_info = oauth2_service.userinfo().get().execute()

        return user_info.get('email')
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        st.error("Failed to get user info. Please try again.")


def authorize_gmail_api():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    try:
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            st.info("Already logged in")
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    CLIENT_CONFIG, SCOPES
                )
                flow.redirect_uri = MAIN_REDIRECT_URI

                authorization_url, state = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true',
                    prompt='consent')

                st.markdown(
                    f"""
                    <style>
                    .custom-button {{
                        display: inline-block;
                        background-color: #4CAF50; /* Green background */
                        color: white !important;  /* White text */
                        padding: 10px 24px;
                        text-align: center;
                        text-decoration: none;
                        font-size: 16px;
                        border-radius: 5px;
                        margin-top: 5px; /* Reduce space above the button */
                        margin-bottom: 5px; /* Reduce space below the button */
                    }}
                    .custom-button:hover {{
                        background-color: #45a049;
                    }}
                    </style>
                    <a href="{authorization_url}" target="_blank" class="custom-button">Authorize with Google</a>
                    """,
                    unsafe_allow_html=True
                )
    except Exception as e:
        logger.error(f"Error authorizing Gmail API: {e}")
        st.error("Failed to authorize Gmail API. Please try again.")

def authenticate_user():
    """after logging in with google, you have a code in the url. This function retrieves the code and fetches the credentials and authenticates user"""
    try:
        auth_code = st.query_params.get('code', None)
        if auth_code is not None:
            logger.info("INSIDE CODE")
            from utility import CLIENT_CONFIG
            
            # make a new flow to fetch tokens
            flow = InstalledAppFlow.from_client_config(
                    CLIENT_CONFIG, SCOPES, 
                )
            flow.redirect_uri = MAIN_REDIRECT_URI
            flow.fetch_token(code=auth_code)
            st.query_params.clear()
            creds = flow.credentials
            if creds:
                st.session_state.creds = creds
                # Save the credentials for future use
                with open('token.json', 'w') as token_file:
                    token_file.write(creds.to_json())
                st.success("Authorization successful! Credentials have been saved.")

                # Save the credentials for the next run
                with open("token.json", "w") as token: 
                    token.write(creds.to_json())
                # get user email
                user_email = get_user_info(creds)
                st.session_state.user_email = user_email
                st.rerun()
        else: st.error("Could not log in user")
    except Exception as e:
        logger.error(f"Error authenticating user: {e}")
        st.error("Failed to authenticate user. Please try again.")

def switch_account(selected_email):
    """
    Switch to the selected Gmail account.

    Args:
        selected_email (str): The email address of the account to switch to.

    Returns:
        None
    """
    try:
        if selected_email in st.session_state.tokens:
            st.session_state.creds = st.session_state.tokens[selected_email]
            st.session_state.user_email = selected_email
        else:
            st.error("Account not authorized. Please log in.")
    except Exception as e:
        logger.error(f"Error switching account: {e}")
        st.error("Failed to switch account. Please try again.")

def store_token(email, creds):
    """
    Store the OAuth token for a Gmail account.

    Args:
        email (str): The email address of the account.
        creds: The OAuth credentials.

    Returns:
        None
    """
    try:
        if "tokens" not in st.session_state:
            st.session_state.tokens = {}
        st.session_state.tokens[email] = creds
    except Exception as e:
        logger.error(f"Error storing token: {e}")
        st.error("Failed to store token. Please try again.")
