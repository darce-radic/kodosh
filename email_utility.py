import base64
import logging
from googleapiclient.discovery import build
from tqdm.auto import tqdm
import streamlit as st

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailUtility:
    def __init__(self):
        pass

    def _get_email_body(self, msg):
        logger.info("INSIDE GET MAIL")
        if 'parts' in msg['payload']:
            for part in msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = part['body']['data']
                    return base64.urlsafe_b64decode(body).decode('utf-8')
        else:
            body = msg['payload']['body'].get('data')
            if body:
                return base64.urlsafe_b64decode(body).decode('utf-8')
        return None

    def fetch_emails_within_time_period(self, service, start_date, end_date):
        try:
            logger.info("INSIDE GET MAIL IN PERIOD")
            all_emails = []
            query = f"after:{start_date} before:{end_date}"
            results = service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])
            all_emails.extend(messages)

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
                    
                    logger.info("INSIDE GET MAIL DETaILS")

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