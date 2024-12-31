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

os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'  # avoids error being thrown for duplicate scopes (doesn't matter for this use case)

CLIENT_ID = st.secrets["GMAIL_API_CREDENTIALS"]["CLIENT_ID"]
CLIENT_SECRET = st.secrets["GMAIL_API_CREDENTIALS"]["CLIENT_SECRET"]

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
    # Build the OAuth2 service to get user info
    oauth2_service = build('oauth2', 'v2', credentials=creds)
    
    # Get user info
    user_info = oauth2_service.userinfo().get().execute()

    return user_info.get('email')

def authorize_gmail_api():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
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

def authenticate_user():
    """after logging in with google, you have a code in the url. This function retrieves the code and fetches the credentials and authenticates user"""
    auth_code = st.query_params.get('code', None)
    if auth_code is not None:
        logger.info("INSIDE CODE")
        try:
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
                st.experimental_set_query_params()
                st.experimental_rerun()
        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            st.error("Failed to authenticate user. Please try again.")
    else:
        st.error("Could not log in user")

def switch_account(selected_email):
    """
    Switch to the selected Gmail account.

    Args:
        selected_email (str): The email address of the account to switch to.

    Returns:
        None
    """
    if selected_email in st.session_state.tokens:
        st.session_state.creds = st.session_state.tokens[selected_email]
        st.session_state.user_email = selected_email
    else:
        st.error("Account not authorized. Please log in.")

def store_token(email, creds):
    """
    Store the OAuth token for a Gmail account.

    Args:
        email (str): The email address of the account.
        creds: The OAuth credentials.

    Returns:
        None
    """
    if "tokens" not in st.session_state:
        st.session_state.tokens = {}
    st.session_state.tokens[email] = creds
