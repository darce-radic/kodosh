import streamlit as st
import pandas as pd
from pinecone_utility import PineconeUtility

st.title("Manage Subscriptions")

def write_subscriptions_to_sheet():
    pinecone_utility = PineconeUtility(index="your_index_name")
    sheet_url = st.session_state.sheet_url
    all_subscriptions = pinecone_utility.get_all_subscriptions()
    pinecone_utility._store_subscriptions_in_sheet(all_subscriptions, sheet_url)
    st.success("Subscriptions stored successfully!")

if st.button("Write Subscriptions to Sheet"):
    write_subscriptions_to_sheet()

sheet_url = 'https://docs.google.com/spreadsheets/d/1juwBy3RK3XNeY6RWkPwqocJmDc4sb0QGetRdQuRA4Eg/export?format=csv'
subscriptions_df = pd.read_csv(sheet_url)

if not subscriptions_df.empty:
    st.write("Here are the potential subscriptions identified from your emails:")
    st.dataframe(subscriptions_df)
else:
    st.write("No subscriptions found.")
