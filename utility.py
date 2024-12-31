import os
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import streamlit as st
from safe_constants import SCOPES, MAIN_REDIRECT_URI, ALL_REDIRECT_URIS, ALL_JAVASCRIPT_ORIGINS, PROJECT_ID, AUTH_URI, TOKEN_URI, AUTH_PROVIDER_X509_CERT_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CLIENT_ID = os.getenv("GMAIL_API_CLIENT_ID")
CLIENT_SECRET = os.getenv("GMAIL_API_CLIENT_SECRET")

CLIENT_CONFIG = {
    "web": {
        "client_id": CLIENT_ID,
        "project_id": PROJECT_ID,
        "auth_uri": AUTH_URI,
        "token_uri": TOKEN_URI,
        "auth_provider_x509_cert_url": AUTH_PROVIDER_X509_CERT_URL,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ALL_REDIRECT_URIS,
        "javascript_origins": ALL_JAVASCRIPT_ORIGINS
    }
}

def get_user_info(creds):
    try:
        oauth2_service = build('oauth2', 'v2', credentials=creds)
        user_info = oauth2_service.userinfo().get().execute()
        return user_info.get('email')
    except Exception as e:
        logger.error(f"Error getting user info: {e}")
        return None

def authorize_gmail_api():
    try:
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
            st.info("Already logged in")
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
                flow.redirect_uri = MAIN_REDIRECT_URI

                authorization_url, state = flow.authorization_url(
                    access_type='offline',
                    include_granted_scopes='true',
                    prompt='consent'
                )

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
    try:
        auth_code = st.query_params.get('code', None)
        if auth_code:
            flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
            flow.redirect_uri = MAIN_REDIRECT_URI
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            if creds:
                email = get_user_info(creds)
                if email:
                    store_token(email, creds)
                    st.session_state.creds = creds
                    st.session_state.user_email = email
                    st.experimental_update_query_params()
                    st.success("Logged in successfully!")
                else:
                    st.error("Failed to retrieve user email.")
        else:
            st.error("Could not log in user")
    except Exception as e:
        logger.error(f"Error authenticating user: {e}")
        st.error("Failed to authenticate user. Please try again.")

def switch_account(selected_email):
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
    try:
        if "tokens" not in st.session_state:
            st.session_state.tokens = {}
        st.session_state.tokens[email] = creds
    except Exception as e:
        logger.error(f"Error storing token: {e}")
        st.error("Failed to store token. Please try again.")