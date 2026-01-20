import streamlit as st
import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import traceback

# Gmail API scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_google_oauth_flow():
    """Initialize Google OAuth flow"""
    try:
        # Get redirect URL and strip any whitespace
        redirect_url = st.secrets.get("redirect_url")
        
        print(f"[DEBUG] Redirect URL from secrets: '{redirect_url}'")
        print(f"[DEBUG] Redirect URL length: {len(redirect_url)}")
        
        client_config = {
            "web": {
                "client_id": st.secrets["web_client"]["client_id"],
                "client_secret": st.secrets["web_client"]["client_secret"],
                "auth_uri": st.secrets["web_client"]["auth_uri"],
                "token_uri": st.secrets["web_client"]["token_uri"],
                "redirect_uris": [redirect_url]
            }
        }
        
        print(f"[DEBUG] Client ID: {st.secrets['web_client']['client_id'][:20]}...")
        print(f"[DEBUG] Auth URI: {st.secrets['web_client']['auth_uri']}")
        print(f"[DEBUG] Token URI: {st.secrets['web_client']['token_uri']}")
        
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_url
        )
        
        print(f"[DEBUG] Flow created successfully with redirect_uri: '{flow.redirect_uri}'")
        return flow
        
    except KeyError as e:
        error_msg = f"Missing secret configuration: {e}"
        print(f"[ERROR] {error_msg}")
        st.error(error_msg)
        st.info("Please add the following to your Streamlit secrets:")
        st.code("""
# Required secrets structure:
redirect_url = "your-app-url"

[web_client]
client_id = "your-client-id"
client_secret = "your-client-secret"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
        """)
        return None
    except Exception as e:
        error_msg = f"Unexpected error in get_google_oauth_flow: {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        st.error(error_msg)
        return None

def show_login_button():
    """Display the Google login interface"""
    st.title("📧 Email Agent - Login Required")
    st.markdown("### Please sign in with your Google account to continue")
    
    # Get authorization URL
    flow = get_google_oauth_flow()
    if flow is None:
        st.stop()
    
    # Show debug info in the UI
    st.info(f"🔍 **Debug Info:**\n\nRedirect URI being used:\n`{flow.redirect_uri}`")
    st.warning("⚠️ Make sure this EXACTLY matches one of your Authorized redirect URIs in Google Cloud Console")
    
    try:
        auth_url, state = flow.authorization_url(prompt='consent')
        print(f"[DEBUG] Authorization URL generated: {auth_url[:100]}...")
        print(f"[DEBUG] State: {state}")
        
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
        
    except Exception as e:
        error_msg = f"Error generating authorization URL: {str(e)}"
        print(f"[ERROR] {error_msg}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        st.error(error_msg)

def authenticate_user():
    """
    Handle Google OAuth authentication and return True if authenticated.
    This function also handles the OAuth callback.
    """
    print("[DEBUG] authenticate_user() called")
    
    # Check if we're handling an OAuth callback
    query_params = st.query_params
    print(f"[DEBUG] Query params: {dict(query_params)}")
    
    if "code" in query_params:
        # User is coming back from Google OAuth
        print("[DEBUG] Authorization code found in query params")
        code = query_params["code"]
        print(f"[DEBUG] Code length: {len(code)}")
        
        # Check for error in query params
        if "error" in query_params:
            error = query_params["error"]
            error_msg = f"OAuth error: {error}"
            print(f"[ERROR] {error_msg}")
            st.error(error_msg)
            st.error("Please try logging in again or check your Google Cloud Console configuration.")
            return False
        
        try:
            print("[DEBUG] Creating flow for token exchange...")
            flow = get_google_oauth_flow()
            
            if flow is None:
                print("[ERROR] Flow is None, cannot proceed")
                return False
            
            print(f"[DEBUG] Flow redirect_uri: '{flow.redirect_uri}'")
            print("[DEBUG] Attempting to fetch token...")
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            print("[DEBUG] Token fetched successfully!")
            print(f"[DEBUG] Token: {credentials.token[:20]}..." if credentials.token else "[DEBUG] No token")
            print(f"[DEBUG] Has refresh token: {credentials.refresh_token is not None}")
            
            # Store credentials in session state
            st.session_state.credentials = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            
            print("[DEBUG] Credentials stored in session state")
            
            # Build Gmail service
            creds = Credentials(
                token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_uri=credentials.token_uri,
                client_id=credentials.client_id,
                client_secret=credentials.client_secret,
                scopes=credentials.scopes
            )
            
            print("[DEBUG] Building Gmail service...")
            st.session_state.gmail_service = build('gmail', 'v1', credentials=creds)
            print("[DEBUG] Gmail service built successfully!")
            
            # Clear the query parameters
            st.query_params.clear()
            print("[DEBUG] Query params cleared, rerunning...")
            st.rerun()
            
        except Exception as e:
            error_msg = f"Authentication failed: {str(e)}"
            print(f"[ERROR] {error_msg}")
            print(f"[ERROR] Full traceback:\n{traceback.format_exc()}")
            
            st.error(f"❌ Authentication Error: {error_msg}")
            st.error("**Common causes:**")
            st.markdown("""
            - Redirect URI mismatch between Google Cloud Console and Streamlit secrets
            - Invalid client ID or client secret
            - OAuth consent screen not properly configured
            - Gmail API not enabled in Google Cloud Console
            """)
            
            # Show detailed error for debugging
            with st.expander("🔍 View detailed error"):
                st.code(traceback.format_exc())
            
            return False
    
    # Check if user is already authenticated
    if "credentials" in st.session_state and "gmail_service" in st.session_state:
        print("[DEBUG] User already authenticated")
        return True
    
    print("[DEBUG] User not authenticated")
    return False