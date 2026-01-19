import base64
import json
from email.mime.text import MIMEText
from typing import Dict, List, Optional
from googleapiclient.discovery import build
from langchain_core.tools import tool
import streamlit as st

# ============================================================
# DYNAMIC SERVICE RETRIEVAL
# ============================================================
def get_gmail_service():
    """Retrieve the Gmail service from the current user's session state."""
    # This ensures we get the specific connection for the user currently interacting with the app
    if 'gmail_service' not in st.session_state:
        return None
    return st.session_state.gmail_service

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _get_email_details(message_id: str) -> Dict:
    service = get_gmail_service()
    if not service: return {'error': 'Authentication required'}
    
    try:
        message = service.users().messages().get(
            userId='me', id=message_id, format='full'
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
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    
    try:
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        result = service.users().messages().send(
            userId='me', body={'raw': raw_message}
        ).execute()
        return {'success': True, 'message_id': result['id'], 'message': f'Email sent to {to}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_recent_emails(max_results: int = 10, include_spam_trash: bool = False) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    
    try:
        query = '' if include_spam_trash else '-in:spam -in:trash'
        results = service.users().messages().list(
            userId='me', maxResults=min(max_results, 50), q=query
        ).execute()
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        return {'success': True, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def search_emails(query: str, max_results: int = 20) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    
    try:
        results = service.users().messages().list(
            userId='me', q=query, maxResults=min(max_results, 50)
        ).execute()
        messages = results.get('messages', [])
        emails = [_get_email_details(msg['id']) for msg in messages]
        return {'success': True, 'query': query, 'count': len(emails), 'emails': emails}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def count_emails(query: str = "") -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    
    try:
        results = service.users().messages().list(
            userId='me', q=query, maxResults=1
        ).execute()
        total_count = results.get('resultSizeEstimate', 0)
        return {'success': True, 'query': query if query else 'all', 'count': total_count}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_unread_emails(max_results: int = 20) -> Dict:
    return search_emails('is:unread', max_results)

def get_emails_from_sender(sender_email: str, max_results: int = 20) -> Dict:
    return search_emails(f'from:{sender_email}', max_results)

def get_emails_by_date_range(start_date: str, end_date: str, max_results: int = 20) -> Dict:
    start_date = start_date.replace('-', '/')
    end_date = end_date.replace('-', '/')
    return search_emails(f'after:{start_date} before:{end_date}', max_results)

def get_email_body(message_id: str) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    
    try:
        message = service.users().messages().get(
            userId='me', id=message_id, format='full'
        ).execute()
        
        payload = message['payload']
        body = ""
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain' and 'data' in part['body']:
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
        return {'success': True, 'message_id': message_id, 'body': body, 'metadata': _get_email_details(message_id)}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def reply_to_email(message_id: str, reply_body: str) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    
    try:
        original = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = original['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        to = next((h['value'] for h in headers if h['name'] == 'From'), '')
        msg_id_header = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
        
        reply = MIMEText(reply_body)
        reply['to'] = to
        reply['subject'] = f"Re: {subject}" if not subject.startswith('Re:') else subject
        reply['In-Reply-To'] = msg_id_header
        reply['References'] = msg_id_header
        
        raw_message = base64.urlsafe_b64encode(reply.as_bytes()).decode('utf-8')
        result = service.users().messages().send(
            userId='me', body={'raw': raw_message, 'threadId': original['threadId']}
        ).execute()
        
        return {'success': True, 'message_id': result['id'], 'message': 'Reply sent successfully'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def mark_as_read(message_id: str) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    try:
        service.users().messages().modify(
            userId='me', id=message_id, body={'removeLabelIds': ['UNREAD']}
        ).execute()
        return {'success': True, 'message_id': message_id, 'message': 'Marked as read'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def mark_as_unread(message_id: str) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    try:
        service.users().messages().modify(
            userId='me', id=message_id, body={'addLabelIds': ['UNREAD']}
        ).execute()
        return {'success': True, 'message_id': message_id, 'message': 'Marked as unread'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def delete_email(message_id: str) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    try:
        service.users().messages().trash(userId='me', id=message_id).execute()
        return {'success': True, 'message_id': message_id, 'message': 'Moved to trash'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_inbox_stats() -> Dict:
    try:
        total = count_emails("")['count']
        unread = count_emails("is:unread")['count']
        starred = count_emails("is:starred")['count']
        return {
            'success': True,
            'stats': {'total': total, 'unread': unread, 'starred': starred}
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

def add_label_to_email(message_id: str, label_id: str) -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    try:
        service.users().messages().modify(
            userId='me', id=message_id, body={'addLabelIds': [label_id]}
        ).execute()
        return {'success': True, 'message': f'Label {label_id} added'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def get_email_labels() -> Dict:
    service = get_gmail_service()
    if not service: return {'success': False, 'error': 'Not logged in'}
    try:
        results = service.users().labels().list(userId='me').execute()
        return {'success': True, 'labels': results.get('labels', [])}
    except Exception as e:
        return {'success': False, 'error': str(e)}

# ============================================================
# LANGCHAIN TOOLS (WRAPPERS)
# ============================================================

@tool
def send_email_tool(to: str, subject: str, body: str) -> str:
    """Send an email to a recipient."""
    return json.dumps(send_email(to, subject, body))

@tool
def get_recent_emails_tool(max_results: int = 10, include_spam_trash: bool = False) -> str:
    """Get the most recent emails."""
    return json.dumps(get_recent_emails(max_results, include_spam_trash))

@tool
def search_emails_tool(query: str, max_results: int = 20) -> str:
    """Search emails using Gmail query syntax."""
    return json.dumps(search_emails(query, max_results))

@tool
def count_emails_tool(query: str = "") -> str:
    """Count emails matching a query."""
    return json.dumps(count_emails(query))

@tool
def get_unread_emails_tool(max_results: int = 20) -> str:
    """Get unread emails."""
    return json.dumps(get_unread_emails(max_results))

@tool
def get_emails_from_sender_tool(sender_email: str, max_results: int = 20) -> str:
    """Get emails from a specific sender."""
    return json.dumps(get_emails_from_sender(sender_email, max_results))

@tool
def get_emails_by_date_range_tool(start_date: str, end_date: str, max_results: int = 20) -> str:
    """Get emails within a date range (YYYY-MM-DD)."""
    return json.dumps(get_emails_by_date_range(start_date, end_date, max_results))

@tool
def get_email_body_tool(message_id: str) -> str:
    """Get the full body content of a specific email."""
    return json.dumps(get_email_body(message_id))

@tool
def reply_to_email_tool(message_id: str, reply_body: str) -> str:
    """Reply to a specific email."""
    return json.dumps(reply_to_email(message_id, reply_body))

@tool
def mark_as_read_tool(message_id: str) -> str:
    """Mark an email as read."""
    return json.dumps(mark_as_read(message_id))

@tool
def mark_as_unread_tool(message_id: str) -> str:
    """Mark an email as unread."""
    return json.dumps(mark_as_unread(message_id))

@tool
def delete_email_tool(message_id: str) -> str:
    """Move an email to trash."""
    return json.dumps(delete_email(message_id))

@tool
def get_inbox_stats_tool() -> str:
    """Get inbox statistics."""
    return json.dumps(get_inbox_stats())

@tool
def add_label_to_email_tool(message_id: str, label_id: str) -> str:
    """Add a label to an email."""
    return json.dumps(add_label_to_email(message_id, label_id))

@tool
def get_email_labels_tool() -> str:
    """Get all available Gmail labels."""
    return json.dumps(get_email_labels())

# EXPORT LIST
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
    add_label_to_email_tool,
    get_email_labels_tool
]