import streamlit as st
import html

def render_mail(selected_mail):
    email_subject = html.escape(selected_mail["subject"])
    email_sender = html.escape(selected_mail["sender"])
    email_date = html.escape(selected_mail["date"])
    email_content = html.escape(selected_mail["text"])
    email_link = selected_mail["email_link"]  # Get the email link from the selected_mail dictionary

    # Custom CSS for styling the box and button
    st.markdown(
        """
        <style>
        .email-box {
            background-color: #f0f9ff;
            border: 1px solid #d1e7dd;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
        }
        .email-content {
            color: #333333;
            font-size: 16px;
            margin-top: 10px;
        }
        .email-header {
            font-weight: bold;
            font-size: 18px;
            margin-bottom: 5px;
        }
        .email-subheader {
            color: #6c757d;
            font-size: 14px;
            margin-bottom: 5px;
        }
        .email-link {
            font-size: 16px;
            margin-top: 20px;
            display: inline-block;
            background-color: #ff8c00; /* Orange background */
            color: white !important; /* Ensure white text */
            padding: 10px 20px;
            text-align: center;
            border-radius: 8px;
            text-decoration: none;
            transition: background-color 0.3s ease; /* Smooth transition */
        }
        .email-link:hover {
            background-color: #e67600; /* Darker orange on hover */
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Display the email inside a styled box with the clickable button link
    st.markdown(f"""
    <div class="email-box">
        <div class="email-header">Subject: <span>{email_subject}</span></div>
        <div class="email-subheader">From: <span>{email_sender}</span> | Date: <span>{email_date}</span></div>
        <a href="{email_link}" target="_blank" class="email-link">Open Email in Gmail</a>
        <div class="email-content"><span>{email_content}</span></div>
    </div>
    """, unsafe_allow_html=True)

def update_selected_mail():
    st.session_state.selected_mail = st.session_state.most_relevant_mails[st.session_state.selected_mail_index]

def render_most_relevant_mails():
    col1, col_mid, col2 = st.columns([1, 1, 1])
    with col1:
        if st.button("← Previous"):
            if st.session_state.selected_mail_index == 0: st.warning("No more emails to show")
            else:
                st.session_state.selected_mail_index -= 1
                update_selected_mail()

    with col2:
        if st.button("Next →"):
            if st.session_state.selected_mail_index == len(st.session_state.most_relevant_mails) - 1: st.warning("No more emails to show")
            else:
                st.session_state.selected_mail_index += 1
                update_selected_mail()

    with col_mid:
        st.write(f"Email {st.session_state.selected_mail_index + 1}/{len(st.session_state.most_relevant_mails)}")

    # Update selected mail if not already set
    if "selected_mail" not in st.session_state:
        update_selected_mail()
    
    # Render the currently selected email
    if st.session_state.selected_mail: render_mail(st.session_state.selected_mail)
