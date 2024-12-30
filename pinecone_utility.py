import hashlib
from tqdm.auto import tqdm
import streamlit as st
from googleapiclient.discovery import build
import base64
import gspread  # Add this import for Google Sheets API

from rag_agent import RagAgent
from safe_constants import MAX_CHARACTER_LENGTH_EMAIL

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PineconeUtility():
    def __init__(self, index) -> None:
        self.rag_agent = RagAgent(index)
        self.gc = gspread.service_account(filename='path/to/your/service_account.json')  # Add this line to initialize gspread

    def _generate_short_id(self, content: str) -> str:
        """
        Generate a short ID based on the content using SHA-256 hash.

        Args:
        - content (str): The content for which the ID is generated.

        Returns:
        - short_id (str): The generated short ID.
        """
        if content is None or content == "":
            return None
        hash_obj = hashlib.sha256()
        hash_obj.update(content.encode("utf-8"))
        return hash_obj.hexdigest()

    def _combine_vector_and_text(self,
        documents: list[any], doc_embeddings: list[list[float]], user_email: str = None
    ) -> list[dict[str, any]]:
        """
        Process a list of documents along with their embeddings.

        Args:
        - documents (List[Any]): A list of documents (strings or other types).
        - doc_embeddings (List[List[float]]): A list of embeddings corresponding to the documents.

        Returns:
        - data_with_metadata (List[Dict[str, Any]]): A list of dictionaries, each containing an ID, embedding values, and metadata.
        """
        data_with_metadata = []

        for doc, embedding in zip(documents, doc_embeddings):
            doc_text = doc["text"]
            doc_date = doc["date"]
            doc_sender = doc["from"]
            doc_subject = doc["subject"]
            doc_email_link = doc["email_link"]

            if doc_text is None or doc_text == "": continue

            # Generate a unique ID based on the text content
            doc_id = self._generate_short_id(doc_text)

            # Create a data item dictionary
            data_item = {
                "id": doc_id,
                "values": embedding,
                "metadata": {"user_email": user_email, "text": doc_text, "date": doc_date, "sender": doc_sender, "subject": doc_subject, "email_link": doc_email_link},  # Include the text as metadata
            }

            # Append the data item to the list
            data_with_metadata.append(data_item)

        return data_with_metadata

    def _upsert_data_to_pinecone(self, index, data_with_metadata: list[dict[str, any]]) -> None:
        """
        Upsert data with metadata into a Pinecone index.

        Args:
        - data_with_metadata (List[Dict[str, Any]]): A list of dictionaries, each containing data with metadata.

        Returns:
        - None
        """
        index.upsert(vectors=data_with_metadata)

    def _get_email_body(self, msg):
        if 'parts' in msg['payload']:
            # The email has multiple parts (possibly plain text and HTML)
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':  # Look for plain text
                    body = part['body']['data']
                    return base64.urlsafe_b64decode(body).decode('utf-8')
        else:
            # The email might have a single part, like plain text or HTML
            body = msg['payload']['body'].get('data')
            if body:
                return base64.urlsafe_b64decode(body).decode('utf-8')
        return None  # In case no plain text is found

    def fetch_emails_within_time_period(self, service, start_date, end_date):
        """
        Fetch emails from Gmail API within a specific time period.

        Args:
            service: Authorized Gmail API service instance.
            start_date (str): Start date in the format 'YYYY/MM/DD'.
            end_date (str): End date in the format 'YYYY/MM/DD'.

        Returns:
            List[dict]: List of email details with metadata.
        """
        all_emails = []
        query = f"after:{start_date} before:{end_date}"
        results = service.users().messages().list(userId='me', q=query).execute()

        # Fetch the first page of messages
        messages = results.get('messages', [])
        all_emails.extend(messages)

        # Keep fetching emails until there are no more pages
        while 'nextPageToken' in results:
            page_token = results['nextPageToken']
            results = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
            messages = results.get('messages', [])
            all_emails.extend(messages)

        email_details = []
        for idx, email in enumerate(all_emails):
            try:
                msg = service.users().messages().get(userId='me', id=email['id']).execute()
                headers = msg['payload']['headers']

                email_text = self._get_email_body(msg)
                if email_text is None or email_text == "":
                    continue

                email_data = {
                    "text": email_text,
                    "id": msg['id'],
                    "date": next((header['value'] for header in headers if header['name'] == 'Date'), None),
                    "from": next((header['value'] for header in headers if header['name'] == 'From'), None),
                    "subject": next((header['value'] for header in headers if header['name'] == 'Subject'), None),
                    "email_link": f"https://mail.google.com/mail/u/0/#inbox/{email['id']}"
                }
                email_details.append(email_data)
            except Exception as e:
                print(f"Error fetching email details: {e}")

        return email_details

    def _identify_subscriptions(self, email_text: str) -> list[str]:
        """
        Identify potential subscriptions from the email text.

        Args:
        - email_text (str): The text content of the email.

        Returns:
        - subscriptions (list[str]): A list of identified subscriptions.
        """
        # Use RAG to identify potential subscriptions
        subscriptions = self.rag_agent.identify_subscriptions(email_text)
        return subscriptions

    def _store_subscriptions_in_sheet(self, subscriptions: list[str], sheet_url: str) -> None:
        """
        Store identified subscriptions in a Google Sheets document.

        Args:
        - subscriptions (list[str]): A list of identified subscriptions.
        - sheet_url (str): The URL of the Google Sheets document.

        Returns:
        - None
        """
        sh = self.gc.open_by_url(sheet_url)
        worksheet = sh.sheet1
        for subscription in subscriptions:
            worksheet.append_row([subscription])

    def upload_email_content(self, index, user_emails, sheet_url):
        """
        Upload email content to Pinecone and store identified subscriptions in Google Sheets.

        Args:
            index: Pinecone index.
            user_emails (list[str]): List of user email addresses.
            sheet_url (str): The URL of the Google Sheets document.

        Returns:
            bool: True if successful, False otherwise.
        """
        if not st.session_state.creds: 
            st.error("Please login first")
            return False

        start_date = st.session_state.get('start_date')
        end_date = st.session_state.get('end_date')
        if not start_date or not end_date:
            st.error('Start date and end date must be specified.')
            return False

        service = build('gmail', 'v1', credentials=st.session_state.creds)

        all_emails = []
        for user_email in user_emails:
            emails = self.fetch_emails_within_time_period(service, start_date, end_date)
            all_emails.extend(emails)

        progress_bar = st.progress(0)
        status_text = st.text("Creating embeddings...")

        # embed emails
        embeddings = []
        all_subscriptions = []
        for idx, email in tqdm(enumerate(all_emails), desc="Creating embeddings"):
            status_text.text(f"Creating embedding {idx + 1} of {len(all_emails)}")
            if email["text"] is None or email["text"] == "": continue
            try:
                embeddings.append(self.rag_agent.get_embedding(email["text"]))
                # Identify subscriptions
                subscriptions = self._identify_subscriptions(email["text"])
                all_subscriptions.extend(subscriptions)
                # Update the progress bar and status text
                progress_bar.progress((idx + 1) / len(all_emails))  # Progress bar update
            except:
                logger.info(f"Error embedding email {idx}")

        data_with_meta_data = self._combine_vector_and_text(documents=all_emails, doc_embeddings=embeddings, user_email=None) 
        self._upsert_data_to_pinecone(index, data_with_metadata=data_with_meta_data)

        # Store identified subscriptions in Google Sheets
        self._store_subscriptions_in_sheet(all_subscriptions, sheet_url)

        return True

# Streamlit UI for specifying date range and multiple email accounts
st.title("Email Content Uploader")
st.write("Specify the date range for fetching emails:")

start_date = st.date_input("Start date", key='start_date')
end_date = st.date_input("End date", key='end_date')

st.write("Specify the email accounts (comma-separated):")
user_emails_input = st.text_input("Email accounts", key='user_emails')
user_emails = [email.strip() for email in user_emails_input.split(",")]

st.write("Specify the Google Sheets URL to store subscriptions:")
sheet_url = st.text_input("Google Sheets URL", key='sheet_url')

if st.button("Upload Emails"):
    pinecone_utility = PineconeUtility(index="your_index_name")
    if pinecone_utility.upload_email_content(index="your_index_name", user_emails=user_emails, sheet_url=sheet_url):
        st.success("Emails uploaded and subscriptions stored successfully!")
    else:
        st.error("Failed to upload emails and store subscriptions.")