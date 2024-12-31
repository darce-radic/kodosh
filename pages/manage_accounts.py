import streamlit as st
from utility import authorize_gmail_api, switch_account, store_token

st.title("Manage Gmail Accounts")

# Display the current accounts
if "tokens" in st.session_state:
    st.write("### Authorized Accounts")
    account_list = list(st.session_state.tokens.keys())
    for account in account_list:
        st.write(account)
else:
    st.write("No accounts available. Please log in.")

# Add a new account
if st.button("Add New Account"):
    authorize_gmail_api()

# Switch to a different account
if "tokens" in st.session_state:
    selected_account = st.selectbox("Select Gmail Account to Switch", account_list)
    if st.button("Switch Account"):
        switch_account(selected_account)

# Remove an account
if "tokens" in st.session_state:
    selected_account_to_remove = st.selectbox("Select Gmail Account to Remove", account_list)
    if st.button("Remove Account"):
        if selected_account_to_remove in st.session_state.tokens:
            del st.session_state.tokens[selected_account_to_remove]
            st.success(f"Account {selected_account_to_remove} removed successfully!")
        else:
            st.error("Account not found.")