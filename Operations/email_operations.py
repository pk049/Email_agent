# ============================================================
# GMAIL OPERATIONS - STREAMLIT CLOUD READY (NO TOKEN CACHING)
# ============================================================

import base64
from email.mime.text import MIMEText
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
from langchain_core.tools import tool
import streamlit as st

# ============================================================
# SCOPES
# ============================================================
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# ============================================================
# GMAIL SERVICE INITIALIZATION (SERVICE ACCOUNT METHOD)
# ============================================================
def get_gmail_service():
    """
    Get authenticated Gmail service using Service Account from Streamlit secrets.
    No token caching - creates fresh connection each time.
    """
    try:
        # Get service account credentials from Streamlit secrets
        credentials_info = dict(st.secrets["google_service_account"])
        
        # Create credentials from service account info
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info,
            scopes=SCOPES
        )
        
        # If you need to impersonate a specific user (domain-wide delegation)
        # Uncomment and set the user email:
        # credentials = credentials.with_subject('user@yourdomain.com')
        
        # Build and return the Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        return service
        
    except Exception as e:
        st.error(f"❌ Gmail authentication failed: {e}")
        st.info("💡 Make sure you've added 'google_service_account' to Streamlit secrets")
        raise

# ============================================================
# ALTERNATIVE: OAUTH2 METHOD (For local development only)
# ============================================================
def get_gmail_service_oauth():
    """
    OAuth2 method for LOCAL DEVELOPMENT ONLY.
    This will NOT work on Streamlit Cloud.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    
    try:
        # Read credentials from Streamlit secrets (for local dev)
        credentials_json = dict(st.secrets["google_oauth_credentials"])
        
        # Create flow
        flow = InstalledAppFlow.from_client_config(
            credentials_json,
            SCOPES
        )
        
        # Run local server (ONLY works locally)
        creds = flow.run_local_server(port=8080)
        
        return build('gmail', 'v1', credentials=creds)
        
    except Exception as e:
        st.error(f"❌ OAuth authentication failed: {e}")
        raise

# ============================================================
# Initialize Gmail Service (Choose your method)
# ============================================================
try:
    # For Streamlit Cloud: Use Service Account
    service = get_gmail_service()
    print("✅ Gmail service authenticated successfully (Service Account)")
    
except Exception as e:
    print(f"⚠️ Gmail service initialization failed: {e}")
    service = None

# ============================================================
# HELPER FUNCTIONS (Internal use)
# ============================================================

def _get_email_details(message_id: str) -> Dict:
    """Internal helper to get email details"""
    if service is None:
        return {'error': 'Gmail service not initialized'}
    
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
        to = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
        
        return {
            'id': message_id,
            'subject': subject,
            'from': sender,
            'to': to,
            'date': date,
            'snippet': message.get('snippet', ''),
            'thread_id': message.get('threadId', '')
        }
    except Exception as e:
        return {'error': str(e)}


# ============================================================
# CORE EMAIL FUNCTIONS
# ============================================================

def send_email(to: str, subject: str, body: str) -> Dict:
    """Send an email to a recipient."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        send_message = {'raw': raw_message}
        
        result = service.users().messages().send(
            userId='me',
            body=send_message
        ).execute()
        
        return {
            'success': True,
            'message_id': result['id'],
            'message': f'Email sent successfully to {to}'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_recent_emails(max_results: int = 10, include_spam_trash: bool = False) -> Dict:
    """Get the most recent emails."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        max_results = min(max_results, 100)
        query = '' if include_spam_trash else '-in:spam -in:trash'
        
        results = service.users().messages().list(
            userId='me',
            maxResults=max_results,
            q=query
        ).execute()
        
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        
        return {'success': True, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def search_emails(query: str, max_results: int = 50) -> Dict:
    """Search emails using Gmail query syntax."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        max_results = min(max_results, 100)
        
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        
        return {'success': True, 'query': query, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def count_emails(query: str = "") -> Dict:
    """Count emails matching a query WITHOUT fetching full details."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        
        total_count = results.get('resultSizeEstimate', 0)
        
        return {
            'success': True,
            'query': query if query else 'all emails',
            'count': total_count
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_unread_emails(max_results: int = 20) -> Dict:
    """Get unread emails."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        max_results = min(max_results, 100)
        
        results = service.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        
        return {'success': True, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_emails_from_sender(sender_email: str, max_results: int = 50) -> Dict:
    """Get all emails from a specific sender."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        max_results = min(max_results, 100)
        query = f'from:{sender_email}'
        
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        
        return {'success': True, 'sender': sender_email, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_emails_by_date_range(start_date: str, end_date: str, max_results: int = 50) -> Dict:
    """Get emails within a date range."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        max_results = min(max_results, 100)
        start_date = start_date.replace('-', '/')
        end_date = end_date.replace('-', '/')
        
        query = f'after:{start_date} before:{end_date}'
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        
        return {
            'success': True,
            'start_date': start_date,
            'end_date': end_date,
            'count': len(emails),
            'emails': emails
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_email_body(message_id: str) -> Dict:
    """Get the full body content of a specific email."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        payload = message['payload']
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        break
        else:
            if 'data' in payload['body']:
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        
        return {
            'success': True,
            'message_id': message_id,
            'body': body,
            'metadata': _get_email_details(message_id)
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def reply_to_email(message_id: str, reply_body: str) -> Dict:
    """Reply to a specific email."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        original = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = original['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        to = next((h['value'] for h in headers if h['name'] == 'From'), '')
        message_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        
        reply = MIMEText(reply_body)
        reply['to'] = to
        reply['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
        reply['In-Reply-To'] = message_id_header
        reply['References'] = message_id_header
        
        raw_message = base64.urlsafe_b64encode(reply.as_bytes()).decode('utf-8')
        send_message = {
            'raw': raw_message,
            'threadId': original['threadId']
        }
        
        result = service.users().messages().send(
            userId='me',
            body=send_message
        ).execute()
        
        return {
            'success': True,
            'message_id': result['id'],
            'replied_to': message_id,
            'message': f'Reply sent successfully to {to}'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def mark_as_read(message_id: str) -> Dict:
    """Mark an email as read."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return {
            'success': True,
            'message_id': message_id,
            'message': 'Email marked as read'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def mark_as_unread(message_id: str) -> Dict:
    """Mark an email as unread."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': ['UNREAD']}
        ).execute()
        
        return {
            'success': True,
            'message_id': message_id,
            'message': 'Email marked as unread'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def delete_email(message_id: str) -> Dict:
    """Move an email to trash."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        service.users().messages().trash(
            userId='me',
            id=message_id
        ).execute()
        
        return {
            'success': True,
            'message_id': message_id,
            'message': 'Email moved to trash'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_email_labels() -> Dict:
    """Get all available Gmail labels."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        label_list = [{'id': label['id'], 'name': label['name']} for label in labels]
        
        return {'success': True, 'count': len(label_list), 'labels': label_list}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def add_label_to_email(message_id: str, label_id: str) -> Dict:
    """Add a label to an email."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        service.users().messages().modify(
            userId='me',
            id=message_id,
            body={'addLabelIds': [label_id]}
        ).execute()
        
        return {
            'success': True,
            'message_id': message_id,
            'label_id': label_id,
            'message': 'Label added successfully'
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_emails_with_attachments(max_results: int = 20) -> Dict:
    """Get emails that have attachments."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        max_results = min(max_results, 100)
        
        results = service.users().messages().list(
            userId='me',
            q='has:attachment',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        
        return {'success': True, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_starred_emails(max_results: int = 20) -> Dict:
    """Get starred/important emails."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        max_results = min(max_results, 100)
        
        results = service.users().messages().list(
            userId='me',
            q='is:starred',
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        
        return {'success': True, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_inbox_stats() -> Dict:
    """Get statistics about the inbox."""
    if service is None:
        return {'success': False, 'error': 'Gmail service not initialized'}
    
    try:
        total = count_emails("")['count']
        unread = count_emails("is:unread")['count']
        starred = count_emails("is:starred")['count']
        with_attachments = count_emails("has:attachment")['count']
        in_inbox = count_emails("in:inbox")['count']
        
        return {
            'success': True,
            'stats': {
                'total_emails': total,
                'unread_emails': unread,
                'starred_emails': starred,
                'emails_with_attachments': with_attachments,
                'emails_in_inbox': in_inbox,
                'read_emails': total - unread
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def count_emails_from_sender(sender_email: str) -> Dict:
    """Count total emails from a specific sender."""
    return count_emails(f"from:{sender_email}")


def count_emails_in_date_range(start_date: str, end_date: str) -> Dict:
    """Count emails within a date range."""
    start_date = start_date.replace('-', '/')
    end_date = end_date.replace('-', '/')
    return count_emails(f"after:{start_date} before:{end_date}")


# ============================================================
# LANGCHAIN TOOL WRAPPERS FOR LANGGRAPH
# ============================================================

@tool
def send_email_tool(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient.
    
    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body text
    """
    result = send_email(to, subject, body)
    return json.dumps(result)


@tool
def get_recent_emails_tool(max_results: int = 10, include_spam_trash: bool = False) -> str:
    """Get the most recent emails.
    
    Args:
        max_results: Number of emails to retrieve (default: 10, max: 100)
        include_spam_trash: Include spam and trash emails (default: False)
    """
    result = get_recent_emails(max_results, include_spam_trash)
    return json.dumps(result)


@tool
def search_emails_tool(query: str, max_results: int = 50) -> str:
    """Search emails using Gmail query syntax.
    
    Args:
        query: Gmail search query (e.g., 'from:user@example.com', 'subject:meeting', 'has:attachment')
        max_results: Maximum number of results (default: 50, max: 100)
    """
    result = search_emails(query, max_results)
    return json.dumps(result)


@tool
def count_emails_tool(query: str = "") -> str:
    """Count emails matching a query WITHOUT fetching full details. Fast.
    
    Args:
        query: Gmail search query (empty string = all emails)
    """
    result = count_emails(query)
    return json.dumps(result)


@tool
def get_unread_emails_tool(max_results: int = 20) -> str:
    """Get unread emails.
    
    Args:
        max_results: Maximum number of unread emails to retrieve
    """
    result = get_unread_emails(max_results)
    return json.dumps(result)


@tool
def get_emails_from_sender_tool(sender_email: str, max_results: int = 50) -> str:
    """Get all emails from a specific sender.
    
    Args:
        sender_email: Email address of the sender
        max_results: Maximum number of emails to retrieve
    """
    result = get_emails_from_sender(sender_email, max_results)
    return json.dumps(result)


@tool
def get_emails_by_date_range_tool(start_date: str, end_date: str, max_results: int = 50) -> str:
    """Get emails within a date range.
    
    Args:
        start_date: Start date in format 'YYYY/MM/DD' or 'YYYY-MM-DD'
        end_date: End date in format 'YYYY/MM/DD' or 'YYYY-MM-DD'
        max_results: Maximum number of emails to retrieve
    """
    result = get_emails_by_date_range(start_date, end_date, max_results)
    return json.dumps(result)


@tool
def get_email_body_tool(message_id: str) -> str:
    """Get the full body content of a specific email.
    
    Args:
        message_id: The ID of the email
    """
    result = get_email_body(message_id)
    return json.dumps(result)


@tool
def reply_to_email_tool(message_id: str, reply_body: str) -> str:
    """Reply to a specific email.
    
    Args:
        message_id: The ID of the email to reply to
        reply_body: The text of the reply
    """
    result = reply_to_email(message_id, reply_body)
    return json.dumps(result)


@tool
def mark_as_read_tool(message_id: str) -> str:
    """Mark an email as read.
    
    Args:
        message_id: The ID of the email to mark as read
    """
    result = mark_as_read(message_id)
    return json.dumps(result)


@tool
def mark_as_unread_tool(message_id: str) -> str:
    """Mark an email as unread.
    
    Args:
        message_id: The ID of the email to mark as unread
    """
    result = mark_as_unread(message_id)
    return json.dumps(result)


@tool
def delete_email_tool(message_id: str) -> str:
    """Move an email to trash.
    
    Args:
        message_id: The ID of the email to delete
    """
    result = delete_email(message_id)
    return json.dumps(result)


@tool
def get_inbox_stats_tool() -> str:
    """Get comprehensive inbox statistics (total, unread, starred, etc.).
    All counting done on server, very fast.
    """
    result = get_inbox_stats()
    return json.dumps(result)


@tool
def count_emails_from_sender_tool(sender_email: str) -> str:
    """Count total emails from a specific sender.
    
    Args:
        sender_email: Sender's email address
    """
    result = count_emails_from_sender(sender_email)
    return json.dumps(result)


@tool
def count_emails_in_date_range_tool(start_date: str, end_date: str) -> str:
    """Count emails within a date range.
    
    Args:
        start_date: Start date (YYYY/MM/DD or YYYY-MM-DD)
        end_date: End date (YYYY/MM/DD or YYYY-MM-DD)
    """
    result = count_emails_in_date_range(start_date, end_date)
    return json.dumps(result)


@tool
def get_emails_with_attachments_tool(max_results: int = 20) -> str:
    """Get emails that have attachments.
    
    Args:
        max_results: Maximum number of emails to retrieve
    """
    result = get_emails_with_attachments(max_results)
    return json.dumps(result)


@tool
def get_starred_emails_tool(max_results: int = 20) -> str:
    """Get starred/important emails.
    
    Args:
        max_results: Maximum number of emails to retrieve
    """
    result = get_starred_emails(max_results)
    return json.dumps(result)


@tool
def add_label_to_email_tool(message_id: str, label_id: str) -> str:
    """Add a label to an email.
    
    Args:
        message_id: The ID of the email
        label_id: The ID of the label to add
    """
    result = add_label_to_email(message_id, label_id)
    return json.dumps(result)


@tool
def get_email_labels_tool() -> str:
    """Get all available Gmail labels."""
    result = get_email_labels()
    return json.dumps(result)


# ============================================================
# EXPORT LANGCHAIN TOOLS FOR LANGGRAPH
# ============================================================

LANGCHAIN_TOOLS = [
    send_email_tool,
    get_recent_emails_tool,
    search_emails_tool,
    count_emails_tool,
    get_unread_emails_tool,
    get_emails_from_sender_tool,
    get_emails_by_date_range_tool,
    get_email_body_tool,
    reply_to_email_tool,
    mark_as_read_tool,
    mark_as_unread_tool,
    delete_email_tool,
    get_inbox_stats_tool,
    count_emails_from_sender_tool,
    count_emails_in_date_range_tool,
    get_emails_with_attachments_tool,
    get_starred_emails_tool,
    add_label_to_email_tool,
    get_email_labels_tool
]