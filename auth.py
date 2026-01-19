import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_google_oauth_flow():
    """Initialize Google OAuth flow"""
    client_config = {
        "web": {
            "client_id": st.secrets["web_client"]["client_id"],
            "client_secret": st.secrets["web_client"]["client_secret"],
            "auth_uri": st.secrets["web_client"]["auth_uri"],
            "token_uri": st.secrets["web_client"]["token_uri"],
            "redirect_uris": [st.secrets["redirect_url"]]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=st.secrets["redirect_url"]
    )
    return flow

def show_login_button():
    """Display the Google login interface"""
    st.title("📧 Email Agent - Login Required")
    st.markdown("### Please sign in with your Google account to continue")
    
    # Get authorization URL
    flow = get_google_oauth_flow()
    auth_url, _ = flow.authorization_url(prompt='consent')
    
    # Display login button
    st.markdown(f"""
        <a href="{auth_url}" target="_self">
            <button style="
                background-color: #4285f4;
                color: white;
                padding: 12px 24px;
                font-size: 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                display: flex;
                align-items: center;
                gap: 10px;
            ">
                <img src="https://www.google.com/favicon.ico" width="20" height="20">
                Sign in with Google
            </button>
        </a>
    """, unsafe_allow_html=True)
    
    st.info("You'll be redirected to Google to authorize access to your Gmail account.")

def authenticate_user():
    """
    Handle Google OAuth authentication and return True if authenticated.
    This function also handles the OAuth callback.
    """
    # Check if we're handling an OAuth callback
    query_params = st.query_params
    
    if "code" in query_params:
        # User is coming back from Google OAuth
        code = query_params["code"]
        
        try:
            # Exchange authorization code for credentials
            flow = get_google_oauth_flow()
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Store credentials in session state
            st.session_state.credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            # Build Gmail service
            creds = Credentials(
                token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
                scopes=credentials.scopes
            )
            st.session_state.gmail_service = build('gmail', 'v1', credentials=creds)
            
            # Clear the query parameters
            st.query_params.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            return False
    
    # Check if user is already authenticated
    if "credentials" in st.session_state and "gmail_service" in st.session_state:
        return True
    
    return False