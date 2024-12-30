import streamlit as st
import pandas as pd
from pinecone_utility import PineconeUtility

def view_subscriptions():
    st.title("Subscriptions from Google Sheet")
    sheet_url = 'https://docs.google.com/spreadsheets/d/1juwBy3RK3XNeY6RWkPwqocJmDc4sb0QGetRdQuRA4Eg/export?format=csv'
    subscriptions_df = pd.read_csv(sheet_url)
    st.dataframe(subscriptions_df)

def extract_subscriptions(pinecone_utility):
    st.title("Extracted Subscriptions")

    # Extract subscriptions using RAG and Pinecone
    email_data = pinecone_utility.fetch_all_email_data()
    subscriptions = []
    for email in email_data:
        text = email.get('text', '').lower()
        if any(keyword in text for keyword in ['subscription', 'unsubscribe', 'renewal', 'billing']):
            subscriptions.append({
                'email_id': email.get('id'),
                'subject': email.get('subject'),
                'from': email.get('from'),
                'date': email.get('date'),
                'subscription_info': text
            })

    # Display subscriptions in the app
    if subscriptions:
        subscriptions_df = pd.DataFrame(subscriptions)
        st.dataframe(subscriptions_df)

        # Update the Google Sheet
        sheet_url = 'https://docs.google.com/spreadsheets/d/1juwBy3RK3XNeY6RWkPwqocJmDc4sb0QGetRdQuRA4Eg/export?format=csv'
        subscriptions_df.to_csv(sheet_url, index=False)
        st.success("Subscriptions have been updated in the Google Sheet.")
    else:
        st.write("No subscriptions found.")
