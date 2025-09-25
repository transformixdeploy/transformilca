import aiohttp
import ssl
import certifi
from bs4 import BeautifulSoup, Tag
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from helpers import is_social_media_url, extract_domain
from instagram_analyzer import InstagramAnalyzer

class SocialAnalyzer:
    """
    Analyzer for social media URLs and profiles
    """
    
    # Add this import at the top
    
    # Then in your SocialAnalyzer class, add this property
    def __init__(self):
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Initialize Instagram analyzer
        self.instagram_analyzer = InstagramAnalyzer()
    
    # Then modify your analyze_social_url method to use the Instagram analyzer for Instagram URLs
    async def analyze_social_url(self, url: str) -> Dict[str, Any]:
        """
        Analyze a social media URL
        
        Args:
            url: Social media URL to analyze
            
        Returns:
            Dictionary containing social media analysis results
        """
        
        if not is_social_media_url(url):
            return {
                "error": "URL is not from a recognized social media platform",
                "url": url,
                "is_social": False
            }
        
        platform = self._identify_platform(url)
        
        # Use Instagram analyzer for Instagram URLs
        if platform == "Instagram":
            try:
                # Extract username from URL
                parsed_url = urlparse(url)
                path_parts = parsed_url.path.strip('/').split('/')
                if path_parts:
                    username = path_parts[0]  # First part of the path should be the username
                    
                    # Use Instagram analyzer
                    instagram_data = await self.instagram_analyzer.analyze_profile(username)
                    
                    if instagram_data.get("success", False):
                        # Determine analysis method used
                        method = instagram_data.get("method", "unknown")
                        note = instagram_data.get("note", "")
                        
                        # Combine basic data with detailed Instagram data
                        result = {
                            "url": url,
                            "platform": platform,
                            "is_social": True,
                            "title": f"Instagram: {instagram_data.get('full_name', username)}",
                            "description": instagram_data.get("biography"),
                            "profile_data": {
                                "name": instagram_data.get("full_name"),
                                "bio": instagram_data.get("biography"),
                                "follower_count": instagram_data.get("followers"),
                                "following_count": instagram_data.get("following"),
                                "verification_status": instagram_data.get("is_verified"),
                                "external_url": instagram_data.get("external_url"),
                                "is_private": instagram_data.get("is_private")
                            },
                            "content_analysis": {
                                "content_themes": list(instagram_data.get("content_analysis", {}).get("top_hashtags", {}).keys()),
                                "hashtags": list(instagram_data.get("content_analysis", {}).get("top_hashtags", {}).keys()),
                                "engagement_rate": instagram_data.get("engagement", {}).get("engagement_rate"),
                                "avg_likes": instagram_data.get("engagement", {}).get("avg_likes"),
                                "avg_comments": instagram_data.get("engagement", {}).get("avg_comments")
                            },
                            "accessibility": not instagram_data.get("is_private", False),
                            "detailed_data": instagram_data,  # Include all the detailed data
                            "analysis_method": method,
                            "analysis_note": note
                        }
                        
                        # Add method-specific information
                        if method == "public_scraping":
                            result["limitations"] = [
                                "Limited data available due to Instagram's restrictions",
                                "No post-level engagement metrics",
                                "No detailed content analysis",
                                "For full analysis, Instagram authentication is required"
                            ]
                        elif method == "authenticated":
                            result["limitations"] = []
                        
                        return result
                    else:
                        # Instagram analysis failed, return error information
                        error_msg = instagram_data.get("error", "Unknown error occurred")
                        return {
                            "url": url,
                            "platform": platform,
                            "is_social": True,
                            "error": f"Instagram analysis failed: {error_msg}",
                            "profile_data": {},
                            "content_analysis": {},
                            "accessibility": False,
                            "analysis_method": "failed",
                            "limitations": [
                                "Unable to access Instagram profile data",
                                "Profile may be private or Instagram may be blocking requests",
                                "Try again later or check if the username is correct"
                            ]
                        }
                        
            except Exception as e:
                # Fall back to basic analysis if Instagram analyzer fails
                print(f"Instagram analyzer failed: {str(e)}. Falling back to basic analysis.")
                # Continue with basic analysis below
        
        # Basic analysis for other platforms or if Instagram analyzer failed
        try:
            # Fetch basic information
            html_content = await self._fetch_html(url)
            soup = BeautifulSoup(html_content, 'html.parser')
            
            analysis_results = {
                "url": url,
                "platform": platform,
                "is_social": True,
                "title": self._extract_title(soup),
                "description": self._extract_description(soup),
                "og_tags": self._extract_og_tags(soup),
                "profile_info": self._extract_profile_info(soup, platform),
                "accessibility": self._check_accessibility(url)
            }
            
            return analysis_results
            
        except Exception as e:
            return {
                "url": url,
                "platform": platform,
                "is_social": True,
                "error": f"Failed to analyze: {str(e)}",
                "accessible": False
            }
    
    def _identify_platform(self, url: str) -> str:
        """Identify the social media platform from URL"""
        domain = extract_domain(url).lower()
        
        platform_map = {
            'facebook.com': 'Facebook',
            'twitter.com': 'Twitter',
            'x.com': 'X (Twitter)',
            'instagram.com': 'Instagram',
            'linkedin.com': 'LinkedIn',
            'youtube.com': 'YouTube',
            'tiktok.com': 'TikTok',
            'pinterest.com': 'Pinterest',
            'snapchat.com': 'Snapchat',
            'threads.net': 'Threads'
        }
        
        for platform_domain, platform_name in platform_map.items():
            if platform_domain in domain:
                return platform_name
        
        return 'Unknown'
    
    async def _fetch_html(self, url: str) -> str:
        """Fetch HTML content from social media URL"""
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        
        async with aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers,
            connector=aiohttp.TCPConnector(ssl=ssl_context)
        ) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: Unable to fetch URL")
                
                return await response.text()
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract page title from social media page"""
        title_tag = soup.find('title')
        return title_tag.get_text().strip() if title_tag else None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract description from social media page"""
        # Try meta description first
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and isinstance(meta_desc, Tag):
            content = meta_desc.get('content', '')
            return str(content).strip() if content else None
        
        # Try OG description
        og_desc = soup.find('meta', property='og:description')
        if og_desc and isinstance(og_desc, Tag):
            content = og_desc.get('content', '')
            return str(content).strip() if content else None
        
        return None
    
    def _extract_og_tags(self, soup: BeautifulSoup) -> Dict[str, Optional[str]]:
        """Extract Open Graph tags from social media page"""
        og_tags = {}
        
        og_properties = [
            'og:title', 'og:description', 'og:image', 'og:url', 
            'og:type', 'og:site_name'
        ]
        
        for prop in og_properties:
            og_tag = soup.find('meta', property=prop)
            og_tags[prop] = og_tag.get('content') if og_tag and isinstance(og_tag, Tag) else None
        
        return og_tags
    
    def _extract_profile_info(self, soup: BeautifulSoup, platform: str) -> Dict[str, Any]:
        """Extract platform-specific profile information"""
        profile_info = {"platform": platform}
        
        # This is a basic implementation
        # In a real-world scenario, you'd need platform-specific parsing
        # due to dynamic content loading and anti-scraping measures
        
        if platform.lower() in ['twitter', 'x (twitter)']:
            # Twitter/X specific extraction would go here
            profile_info["type"] = "twitter_profile"
        elif platform.lower() == 'linkedin':
            # LinkedIn specific extraction would go here
            profile_info["type"] = "linkedin_profile"
        elif platform.lower() == 'instagram':
            # Instagram specific extraction would go here
            profile_info["type"] = "instagram_profile"
        
        return profile_info
    
    def _check_accessibility(self, url: str) -> bool:
        """Check if the social media URL is publicly accessible"""
        # This is a simplified check
        # In practice, you might want to check for login requirements, etc.
        return True