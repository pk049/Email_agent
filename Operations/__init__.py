"""
Operations Package
Simple imports for email and file operations
"""

from . import email_operations as email_functions
from . import file_operations as file_functions

# Export the tools lists
from .email_operations import LANGCHAIN_TOOLS as EMAIL_TOOLS
from .file_operations import LANGCHAIN_TOOLS as FILE_TOOLS

# Combined tools list
ALL_TOOLS = EMAIL_TOOLS + FILE_TOOLS


__all__ = [
    'email_functions',
    'file_functions',
    'EMAIL_TOOLS',
    'FILE_TOOLS',
    'ALL_TOOLS'
]