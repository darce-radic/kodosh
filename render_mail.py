import streamlit as st
import html

def render_mail(selected_mail):
    email_subject = html.escape(selected_mail["subject"])
    email_sender = html.escape(selected_mail["sender"])
    email_date = html.escape(selected_mail["date"])
    email_content = html.escape(selected_mail["text"])
    st.write(f"**Subject:** {email_subject}")
    st.write(f"**From:** {email_sender}")
    st.write(f"**Date:** {email_date}")
    st.write(f"**Content:** {email_content}")

def update_selected_mail():
    query_params = st.experimental_get_query_params()
    # Add logic to update selected mail using query_params
    pass

def render_most_relevant_mails():
    # Add logic to render most relevant mails
    pass
