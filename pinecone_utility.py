import hashlib
import logging
import pandas as pd
import streamlit as st
from gspread_dataframe import set_with_dataframe
from rag_agent import RagAgent
from email_utility import EmailUtility
from googleapiclient.discovery import build
from concurrent.futures import ThreadPoolExecutor, as_completed

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

    def _process_email_batch(self, batch_emails, index, user_email, progress_bar, status_text, total_emails, current_batch):
        embeddings = []
        all_subscriptions = []
        for email in batch_emails:
            if email["text"] is None or email["text"] == "":
                continue
            try:
                embeddings.append(self.rag_agent.get_embedding(email["text"]))
                subscriptions = self._identify_subscriptions(email["text"])
                all_subscriptions.extend(subscriptions)
            except Exception as e:
                logger.error(f"Error processing email: {e}")
                st.error("Failed to process email. Please try again.")
        data_with_meta_data = self._combine_vector_and_text(documents=batch_emails, doc_embeddings=embeddings, user_email=user_email)
        self._upsert_data_to_pinecone(index, data_with_metadata=data_with_meta_data)
        progress_bar.progress((current_batch * 100) / total_emails)
        status_text.text(f"Processed {current_batch * 100} of {total_emails} emails")
        return all_subscriptions

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
                logger.info("INSIDE GET MAIL UTILITY")
                emails = self.email_utility.fetch_emails_within_time_period(service, start_date, end_date)
                all_emails.extend(emails)

            total_emails = len(all_emails)
            progress_bar = st.progress(0)
            status_text = st.text("Creating embeddings...")

            batch_size = 100
            all_subscriptions = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = []
                for i in range(0, total_emails, batch_size):
                    batch_emails = all_emails[i:i+batch_size]
                    futures.append(executor.submit(self._process_email_batch, batch_emails, index, user_emails[0], progress_bar, status_text, total_emails, i // batch_size + 1))

                for future in as_completed(futures):
                    try:
                        result = future.result()
                        all_subscriptions.extend(result)
                    except Exception as e:
                        logger.error(f"Error in batch processing: {e}")
                        st.error("Failed to process batch. Please try again.")

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

if st.button("Upload Emails"):
    pinecone_utility = PineconeUtility(index="your_index_name")
    if pinecone_utility.upload_email_content(index="your_index_name", user_emails=[st.session_state.user_email], sheet_url=st.session_state.sheet_url):
        st.success("Emails uploaded and subscriptions stored successfully!")
    else:
        st.error("Failed to upload emails and store subscriptions.")