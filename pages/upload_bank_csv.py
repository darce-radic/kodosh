import streamlit as st
import pandas as pd
from pinecone import Pinecone
from rag_agent import RagAgent
from pinecone_utility import PineconeUtility

st.title("Upload Bank CSV Files")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write("### Uploaded CSV File")
    st.dataframe(df)

    # Process the CSV file and store in Pinecone
    pinecone_utility = PineconeUtility(index="your_index_name")
    embeddings = []
    for idx, row in df.iterrows():
        description = row['Description']
        embedding = pinecone_utility.rag_agent.get_embedding(description)
        embeddings.append(embedding)

    data_with_metadata = pinecone_utility._combine_vector_and_text(
        documents=[{"text": row['Description'], "date": row['Date'], "amount": row['Amount']} for _, row in df.iterrows()],
        doc_embeddings=embeddings,
        user_email=None
    )
    pinecone_utility._upsert_data_to_pinecone(index="your_index_name", data_with_metadata=data_with_metadata)
    st.success("CSV file processed and data stored in Pinecone successfully!")

    # Identify potential subscriptions
    potential_subscriptions = []
    for idx, row in df.iterrows():
        description = row['Description']
        if any(keyword in description.lower() for keyword in ['subscription', 'renewal', 'billing']):
            potential_subscriptions.append({
                'date': row['Date'],
                'amount': row['Amount'],
                'description': description
            })

    # Store potential subscriptions in a new tab in the Google Sheet
    sheet_url = 'https://docs.google.com/spreadsheets/d/1juwBy3RK3XNeY6RWkPwqocJmDc4sb0QGetRdQuRA4Eg/export?format=csv'
    pinecone_utility._store_subscriptions_in_sheet(potential_subscriptions, sheet_url, sheet_name="Bank Subscriptions")
    st.success("Potential subscriptions identified and stored in Google Sheet successfully!")
