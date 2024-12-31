import base64
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tqdm.auto import tqdm
import streamlit as st
from datetime import datetime

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailUtility:
    def __init__(self):
        pass

    def _get_email_body(self, msg):
        try:
            parts = msg['payload'].get('parts', [])
            if not parts:
                return msg['payload'].get('body', {}).get('data', '')

            body = ''
            for part in parts:
                if part['mimeType'] == 'text/plain':
                    body = part['body'].get('data', '')
                    break
                elif part['mimeType'] == 'text/html':
                    body = part['body'].get('data', '')
            return body
        except KeyError as e:
            logger.error(f"Error fetching email body: {e}")
            return ''

    def fetch_emails_within_time_period(self, service, start_date, end_date):
        try:
            # Convert dates to seconds since epoch
            start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            end_timestamp = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())

            query = f"after:{start_timestamp} before:{end_timestamp}"
            results = service.users().messages().list(userId='me', q=query).execute()
            messages = results.get('messages', [])

            emails = []
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id']).execute()
                email_data = self._extract_email_data(msg)
                if email_data:
                    emails.append(email_data)

            return emails
        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            st.error("Failed to fetch emails. Please try again.")
            return []

    def _extract_email_data(self, msg):
        try:
            headers = msg['payload']['headers']
            email_data = {
                'id': msg['id'],
                'threadId': msg['threadId'],
                'labelIds': msg.get('labelIds', []),
                'snippet': msg.get('snippet', ''),
                'historyId': msg.get('historyId', ''),
                'internalDate': msg.get('internalDate', ''),
                'sizeEstimate': msg.get('sizeEstimate', 0),
                'raw': msg.get('raw', ''),
                'payload': msg.get('payload', {}),
                'parts': msg.get('payload', {}).get('parts', []),
                'mimeType': msg.get('payload', {}).get('mimeType', ''),
                'filename': msg.get('payload', {}).get('filename', ''),
                'headers': headers,
                'text': self._get_email_body(msg)
            }
            return email_data
        except KeyError as e:
            logger.error(f"Error fetching email details: {e}")
            return None