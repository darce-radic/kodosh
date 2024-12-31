import hashlib
import logging
import streamlit as st
from gspread_dataframe import set_with_dataframe
from rag_agent import RagAgent
from email_utility import EmailUtility
from googleapiclient.discovery import build
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import base64
from tqdm.auto import tqdm
from safe_constants import MAX_CHARACTER_LENGTH_EMAIL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeUtility:
    def __init__(self, index) -> None:
        try:
            self.rag_agent = RagAgent(index)
            self.email_utility = EmailUtility()
        except Exception as e:
            logger.error(f"Error initializing PineconeUtility: {e}")
            st.error("Failed to initialize PineconeUtility. Please try again.")

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

    def _combine_vector_and_text(self, documents: list[any], doc_embeddings: list[list[float]], user_email: str = None) -> list[dict[str, any]]:
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
            doc_text = doc.get("text", "")
            doc_date = doc.get("date", "")
            doc_sender = doc.get("from", "")
            doc_subject = doc.get("subject", "")
            doc_email_link = doc.get("email_link", "")

            if doc_text is None or doc_text == "":
                continue

            # Generate a unique ID based on the text content
            doc_id = self._generate_short_id(doc_text)

            # Create a data item dictionary
            data_item = {
                "id": doc_id,
                "values": embedding,
                "metadata": {
                    "user_email": user_email,
                    "text": doc_text[:1000],  # Truncate text to reduce metadata size
                    "date": doc_date,
                    "sender": doc_sender,
                    "subject": doc_subject,
                    "email_link": doc_email_link
                },
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
        try:
            index.upsert(vectors=data_with_metadata)
        except Exception as e:
            logger.error(f"Error upserting data to Pinecone: {e}")
            st.error("Failed to upsert data to Pinecone. Please try again.")

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

    def _list_emails_with_details(self, service, max_emails=100, start_date=None, end_date=None):
        all_emails = []
        query = ""
        if start_date and end_date:
            query = f"after:{start_date.strftime('%Y/%m/%d')} before:{end_date.strftime('%Y/%m/%d')}"
        results = service.users().messages().list(userId='me', maxResults=max_emails, q=query).execute()
        
        # Fetch the first page of messages
        messages = results.get('messages', [])
        all_emails.extend(messages)

        # Keep fetching emails until we reach the max limit or there are no more pages
        while 'nextPageToken' in results and len(all_emails) < max_emails:
            page_token = results['nextPageToken']
            results = service.users().messages().list(userId='me', pageToken=page_token, q=query).execute()
            messages = results.get('messages', [])
            all_emails.extend(messages)

            # Break if we exceed the max limit
            if len(all_emails) >= max_emails:
                all_emails = all_emails[:max_emails]  # Trim to max limit
                break

        progress_bar2 = st.progress(0)
        status_text2 = st.text("Retrieving your emails...")

        email_details = []
        for idx, email in tqdm(enumerate(all_emails), desc="Fetching email details"):
            # Fetch full email details
            msg = service.users().messages().get(userId='me', id=email['id']).execute()
            headers = msg['payload']['headers']

            email_text = self._get_email_body(msg)
            if email_text is None or email_text == "":
                continue
            if len(email_text) >= MAX_CHARACTER_LENGTH_EMAIL:
                email_text = email_text[:MAX_CHARACTER_LENGTH_EMAIL]  # Truncate long emails
            
            # Extract date, sender, and subject from headers
            email_data = {
                "text": email_text,
                'id': msg['id'],
                'date': next((header['value'] for header in headers if header['name'] == 'Date'), None),
                'from': next((header['value'] for header in headers if header['name'] == 'From'), None),
                'subject': next((header['value'] for header in headers if header['name'] == 'Subject'), None),
                "email_link": f"https://mail.google.com/mail/u/0/#inbox/{email['id']}"
            }
            email_details.append(email_data)
            progress_bar2.progress((idx + 1) / len(all_emails))  # Progress bar update
            status_text2.text(f"Retrieving email {idx + 1} of {len(all_emails)}")

        return email_details

    def upload_email_content(self, index, user_email=None, max_emails=100, start_date=None, end_date=None):
        # Build Gmail service
        if not st.session_state.creds: 
            st.error("Please login first")
            return
        service = build('gmail', 'v1', credentials=st.session_state.creds)
        emails = self._list_emails_with_details(service, max_emails=max_emails, start_date=start_date, end_date=end_date)

        progress_bar = st.progress(0)
        status_text = st.text("Creating embeddings...")

        # Embed emails
        embeddings = []
        for idx, email in tqdm(enumerate(emails), desc="Creating embeddings"):
            status_text.text(f"Creating embedding {idx + 1} of {len(emails)}")
            if email["text"] is None or email["text"] == "":
                continue
            try:
                embeddings.append(self.rag_agent.get_embedding(email["text"]))
                # Update the progress bar and status text
                progress_bar.progress((idx + 1) / len(emails))  # Progress bar update
            except Exception as e:
                logger.error(f"Error embedding email {idx}: {e}")

        data_with_meta_data = self._combine_vector_and_text(documents=emails, doc_embeddings=embeddings, user_email=user_email) 
        self._upsert_data_to_pinecone(index, data_with_metadata=data_with_meta_data)

        return True

    def get_all_subscriptions(self):
        # This method should return all subscriptions
        # Implement the logic to fetch all subscriptions
        return []

# Streamlit UI for specifying date range and multiple email accounts
st.title("Email Content Uploader")
st.write("Specify the date range for fetching emails:")

start_date = st.date_input("Start date", key='start_date')
end_date = st.date_input("End date", key='end_date')

if st.button("Upload Emails"):
    pinecone_utility = PineconeUtility(index="your_index_name")
    if pinecone_utility.upload_email_content(index="your_index_name", user_email=st.session_state.user_email, start_date=start_date, end_date=end_date):
        st.success("Emails uploaded and subscriptions stored successfully!")
    else:
        st.error("Failed to upload emails and store subscriptions.")