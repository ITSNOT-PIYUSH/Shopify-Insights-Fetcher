"""
Utility functions for the Shopify Insights Fetcher application.
"""
import re
import validators
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin, urlparse
import logging

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize a URL by ensuring it has a proper scheme.
    
    Args:
        url: The URL to normalize
        
    Returns:
        Normalized URL with proper scheme
    """
    if not url:
        return ""
    
    # Remove leading/trailing whitespace
    url = url.strip()
    
    # Add https:// if no scheme is present
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
    
    return url


def is_valid_url(url: str) -> bool:
    """
    Validate if a URL is properly formatted.
    
    Args:
        url: The URL to validate
        
    Returns:
        True if URL is valid, False otherwise
    """
    try:
        return validators.url(url) is True
    except Exception:
        return False


def is_shopify_store(url: str) -> bool:
    """
    Check if a URL appears to be a Shopify store.
    
    Args:
        url: The URL to check
        
    Returns:
        True if it appears to be a Shopify store, False otherwise
    """
    # Common indicators of Shopify stores
    shopify_indicators = [
        '.myshopify.com',
        'shopifycdn.com',
        'shopify-checkout'
    ]
    
    return any(indicator in url.lower() for indicator in shopify_indicators)


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.
    
    Args:
        url: The URL to extract domain from
        
    Returns:
        Domain name without protocol or path
    """
    try:
        parsed = urlparse(url)
        return parsed.netloc.lower()
    except Exception:
        return ""


def extract_emails(text: str) -> List[str]:
    """
    Extract email addresses from text using regex.
    
    Args:
        text: Text to search for email addresses
        
    Returns:
        List of found email addresses
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text, re.IGNORECASE)
    return list(set(emails))  # Remove duplicates


def extract_phone_numbers(text: str) -> List[str]:
    """
    Extract phone numbers from text using regex.
    
    Args:
        text: Text to search for phone numbers
        
    Returns:
        List of found phone numbers
    """
    # Various phone number patterns
    patterns = [
        r'\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})',  # US format
        r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',     # International
        r'\(\d{3}\)\s*\d{3}[-.\s]?\d{4}',                           # (123) 456-7890
    ]
    
    phones = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            if isinstance(match, tuple):
                phone = ''.join(match)
            else:
                phone = match
            phones.append(phone)
    
    return list(set(phones))  # Remove duplicates


def extract_social_handles(text: str, html_content: str = "") -> Dict[str, List[str]]:
    """
    Extract social media handles and links from text and HTML.
    
    Args:
        text: Text content to search
        html_content: HTML content to search for links
        
    Returns:
        Dictionary with social platform names as keys and handles/URLs as values
    """
    social_handles = {
        'instagram': [],
        'facebook': [],
        'twitter': [],
        'tiktok': [],
        'youtube': [],
        'linkedin': [],
        'pinterest': []
    }
    
    # Social media URL patterns
    patterns = {
        'instagram': [
            r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9._]+)',
            r'@([a-zA-Z0-9._]+).*instagram',
        ],
        'facebook': [
            r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9._]+)',
            r'(?:https?://)?(?:www\.)?fb\.com/([a-zA-Z0-9._]+)',
        ],
        'twitter': [
            r'(?:https?://)?(?:www\.)?twitter\.com/([a-zA-Z0-9._]+)',
            r'(?:https?://)?(?:www\.)?x\.com/([a-zA-Z0-9._]+)',
            r'@([a-zA-Z0-9._]+).*twitter',
        ],
        'tiktok': [
            r'(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9._]+)',
        ],
        'youtube': [
            r'(?:https?://)?(?:www\.)?youtube\.com/(?:channel/|user/|c/)?([a-zA-Z0-9._-]+)',
        ],
        'linkedin': [
            r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company/|in/)?([a-zA-Z0-9._-]+)',
        ],
        'pinterest': [
            r'(?:https?://)?(?:www\.)?pinterest\.com/([a-zA-Z0-9._]+)',
        ]
    }
    
    combined_content = f"{text} {html_content}"
    
    for platform, platform_patterns in patterns.items():
        for pattern in platform_patterns:
            matches = re.findall(pattern, combined_content, re.IGNORECASE)
            for match in matches:
                if match and match not in social_handles[platform]:
                    social_handles[platform].append(match)
    
    # Remove empty lists
    return {k: v for k, v in social_handles.items() if v}


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove common HTML entities that might have been missed
    html_entities = {
        '&nbsp;': ' ',
        '&amp;': '&',
        '&lt;': '<',
        '&gt;': '>',
        '&quot;': '"',
        '&#39;': "'",
    }
    
    for entity, replacement in html_entities.items():
        text = text.replace(entity, replacement)
    
    return text


def get_absolute_url(base_url: str, relative_url: str) -> str:
    """
    Convert a relative URL to an absolute URL.
    
    Args:
        base_url: The base URL
        relative_url: The relative URL to convert
        
    Returns:
        Absolute URL
    """
    try:
        return urljoin(base_url, relative_url)
    except Exception:
        return relative_url


def setup_logging(debug: bool = False) -> None:
    """
    Setup logging configuration with user-friendly format.
    
    Args:
        debug: Enable debug level logging
    """
    level = logging.DEBUG if debug else logging.INFO
    
    # Create a cleaner format for user-facing logs
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Setup handler
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
