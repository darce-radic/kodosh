import hashlib
import logging
import pandas as pd
from tqdm.auto import tqdm
import streamlit as st
from gspread_dataframe import set_with_dataframe
from rag_agent import RagAgent
from email_utility import EmailUtility

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
        if content is None or content == "":
            return None
        hash_obj = hashlib.sha256()
        hash_obj.update(content.encode("utf-8"))
        return hash_obj.hexdigest()

    def _combine_vector_and_text(self, documents: list, doc_embeddings: list[list[float]], user_email: str = None) -> list[dict]:
        data_with_metadata = []
        for doc, embedding in zip(documents, doc_embeddings):
            doc_text = doc["text"]
            doc_date = doc.get("date")
            doc_amount = doc.get("amount")

            if doc_text is None or doc_text == "":
                continue

            doc_id = self._generate_short_id(doc_text)
            data_item = {
                "id": doc_id,
                "values": embedding,
                "metadata": {"user_email": user_email, "text": doc_text, "date": doc_date, "amount": doc_amount},
            }
            data_with_metadata.append(data_item)
        return data_with_metadata

    def _upsert_data_to_pinecone(self, index, data_with_metadata: list[dict]) -> None:
        try:
            index.upsert(vectors=data_with_metadata)
        except Exception as e:
            logger.error(f"Error upserting data to Pinecone: {e}")
            st.error("Failed to upsert data to Pinecone. Please try again.")

    def _store_subscriptions_in_sheet(self, subscriptions: list[dict], sheet_url: str, sheet_name: str = "Sheet1") -> None:
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
                emails = self.email_utility.fetch_emails_within_time_period(service, start_date, end_date)
                all_emails.extend(emails)

            progress_bar = st.progress(0)
            status_text = st.text("Creating embeddings...")

            batch_size = 100
            for i in range(0, len(all_emails), batch_size):
                batch_emails = all_emails[i:i+batch_size]
                embeddings = []
                all_subscriptions = []
                for idx, email in tqdm(enumerate(batch_emails), desc="Creating embeddings"):
                    status_text.text(f"Creating embedding {i + idx + 1} of {len(all_emails)}")
                    if email["text"] is None or email["text"] == "":
                        continue
                    try:
                        embeddings.append(self.rag_agent.get_embedding(email["text"]))
                        subscriptions = self._identify_subscriptions(email["text"])
                        all_subscriptions.extend(subscriptions)
                        progress_bar.progress((i + idx + 1) / len(all_emails))
                    except Exception as e:
                        logger.error(f"Error embedding email {i + idx}: {e}")
                        st.error("Failed to create embedding. Please try again.")

                data_with_meta_data = self._combine_vector_and_text(documents=batch_emails, doc_embeddings=embeddings, user_email=None)
                self._upsert_data_to_pinecone(index, data_with_metadata=data_with_meta_data)
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