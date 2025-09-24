import os
import aiohttp
import json
import asyncio  # Add this import
from typing import Dict, List, Optional, Any
from datetime import datetime
from google.generativeai import GenerativeModel
import google.generativeai as genai
import base64
from dotenv import load_dotenv
class GPTInsightsService:
    """
    AI Integration service for generating AI-powered SEO and marketing insights
    """
    
    def __init__(self):
        # Read from environment only; no hardcoded default
        load_dotenv()
        self.api_key = os.environ.get('GOOGLE_AI_API_KEY')  
        
        if not self.api_key:
            print("Warning: No Google AI API key found. AI insights will use mock data.")
        else:
            # Configure the Google AI Studio client
            genai.configure(api_key=self.api_key)
            
        # Set the model name
        self.model_name = "gemini-2.0-flash"  # You can change this to other Gemini models as needed
    
    async def generate_seo_insights(self, seo_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered SEO insights and recommendations
        
        Args:
            seo_data: SEO analysis data from SEOAnalyzer
            
        Returns:
            Dictionary containing GPT-generated insights
        """
        
        if not self.api_key:
            return self._generate_mock_seo_insights(seo_data)
        
        # Prepare prompt for GPT
        prompt = self._create_seo_analysis_prompt(seo_data)
        
        try:
            # Call Google AI API
            response = await self._call_ai_api(prompt, max_tokens=1500)
            
            # Parse and structure the response
            insights = self._parse_seo_insights(response)
            
            return {
                "url": seo_data.get("url"),
                "generated_at": datetime.now().isoformat(),
                "insights": insights,
                "recommendations": self._extract_recommendations(response),
                "priority_score": self._calculate_priority_score(seo_data),
                "improvement_areas": self._identify_improvement_areas(seo_data)
            }
            
        except Exception as e:
            print(f"Google AI API error: {str(e)}")
            return self._generate_mock_seo_insights(seo_data)
    
    async def generate_social_insights(self, social_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered social media insights
        
        Args:
            social_data: Social media analysis data
            
        Returns:
            Dictionary containing social media insights
        """
        
        if not self.api_key:
            return self._generate_mock_social_insights(social_data)
        
        prompt = self._create_social_analysis_prompt(social_data)
        
        try:
            response = await self._call_ai_api(prompt, max_tokens=1200)
            
            return {
                "url": social_data.get("url"),
                "platform": social_data.get("platform"),
                "generated_at": datetime.now().isoformat(),
                "insights": self._parse_social_insights(response),
                "content_strategy": self._extract_content_strategy(response),
                "engagement_opportunities": self._identify_engagement_opportunities(social_data),
                "competitive_analysis": self._generate_competitive_suggestions(social_data)
            }
            
        except Exception as e:
            print(f"Google AI API error: {str(e)}")
            return self._generate_mock_social_insights(social_data)
    
    async def generate_comprehensive_report(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate a comprehensive marketing report combining SEO, social media, and branding insights
        
        Args:
            seo_data: SEO analysis results
            social_data: List of social media analysis results
            branding_data: Branding analysis results
            
        Returns:
            Comprehensive marketing insights report
        """
        
        prompt = self._create_comprehensive_report_prompt(seo_data, social_data, branding_data)
        
        try:
            if self.api_key:
                response = await self._call_ai_api(prompt, max_tokens=2000)
                comprehensive_insights = self._parse_comprehensive_insights(response)
            else:
                comprehensive_insights = self._generate_mock_comprehensive_insights(branding_data)
            
            return {
                "generated_at": datetime.now().isoformat(),
                "website_url": seo_data.get("url"),
                "social_profiles_analyzed": len(social_data),
                "executive_summary": comprehensive_insights.get("executive_summary"),
                "key_findings": comprehensive_insights.get("key_findings", []),
                "strategic_recommendations": comprehensive_insights.get("strategic_recommendations", []),
                "priority_actions": comprehensive_insights.get("priority_actions", []),
                "performance_benchmarks": self._generate_benchmarks(seo_data, social_data, branding_data),
                "next_steps": comprehensive_insights.get("next_steps", [])
            }
            
        except Exception as e:
            print(f"Error generating comprehensive report: {str(e)}")
            return self._generate_mock_comprehensive_report(seo_data, social_data, branding_data)
    
    async def _call_ai_api(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call Google AI Studio API with Gemini model"""
        
        try:
            # Create a GenerativeModel instance
            model = GenerativeModel(self.model_name)
            
            # System message to set the context
            system_message = "You are an expert SEO and digital marketing consultant. Provide actionable, data-driven insights and recommendations."
            
            # Generate content
            response = await asyncio.to_thread(
                model.generate_content,
                [system_message, prompt],
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": 0.7
                }
            )
            
            # Extract the text from the response
            return response.text
            
        except Exception as e:
            print(f"Google AI API error: {str(e)}")
            raise Exception(f"Google AI API error: {str(e)}")
    
    def _create_seo_analysis_prompt(self, seo_data: Dict[str, Any]) -> str:
        """Create prompt for SEO analysis"""
        
        # Extract page speed scores
        page_speed_scores = seo_data.get('page_speed_scores', {})
        performance = page_speed_scores.get('performance', 'N/A')
        accessibility = page_speed_scores.get('accessibility', 'N/A')
        best_practices = page_speed_scores.get('best_practices', 'N/A')
        seo_score = page_speed_scores.get('seo', 'N/A')
        overall = page_speed_scores.get('overall', 'N/A')
        return f"""
        Analyze the following SEO data for a website and provide actionable insights:

        Website: {seo_data.get('url')}
        HTTPS: {seo_data.get('https')}
        Title: {seo_data.get('title')}
        Meta Description: {seo_data.get('meta_description')}
        H1 Tags: {seo_data.get('headings', {}).get('h1', [])}
        H2 Tags: {seo_data.get('headings', {}).get('h2', [])}
        Missing Alt Tags: {seo_data.get('alt_tags_missing')}
        
        Page Speed Metrics:
        - Performance: {performance}
        - Accessibility: {accessibility}
        - Best Practices: {best_practices}
        - SEO: {seo_score}
        - Overall: {overall}
        
        Social Links: {seo_data.get('social_links', [])}
        Open Graph Tags: {seo_data.get('og_tags', {})}

        Please provide:
        1. Overall SEO health score (1-100)
        2. Top 3 critical issues that need immediate attention
        3. Top 5 actionable recommendations with expected impact
        4. Content optimization suggestions
        5. Technical SEO improvements needed
        6. Specific recommendations for improving page speed metrics
        
        Format your response as structured insights that can be easily parsed.
        """
    
    def _create_social_analysis_prompt(self, social_data: Dict[str, Any]) -> str:
        """Create prompt for social media analysis"""
        
        profile_data = social_data.get('profile_data', {})
        platform = social_data.get('platform', 'unknown')
        
        return f"""
        Analyze the following social media profile data and provide marketing insights:

        Platform: {platform}
        Profile URL: {social_data.get('url')}
        Name: {profile_data.get('name')}
        Bio: {profile_data.get('bio')}
        Followers: {profile_data.get('follower_count')}
        Following: {profile_data.get('following_count')}
        Verified: {profile_data.get('verification_status')}
        Recent Content Themes: {social_data.get('content_analysis', {}).get('content_themes', [])}
        Hashtags Used: {social_data.get('content_analysis', {}).get('hashtags', [])}

        Please provide:
        1. Profile optimization score (1-100)
        2. Content strategy recommendations
        3. Engagement improvement suggestions
        4. Platform-specific best practices
        5. Growth opportunities
        
        Focus on actionable insights for improving social media presence.
        """
    
    def _create_comprehensive_report_prompt(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> str:
        """Create prompt for comprehensive marketing report with detailed SEO and social data"""
        page_speed_scores = seo_data.get('page_speed_scores', {})
        performance = page_speed_scores.get('performance', 'N/A')
        accessibility = page_speed_scores.get('accessibility', 'N/A')
        best_practices = page_speed_scores.get('best_practices', 'N/A')
        seo_score = page_speed_scores.get('seo', 'N/A')
        overall = page_speed_scores.get('overall', 'N/A')
        print(page_speed_scores)
        # Format social profiles information
        social_profiles = []
        for profile in social_data:
            platform = profile.get('platform', 'unknown')
            url = profile.get('url', 'N/A')
            profile_data = profile.get('profile_data', {})
            content_analysis = profile.get('content_analysis', {})
            
            profile_info = f"\n    - Platform: {platform}\n"
            profile_info += f"      URL: {url}\n"
            profile_info += f"      Name: {profile_data.get('name', 'N/A')}\n"
            profile_info += f"      Bio: {profile_data.get('bio', 'N/A')}\n"
            profile_info += f"      Followers: {profile_data.get('follower_count', 'N/A')}\n"
            profile_info += f"      Following: {profile_data.get('following_count', 'N/A')}\n"
            profile_info += f"      Verified: {profile_data.get('verification_status', 'N/A')}\n"
            profile_info += f"      Content Themes: {content_analysis.get('content_themes', [])}\n"
            profile_info += f"      Hashtags: {content_analysis.get('hashtags', [])}\n"
            profile_info += f"      Engagement Rate: {content_analysis.get('engagement_rate', 'N/A')}\n"
            
            social_profiles.append(profile_info)
        
        # Format headings structure
        headings_structure = ""
        headings = seo_data.get('headings')

        if isinstance(headings, dict):
            for heading_type, heading_list in headings.items():
                if heading_list:
                    headings_structure += f"\n      {heading_type}: {len(heading_list)} headings"
                    for heading in heading_list[:3]:
                        headings_structure += f"\n        - {heading}"
                    if len(heading_list) > 3:
                        headings_structure += f"\n        - ... ({len(heading_list) - 3} more)"
        elif isinstance(headings, list):
            headings_structure += "\n      Headings (list format):"
            for heading in headings[:3]:
                headings_structure += f"\n        - {heading}"
            if len(headings) > 3:
                headings_structure += f"\n        - ... ({len(headings) - 3} more)"
        else:
            headings_structure += "\n      No heading data found."

        # Add branding data if available
        branding_summary = "Not analyzed."
        if branding_data and "branding_analysis" in branding_data:
            branding_summary = branding_data["branding_analysis"].get("executive_summary", "No summary available.")

        # Format schema markup
        schema_markup = ""
        schema_data = seo_data.get('schema_markup')
        if isinstance(schema_data, list):
            schema_markup = "\n      " + "\n      ".join([f"- {schema}" for schema in schema_data])
        elif isinstance(schema_data, dict):
            schema_markup = "\n      " + "\n      ".join([f"- {key}: {value}" for key, value in schema_data.items()])
        elif schema_data:
            schema_markup = f"\n      - {schema_data}"

        # Format Open Graph tags
        og_tags = ""
        og_data = seo_data.get('og_tags')
        if isinstance(og_data, dict):
            og_tags = "\n      " + "\n      ".join([f"- {tag}: {value}" for tag, value in og_data.items() if value])
        elif isinstance(og_data, list):
            og_tags = "\n      " + "\n      ".join([f"- {tag}" for tag in og_data])
        elif og_data:
            og_tags = f"\n      - {og_data}"

        # Format social links
        social_links = ""
        social_links_data = seo_data.get('social_links')
        if isinstance(social_links_data, dict):
            social_links = "\n      " + "\n      ".join([f"- {platform}: {url}" for platform, url in social_links_data.items()])
        elif isinstance(social_links_data, list):
            social_links = "\n      " + "\n      ".join([f"- {link}" for link in social_links_data])
        elif social_links_data:
            social_links = f"\n      - {social_links_data}"

        # Return final prompt
        return f"""
        Create a comprehensive digital marketing analysis report based on the following detailed data:

        WEBSITE SEO DATA:
        - URL: {seo_data.get('url')}
        - Performance: {performance}
        - Accessibility: {accessibility}
        - Best Practices: {best_practices}
        - SEO: {seo_score}
        - Page Speed Score: {overall}        
        - HTTPS Enabled: {seo_data.get('https', False)}
        - Title: {seo_data.get('title', 'N/A')}
        - Title Length: {seo_data.get('title_length', 0)} characters
        - Meta Description: {seo_data.get('meta_description', 'N/A')}
        - Meta Description Length: {seo_data.get('meta_description_length', 0)} characters
        - Canonical URL: {seo_data.get('canonical_url', 'N/A')}
        - Images Count: {seo_data.get('images_count', 0)}
        - Images Missing Alt Tags: {seo_data.get('alt_tags_missing', 0)}
        - Internal Links: {seo_data.get('internal_links', 0)}
        - External Links: {seo_data.get('external_links', 0)}
        - Technical Issues: {self._identify_technical_issues(seo_data)}
        - Content Gaps: (AI should infer this based on headings, etc.)
        - Headings Structure: {headings_structure}
        - Schema Markup: {schema_markup}
        - Open Graph Tags: {og_tags}
        - Social Links on Website: {social_links}

        SOCIAL MEDIA PRESENCE:
        - Platforms: {', '.join([p.get('platform', 'unknown') for p in social_data])}
        - Total Profiles: {len(social_data)}
        - Detailed Profile Information: {''.join(social_profiles)}

        **Branding Analysis Summary**:
        - {branding_summary}

        Please provide a comprehensive marketing report including:
        1.  **Executive Summary**: A high-level overview of the key findings and strategic direction.
        2.  **Key Findings**: Bulleted list of the most important insights from both SEO and social media analysis.
        3.  **Strategic Recommendations**: Prioritized list of strategies based on the analysis.
        4.  **Priority Actions**: Immediate next steps with timeline.
        5.  **Performance Benchmarks**: Quantitative assessment of current performance.
        6.  **Next Steps**: Long-term growth strategy and follow-up actions.
        
        Focus on cross-platform synergies, integrated marketing opportunities, and actionable insights that will improve both SEO performance and social media engagement. Provide specific, data-driven recommendations based on the detailed analysis provided.
        """
        
    def _parse_seo_insights(self, response: str) -> Dict[str, Any]:
        """Parse GPT response for SEO insights"""
        return {
            "summary": response[:200] + "..." if len(response) > 200 else response,
            "full_analysis": response
        }
    
    def _parse_social_insights(self, response: str) -> Dict[str, Any]:
        """Parse GPT response for social insights"""
        return {
            "summary": response[:200] + "..." if len(response) > 200 else response,
            "full_analysis": response
        }
    
    def _parse_comprehensive_insights(self, response: str) -> Dict[str, Any]:
        """Parse comprehensive report response"""
        lines = response.split('\n')
        
        insights = {
            "executive_summary": "",
            "key_findings": [],
            "strategic_recommendations": [],
            "priority_actions": [],
            "next_steps": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "executive summary" in line.lower():
                current_section = "executive_summary"
            elif "key findings" in line.lower():
                current_section = "key_findings"
            elif "strategic recommendations" in line.lower():
                current_section = "strategic_recommendations"
            elif "priority actions" in line.lower():
                current_section = "priority_actions"
            elif "next steps" in line.lower():
                current_section = "next_steps"
            else:
                if current_section and line:
                    if current_section == "executive_summary":
                        insights[current_section] += line + " "
                    else:
                        insights[current_section].append(line)
        
        return insights
    
    def _extract_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from GPT response"""
        recommendations = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*')) or line[0:2].isdigit():
                recommendations.append(line)
        
        return recommendations[:10]  # Limit to top 10
    
    def _calculate_priority_score(self, seo_data: Dict[str, Any]) -> int:
        """Calculate priority score based on SEO issues"""
        score = 100
        
        # Deduct points for various issues
        if not seo_data.get('https'):
            score -= 20
        if not seo_data.get('title'):
            score -= 15
        if not seo_data.get('meta_description'):
            score -= 10
        if seo_data.get('alt_tags_missing', 0) > 5:
            score -= 15
        
        page_speed = seo_data.get('page_speed_score')
        if page_speed and page_speed < 50:
            score -= 20
        elif page_speed and page_speed < 70:
            score -= 10
        
        return max(0, score)
    
    def _calculate_seo_score(self, seo_data: Dict[str, Any]) -> int:
        """Calculate overall SEO score"""
        return self._calculate_priority_score(seo_data)
    
    def _identify_improvement_areas(self, seo_data: Dict[str, Any]) -> List[str]:
        """Identify key improvement areas"""
        areas = []
        
        if not seo_data.get('https'):
            areas.append("HTTPS/SSL Certificate")
        if not seo_data.get('title') or len(seo_data.get('title', '')) < 30:
            areas.append("Title Tag Optimization")
        if not seo_data.get('meta_description'):
            areas.append("Meta Description")
        if seo_data.get('alt_tags_missing', 0) > 0:
            areas.append("Image Alt Tags")
        
        page_speed = seo_data.get('page_speed_score')
        if page_speed and page_speed < 70:
            areas.append("Page Speed Optimization")
        
        if not seo_data.get('social_links'):
            areas.append("Social Media Integration")
        
        return areas
    
    def _identify_technical_issues(self, seo_data: Dict[str, Any]) -> List[str]:
        """Identify technical SEO issues"""
        issues = []
        
        if not seo_data.get('https'):
            issues.append("Missing HTTPS")
        if seo_data.get('alt_tags_missing', 0) > 0:
            issues.append(f"{seo_data.get('alt_tags_missing')} missing alt tags")
        if seo_data.get('page_speed_score', 100) < 60:
            issues.append("Poor page speed performance")
        
        return issues
    
    def _extract_content_strategy(self, response: str) -> List[str]:
        """Extract content strategy suggestions"""
        strategies = []
        lines = response.split('\n')
        
        for line in lines:
            if 'content' in line.lower() and any(word in line.lower() for word in ['strategy', 'recommend', 'suggest']):
                strategies.append(line.strip())
        
        return strategies[:5]
    
    def _identify_engagement_opportunities(self, social_data: Dict[str, Any]) -> List[str]:
        """Identify engagement opportunities"""
        opportunities = []
        
        profile_data = social_data.get('profile_data', {})
        
        if not profile_data.get('bio'):
            opportunities.append("Add compelling bio/description")
        
        if not profile_data.get('verification_status'):
            opportunities.append("Apply for verification badge")
        
        hashtags = social_data.get('content_analysis', {}).get('hashtags', [])
        if len(hashtags) < 5:
            opportunities.append("Increase hashtag usage for better discoverability")
        
        return opportunities
    
    def _generate_competitive_suggestions(self, social_data: Dict[str, Any]) -> List[str]:
        """Generate competitive analysis suggestions"""
        return [
            "Analyze top competitors in your niche",
            "Benchmark posting frequency against industry standards",
            "Study successful content formats in your space",
            "Identify trending hashtags in your industry"
        ]
    
    def _generate_benchmarks(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate performance benchmarks"""
        page_speed_scores = seo_data.get('page_speed_scores', {})
        seo_score = page_speed_scores.get('seo', 'N/A')
        overall = page_speed_scores.get('overall', 'N/A')

        branding_score = "N/A"
        if branding_data and "branding_analysis" in branding_data:
            scores = [item.get("score", 0) for item in branding_data["branding_analysis"].get("scorecard", [])]
            if scores:
                branding_score = f"{sum(scores) / len(scores):.1f}/10"

        return {
            "seo_score": seo_score,
            "page_speed":overall,
            "social_presence": len(social_data),
            "technical_health": "Good" if seo_data.get('https') and seo_data.get('title') else "Needs Improvement",
            "branding_consistency": branding_score
        }
    
    # Mock data generators for when GPT API is not available
    def _generate_mock_seo_insights(self, seo_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock SEO insights when GPT API is unavailable"""
        return {
            "url": seo_data.get("url"),
            "generated_at": datetime.now().isoformat(),
            "insights": {
                "summary": "Mock SEO analysis: Your website shows good fundamental SEO structure with opportunities for improvement in page speed and meta descriptions.",
                "full_analysis": "This is a mock analysis. Connect OpenAI API for detailed insights."
            },
            "recommendations": [
                "Optimize page loading speed for better user experience",
                "Add meta descriptions to improve search engine visibility",
                "Implement proper image alt tags for accessibility",
                "Consider adding structured data markup"
            ],
            "priority_score": self._calculate_priority_score(seo_data),
            "improvement_areas": self._identify_improvement_areas(seo_data)
        }
    
    def _generate_mock_social_insights(self, social_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock social media insights"""
        return {
            "url": social_data.get("url"),
            "platform": social_data.get("platform"),
            "generated_at": datetime.now().isoformat(),
            "insights": {
                "summary": "Mock social analysis: Profile shows potential for increased engagement through consistent posting and community interaction.",
                "full_analysis": "This is a mock analysis. Connect OpenAI API for detailed insights."
            },
            "content_strategy": [
                "Post consistently 3-5 times per week",
                "Use platform-specific hashtags",
                "Engage with your community regularly",
                "Share behind-the-scenes content"
            ],
            "engagement_opportunities": self._identify_engagement_opportunities(social_data),
            "competitive_analysis": self._generate_competitive_suggestions(social_data)
        }
    
    def _generate_mock_comprehensive_insights(self, branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock comprehensive insights"""
        summary = "Your digital presence shows strong potential with opportunities for growth through improved SEO optimization and enhanced social media engagement."
        if branding_data:
            summary += " Branding is a key area for improvement."

        return {
            "executive_summary": summary,
            "key_findings": [
                "Website has solid technical foundation but needs speed optimization",
                "Social media presence exists but could benefit from more consistent posting",
                "Brand messaging is consistent across platforms",
                "There's untapped potential for cross-platform content promotion"
            ],
            "strategic_recommendations": [
                "Implement comprehensive SEO optimization strategy",
                "Develop content calendar for social media consistency",
                "Create integrated marketing campaigns across platforms",
                "Focus on community building and engagement"
            ],
            "priority_actions": [
                "Fix technical SEO issues immediately",
                "Optimize page loading speed",
                "Create weekly content posting schedule",
                "Set up social media monitoring and analytics"
            ],
            "next_steps": [
                "Conduct competitor analysis",
                "Set up tracking and measurement systems",
                "Plan quarterly marketing campaigns",
                "Review and optimize monthly performance"
            ]
        }
    
    def _generate_mock_comprehensive_report(self, seo_data: Dict[str, Any], social_data: List[Dict[str, Any]], branding_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate mock comprehensive report"""
        insights = self._generate_mock_comprehensive_insights(branding_data)
        return {
            "generated_at": datetime.now().isoformat(),
            "website_url": seo_data.get("url"),
            "social_profiles_analyzed": len(social_data),
            **insights,
            "performance_benchmarks": self._generate_benchmarks(seo_data, social_data, branding_data),
        }

    async def generate_branding_insights(self, screenshots: List[Dict[str, Any]], branding_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate AI-powered branding insights from screenshots.
        
        Args:
            screenshots: A list of dictionaries, where each dictionary contains a URL and a base64-encoded screenshot.
            branding_profile: Optional company branding profile with logo and colors for comparison.
            
        Returns:
            A dictionary containing the branding analysis.
        """
        if not self.api_key:
            return self._generate_mock_branding_insights()

        prompt = self._create_branding_analysis_prompt(branding_profile)
        
        try:
            # Create a GenerativeModel instance for multimodal input
            model = genai.GenerativeModel(self.model_name)
            
            # Prepare content with text prompt and images
            content: List[Any] = [prompt]
            for item in screenshots:
                # The API expects bytes, so we decode the base64 string
                image_bytes = base64.b64decode(item["screenshot"])
                content.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": base64.b64encode(image_bytes).decode('utf-8')
                    }
                })

            response = await asyncio.to_thread(
                model.generate_content,
                content,
                generation_config={
                    "max_output_tokens": 2048,
                    "temperature": 0.7
                }
            )
            
            # Parse and structure the response
            insights = self._parse_branding_insights(response.text)
            return insights

        except Exception as e:
            print(f"Google AI API error during branding analysis: {str(e)}")
            return self._generate_mock_branding_insights()

    def _create_branding_analysis_prompt(self, branding_profile: Optional[Dict[str, Any]] = None) -> str:
        """Creates a prompt for the branding analysis LLM."""
        base_prompt = """
        As an expert in branding and visual design, analyze the provided screenshot(s) of a company's web presence (website or social media). 
        
        Provide a comprehensive brand audit based on the visual elements in the image(s). Structure your analysis in JSON format with the following sections:

        1.  **executive_summary**: A concise overview of the brand audit.
        2.  **overall_brand_impression**: 
            -   **strengths**: List of positive aspects (e.g., friendly tone, clear logo).
            -   **room_for_improvement**: List of negative aspects (e.g., lack of cohesion, poor typography).
        3.  **messaging_and_content_style**:
            -   **content**: Analysis of the textual content and messaging style.
            -   **recommendations**: Suggestions for improving messaging.
        4.  **visual_branding_elements**:
            -   **color_palette**:
                -   **analysis**: Describe the color palette used.
                -   **recommendations**: Suggest improvements for the color system.
            -   **typography**:
                -   **analysis**: Analyze the use of fonts, sizes, and readability.
                -   **recommendations**: Suggest improvements for typography.
        5.  **highlights_and_stories** (for social media):
            -   **analysis**: Analyze the use of icons and descriptive labels.
            -   **recommendations**: Suggestions for improvement.
        6.  **grid_strategy** (for social media):
            -   **analysis**: Analyze the layout and flow of the feed.
            -   **recommendations**: Suggestions for improvement.
        7.  **scorecard**:
            -   A list of dictionaries, each with "area" (e.g., "Visual Consistency") and "score" (out of 10).

        Be insightful, professional, and provide actionable recommendations.
        """
        
        # Add branding profile context if available
        if branding_profile:
            profile_context = "\n\nIMPORTANT: The company has provided their official branding profile for comparison:\n"
            
            if branding_profile.get('logo'):
                logo_info = branding_profile['logo']
                profile_context += f"- Company Logo: {logo_info.get('filename', 'Uploaded logo')} ({logo_info.get('size', 'Unknown size')})\n"
            
            if branding_profile.get('colors'):
                colors = branding_profile['colors']
                profile_context += f"- Official Brand Colors:\n"
                profile_context += f"  - Dominant Color: {colors.get('dominant', 'N/A')}\n"
                profile_context += f"  - Color Palette: {', '.join(colors.get('palette', []))}\n"
            
            profile_context += """
            
            When analyzing the screenshots, compare them against this official branding profile:
            - Check if the website/social media uses the official brand colors consistently
            - Verify if the logo appears correctly and matches the official version
            - Assess whether the visual elements align with the established brand identity
            - Provide specific recommendations on how to better align with the official branding
            - Note any inconsistencies between the official brand and what's displayed
            """
            
            return base_prompt + profile_context
        
        return base_prompt

    def _generate_mock_branding_insights(self) -> Dict[str, Any]:
        """
        Generates mock data for branding analysis, structured like the user's example.
        """
        return {
            "executive_summary": "This is a mock executive summary for the brand audit of Seayou Camp. The analysis reveals a friendly and adventure-oriented brand identity, but there are significant inconsistencies in visual branding and content strategy that need to be addressed.",
            "overall_brand_impression": {
                "strengths": [
                    "Friendly, family-oriented logo & tone",
                    "Real moments, community & adventure are well-represented"
                ],
                "room_for_improvement": [
                    "Lack of cohesive color, typography & layout",
                    "Fluctuating visual tone & style across posts",
                    "No clear brand guidelines seem to be followed"
                ]
            },
            "messaging_and_content_style": {
                "content": "The messaging is generally positive and family-friendly, but lacks a consistent tone of voice. There's an opportunity to introduce thematic series to structure content.",
                "recommendations": [
                    "Develop a consistent brand voice (e.g., adventurous, educational, friendly).",
                    "Introduce thematic content series (e.g., 'Tip Tuesday', 'Family Fridays').",
                    "For Arabic typography, ensure text is legible and consistently styled, using text blocks or overlays where necessary."
                ]
            },
            "visual_branding_elements": {
                "color_palette": {
                    "analysis": "Too many uncoordinated colors are used. A clear brand color system is missing.",
                    "recommendations": [
                        "Create a brand color system with 3-5 main colors and 2 accent colors.",
                        "Apply a visual rhythm (e.g., photo, graphic, reel pattern) for consistent post framing."
                    ]
                },
                "typography": {
                    "analysis": "Inconsistent fonts, sizes, and readability across posts.",
                    "recommendations": [
                        "Choose 1-2 primary fonts and standardize hierarchy (headings, body text) across all posts.",
                        "Design branded reel cover templates to use every time for a cohesive look."
                    ]
                }
            },
            "highlights_and_stories": {
                "analysis": "Good use of icons, but they are not consistently branded.",
                "recommendations": [
                    "Use branded designs with descriptive labels for all highlights.",
                    "Rename highlights clearly (e.g., 'Booking' to 'Activities')."
                ]
            },
            "grid_strategy": {
                "analysis": "The feed lacks a clear structure, with a random mix of reels, posts, and graphics.",
                "recommendations": [
                    "Use branded design templates for a more structured and visually appealing feed.",
                    "Plan the grid layout to create a better flow and visual narrative."
                ]
            },
            "scorecard": [
                {"area": "Visual Consistency", "score": 5},
                {"area": "Brand Identity Clarity", "score": 6},
                {"area": "Content Strategy", "score": 7},
                {"area": "Reel Presentation", "score": 5},
                {"area": "User Experience (UX)", "score": 6}
            ]
        }

    def _parse_branding_insights(self, response: str) -> Dict[str, Any]:
        """
        Parses the JSON response from the branding analysis LLM.
        """
        try:
            # The response might be wrapped in markdown JSON
            cleaned_response = response.strip().replace("```json", "").replace("```", "")
            return json.loads(cleaned_response)
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON from branding analysis response.")
            # Fallback to returning the raw text in a structured way
            return {"executive_summary": "Could not parse the analysis.", "raw_response": response}

    async def generate_sentiment_insights(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered insights for sentiment analysis
        
        Args:
            sentiment_data: Dictionary containing sentiment analysis data and summary
            
        Returns:
            Dictionary with AI insights for sentiment analysis
        """
        if not self.api_key:
            return self._generate_mock_sentiment_insights(sentiment_data)
        
        prompt = self._create_sentiment_analysis_prompt(sentiment_data)
        
        try:
            response = await self._call_ai_api(prompt, max_tokens=1000)
            
            return {
                "generated_at": datetime.now().isoformat(),
                "insights": self._parse_sentiment_insights(response),
                "recommendations": self._extract_sentiment_recommendations(response),
                "action_items": self._extract_sentiment_action_items(response)
            }
            
        except Exception as e:
            print(f"Google AI API error: {str(e)}")
            return self._generate_mock_sentiment_insights(sentiment_data)

    def _create_sentiment_analysis_prompt(self, sentiment_data: Dict[str, Any]) -> str:
        """Create prompt for sentiment analysis insights"""
        
        summary = sentiment_data.get("summary", {})
        sample_reviews = sentiment_data.get("sample_reviews", [])
        sentiment_distribution = summary.get("sentiment_percentages", {})
        avg_star_rating = summary.get("average_star_rating", 0)
        
        # Format sample reviews
        reviews_text = ""
        for i, review in enumerate(sample_reviews[:5]):
            reviews_text += f"\n{i+1}. Rating: {review.get('Star Rating', 'N/A')}/5\n"
            reviews_text += f"   Sentiment: {review.get('Sentiment', 'N/A')}\n"
            reviews_text += f"   Text: {review.get('Review Text', 'N/A')[:100]}...\n"
        
        return f"""
        Analyze the following customer sentiment data and provide actionable business insights:

        SENTIMENT SUMMARY:
        - Total Reviews: {summary.get('total_reviews', 0)}
        - Positive: {sentiment_distribution.get('Positive', 0):.1f}%
        - Negative: {sentiment_distribution.get('Negative', 0):.1f}%
        - Neutral: {sentiment_distribution.get('Neutral', 0):.1f}%
        - Average Star Rating: {avg_star_rating:.1f}/5
        - Average Sentiment Polarity: {summary.get('average_polarity', 0):.2f}
        - Average Subjectivity: {summary.get('average_subjectivity', 0):.2f}

        SAMPLE REVIEWS:
        {reviews_text}

        Please provide:
        1. Overall sentiment health score (1-100)
        2. Key insights about customer satisfaction
        3. Top 3 areas for improvement based on negative feedback
        4. Positive aspects to leverage and promote
        5. Specific recommendations for improving customer experience
        6. Action items for addressing common complaints
        7. Strategies for increasing positive sentiment

        Focus on actionable insights that can directly improve business performance and customer satisfaction.
        """

    def _parse_sentiment_insights(self, response: str) -> Dict[str, Any]:
        """Parse GPT response for sentiment insights"""
        return {
            "summary": response[:300] + "..." if len(response) > 300 else response,
            "full_analysis": response
        }

    def _extract_sentiment_recommendations(self, response: str) -> List[str]:
        """Extract recommendations from sentiment analysis response"""
        recommendations = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith(('•', '-', '*')) or line[0:2].isdigit():
                recommendations.append(line)
        
        return recommendations[:8]  # Limit to top 8

    def _extract_sentiment_action_items(self, response: str) -> List[str]:
        """Extract action items from sentiment analysis response"""
        action_items = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            if any(keyword in line.lower() for keyword in ['action', 'implement', 'address', 'fix', 'improve']):
                action_items.append(line)
        
        return action_items[:5]  # Limit to top 5

    def _generate_mock_sentiment_insights(self, sentiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock sentiment insights when GPT API is unavailable"""
        summary = sentiment_data.get("summary", {})
        sentiment_distribution = summary.get("sentiment_percentages", {})
        
        return {
            "generated_at": datetime.now().isoformat(),
            "insights": {
                "summary": f"Mock sentiment analysis: Customer sentiment shows {sentiment_distribution.get('Positive', 0):.1f}% positive feedback with opportunities for improvement in customer experience.",
                "full_analysis": "This is a mock analysis. Connect Google AI API for detailed sentiment insights."
            },
            "recommendations": [
                "Monitor customer feedback regularly to identify trends",
                "Address negative reviews promptly and professionally",
                "Leverage positive reviews for marketing and testimonials",
                "Implement customer satisfaction surveys",
                "Train staff on customer service best practices"
            ],
            "action_items": [
                "Set up automated review monitoring system",
                "Create response templates for common complaints",
                "Develop customer feedback collection process",
                "Implement customer service training program"
            ]
        }