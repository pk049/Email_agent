import streamlit as st
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import os

# Scopes required for the agent to function
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

def authenticate_user():
    """
    Handles the authentication flow.
    Returns: True if the user is authenticated, False otherwise.
    """
    # 1. Check if the user is already authenticated in this session
    if "gmail_service" in st.session_state and st.session_state.gmail_service:
        return True

    # 2. Check if the user is returning from the Google Login page (URL has ?code=...)
    if "code" in st.query_params:
        code = st.query_params["code"]
        try:
            # Retrieve client config from Streamlit secrets
            client_config = st.secrets["web_client"]
            
            # Create the OAuth flow
            flow = google_auth_oauthlib.flow.Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=st.secrets["redirect_url"]
            )
            
            # Exchange the authorization code for an access token
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Build the Gmail service for this specific user
            service = build('gmail', 'v1', credentials=credentials)
            
            # Store the service in the session state
            st.session_state.gmail_service = service
            
            # Clear the query parameters to clean up the URL
            st.query_params.clear()
            
            return True
            
        except Exception as e:
            st.error(f"❌ Authentication failed: {e}")
            return False

    return False

def show_login_button():
    """Generates and displays the 'Sign in with Google' button."""
    try:
        client_config = st.secrets["web_client"]
        
        flow = google_auth_oauthlib.flow.Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=st.secrets["redirect_url"]
        )
        
        # Generate the authorization URL
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        # Display a styled login button using HTML
        st.markdown(
            f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 50vh;">
                <h1 style="margin-bottom: 20px;">🤖 Agentic Email Assistant</h1>
                <p style="margin-bottom: 30px; color: #666;">Please sign in to allow the AI to access your Gmail.</p>
                <a href="{auth_url}" target="_self" style="text-decoration: none;">
                    <button style="
                        background-color: #4285F4; 
                        color: white; 
                        padding: 12px 24px; 
                        border: none; 
                        border-radius: 4px; 
                        font-size: 16px; 
                        font-weight: 500;
                        cursor: pointer;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        transition: background-color 0.3s;
                    ">
                        Sign in with Google
                    </button>
                </a>
            </div>
            """, 
            unsafe_allow_html=True
        )
    except Exception as e:
        st.error("⚠️ Error loading login configuration.")
        st.info("Please ensure 'web_client' and 'redirect_url' are set in your Streamlit secrets.")
        with st.expander("See Error Details"):
            st.code(str(e))