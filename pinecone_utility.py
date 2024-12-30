import hashlib
from tqdm.auto import tqdm
import streamlit as st
from googleapiclient.discovery import build
import base64
import gspread  # Add this import for Google Sheets API
from gspread_dataframe import set_with_dataframe
from rag_agent import RagAgent
from safe_constants import MAX_CHARACTER_LENGTH_EMAIL
import logging
import os
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PineconeUtility():
    def __init__(self, index) -> None:
        try:
            self.rag_agent = RagAgent(index)
            self.gc = self._initialize_gspread()
        except Exception as e:
            logger.error(f"Error initializing PineconeUtility: {e}")
            st.error("Failed to initialize PineconeUtility. Please try again.")

    def _initialize_gspread(self):
        try:
            credentials = {
                "type": "service_account",
                "project_id": "solarprojectss",
                "private_key_id": "c486ef1b0896fd5d93e487b9d9710e1b2ca0674b",
                "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDMqDUPffEV6Yw/\ni7jPHylBST9lMPekzTZBUmei56Njq6ZLcjkattsGtFPtoiHS9HgH627ujkWCumvH\nXeMPKIuiSUWuLRW6xNrQcPp2xxqnLnYIhsOfLv3fMMRr/KtjqlmdKOuf9U1Gih9R\n2nyJbQbfhL5+ZpDc1Dr4F1c30IZOnP3lx/njkq0Td4tIJlO6do1G2pIaWQatfh6a\n4XkaDu3LuRDV0JlombUoD1RN+407dJ9AWkoNediPU1n187oeWg6d5Vf77Xw9yUe9\njv8Bp1mzQ/j0oBW4DjbFmdyCInZWbFPavpWq7UuZN7lIWoIoO9nF1edIKmdQOJlY\ncZ27PzENAgMBAAECgf8f+ihQQ11oDxXa1/oIYtYPXWKKbRxEo8vWaQnIamkdKbTS\nFQbXJbsTURnMB4lBbPFUS3UJ0TELPBWbERBpTeyDbu90R5cdl6SY7Q41gOapOJk4\nu9XVCYKhXP1T4ibla7iU1c/7LljkrLA4Getbja2FPziEh4Ia/w43tW3rSqmxno5Y\nbdojFTVKgPv9xp39CJpVkyG7BDhxV/oXD1AU4cC+APXpfB00RX4prqJXh1EfX1DH\nuAYVGK2HBEEb6VwF6W8f4idrukdO6WIob2Nh2XDUZgIgsXRsxhE/6xfPlmG1jhO2\nSRDocWqXNOkJBbVp9o0K01PxkXxxIuVNRN2SeAECgYEA9ZjjUAhJSVQyuwwR3KX4\nmFFNcAlMfLCDMLoLuooGGSuCXUuzJE6HSmh59BEN8CB1t1hV+UdCz8pkqQZeCrBU\n+uvdnpfWq6+3ystkNRzTbstzB8maSFWxH48SBjWhVFWyWEUHEKIzAAD2mrLKCQtP\nMezI1o0bkqVgtlJL53gD2c0CgYEA1VNjZjuz+vRP2d2dXv0gkprQjOmzQKYrcYCZ\nkNuWsKHFZ0dDsLE0WytDea8WMonI5u4yXtilXmB841TsSXKu83Zl8Qs/I4Zzdhm6\nfkNOpo8+x2aIeW2zikNsCztZgBq7WeAyijJFBPqqtqLLtlI5rjakS87sFJoPU2t+\nPa3kdEECgYEAs/P2eunXaRd8pHlPjTE/WbwY1YK6vJJJTibD+Uaw+ThcKSgSdwPj\nNa4fzanBYLUoC9N6C1Efr0lJQGAeAA779W9lz5LKBLqYHMuy/QfGFGSWQJqDpYTE\nZ69ZMZuSPk0chHjvmEyAufv6tZdTWhUjTh2Fe0+haG4s0uqyG0Rg7fECgYEAhpsU\niGi5u2s3i4hsCYj9aaRoXdIE+pEfroHv5Fi67/9TuURdcPuPxss4y2pwPjl03EqG\n3BQl3LRTeXqXkgzcWeFml795+qeW6Xl4lL1RvoV6noWTLdPLyz2ZykiLw+qaNy7h\nlRP9OxQUbiOxGP0vSj9OUkth6eoAK6oTQUYddkECgYEAu3q1qRg6ShNtvCn0swZs\npD7yX3hw+3FkOGkBkMRFfEvifSuLFvAE+Gy4etwdS1MUIzcBkFDfF55Y+9A5B4UW\ng0GaIPsQv7Yi4kX7Yfb84wRsaxQiDQOkDBfATy5vn5qRbizoY3bHaC7RmYNMxVzm\nB4hSvxL5gugQY8FN/EG8VKI=\n-----END PRIVATE KEY-----\n",
                "client_email": "ghlconnect@solarprojectss.iam.gserviceaccount.com",
                "client_id": "113910955082449298707",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/ghlconnect%40solarprojectss.iam.gserviceaccount.com"
            }
            return gspread.service_account_from_dict(credentials)
        except Exception as e:
            logger.error(f"Error initializing gspread: {e}")
            st.error("Failed to initialize gspread. Please check your credentials.")

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
            doc_date = doc.get("date")
            doc_amount = doc.get("amount")

            if doc_text is None or doc_text == "": continue

            # Generate a unique ID based on the text content
            doc_id = self._generate_short_id(doc_text)

            # Create a data item dictionary
            data_item = {
                "id": doc_id,
                "values": embedding,
                "metadata": {"user_email": user_email, "text": doc_text, "date": doc_date, "amount": doc_amount},  # Include the text as metadata
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
        try:
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
        except Exception as e:
            logger.error(f"Error getting email body: {e}")
            st.error("Failed to get email body. Please try again.")

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
        try:
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
                    logger.error(f"Error fetching email details: {e}")
                    st.error("Failed to fetch email details. Please try again.")

            return email_details
        except Exception as e:
            logger.error(f"Error fetching emails within time period: {e}")
            st.error("Failed to fetch emails. Please try again.")

    def _identify_subscriptions(self, email_text: str) -> list[str]:
        """
        Identify potential subscriptions from the email text.

        Args:
        - email_text (str): The text content of the email.

        Returns:
        - subscriptions (list[str]): A list of identified subscriptions.
        """
        try:
            # Use RAG to identify potential subscriptions
            subscriptions = self.rag_agent.identify_subscriptions(email_text)
            return subscriptions
        except Exception as e:
            logger.error(f"Error identifying subscriptions: {e}")
            st.error("Failed to identify subscriptions. Please try again.")

    def _store_subscriptions_in_sheet(self, subscriptions: list[dict[str, str]], sheet_url: str, sheet_name: str = "Sheet1") -> None:
        """
        Store identified subscriptions in a Google Sheets document.

        Args:
        - subscriptions (list[dict[str, str]]): A list of identified subscriptions.
        - sheet_url (str): The URL of the Google Sheets document.
        - sheet_name (str): The name of the sheet to store the data in.

        Returns:
        - None
        """
        try:
            sh = self.gc.open_by_url(sheet_url)
            try:
                worksheet = sh.worksheet(sheet_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sh.add_worksheet(title=sheet_name, rows="100", cols="20")

            existing_data = worksheet.get_all_records()
            new_data = pd.DataFrame(subscriptions)
            updated_data = pd.concat([pd.DataFrame(existing_data), new_data], ignore_index=True)
            worksheet.clear()
            set_with_dataframe(worksheet, updated_data)
        except Exception as e:
            logger.error(f"Error storing subscriptions in sheet: {e}")
            st.error("Failed to store subscriptions in sheet. Please try again.")

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
        try:
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

            # Process emails in batches
            batch_size = 100
            for i in range(0, len(all_emails), batch_size):
                batch_emails = all_emails[i:i+batch_size]
                embeddings = []
                all_subscriptions = []
                for idx, email in tqdm(enumerate(batch_emails), desc="Creating embeddings"):
                    status_text.text(f"Creating embedding {i + idx + 1} of {len(all_emails)}")
                    if email["text"] is None or email["text"] == "": continue
                    try:
                        embeddings.append(self.rag_agent.get_embedding(email["text"]))
                        # Identify subscriptions
                        subscriptions = self._identify_subscriptions(email["text"])
                        all_subscriptions.extend(subscriptions)
                        # Update the progress bar and status text
                        progress_bar.progress((i + idx + 1) / len(all_emails))  # Progress bar update
                    except Exception as e:
                        logger.error(f"Error embedding email {i + idx}: {e}")
                        st.error("Failed to create embedding. Please try again.")

                data_with_meta_data = self._combine_vector_and_text(documents=batch_emails, doc_embeddings=embeddings, user_email=None) 
                self._upsert_data_to_pinecone(index, data_with_metadata=data_with_meta_data)

                # Store identified subscriptions in Google Sheets
                self._store_subscriptions_in_sheet(all_subscriptions, sheet_url)

            return True
        except Exception as e:
            logger.error(f"Error uploading email content: {e}")
            st.error("Failed to upload email content. Please try again.")

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