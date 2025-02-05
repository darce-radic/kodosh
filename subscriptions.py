import streamlit as st
import pandas as pd
from pinecone_utility import PineconeUtility

def view_subscriptions():
    st.title("Subscriptions from Google Sheet")
    sheet_url = 'https://docs.google.com/spreadsheets/d/1juwBy3RK3XNeY6RWkPwqocJmDc4sb0QGetRdQuRA4Eg/export?format=csv'
    subscriptions_df = pd.read_csv(sheet_url)
    if not subscriptions_df.empty:
        st.write("Here are the potential subscriptions identified from your emails:")
        st.dataframe(subscriptions_df)
    else:
        st.write("No subscriptions found.")

def extract_subscriptions(pinecone_utility):
    st.title("Extract Subscriptions")
    # Add logic to extract subscriptions using pinecone_utility
