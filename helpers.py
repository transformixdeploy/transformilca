import re
from urllib.parse import urlparse
from typing import List, Optional

def is_valid_url(url: str) -> bool:
    """Check if a URL is valid"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
    except ValueError:
        return False

def validate_url(url: str) -> str:
    """Validate and normalize URL"""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url

def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    parsed_url = urlparse(url)
    return parsed_url.netloc

def is_social_media_url(url: str) -> bool:
    """Check if URL is from a social media platform"""
    social_domains = [
        'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
        'youtube.com', 'pinterest.com', 'tiktok.com', 'snapchat.com',
        'reddit.com', 'tumblr.com', 'quora.com', 'medium.com'
    ]
    
    domain = extract_domain(url)
    
    for social_domain in social_domains:
        if social_domain in domain:
            return True
    
    return False

def extract_username_from_url(url: str, platform: str) -> Optional[str]:
    """Extract username from social media URL"""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    
    if platform == "Instagram" and len(path_parts) > 0:
        return path_parts[0]
    elif platform == "Twitter" and len(path_parts) > 0:
        return path_parts[0]
    elif platform == "Facebook" and len(path_parts) > 0:
        return path_parts[0]
    elif platform == "LinkedIn" and len(path_parts) > 1 and path_parts[0] == "in":
        return path_parts[1]
    
    return None

def clean_text(text: str) -> str:
    """Clean text by removing extra whitespace and special characters"""
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()