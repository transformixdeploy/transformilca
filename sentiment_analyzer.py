import time
import logging
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.wheel_input import ScrollOrigin
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, List, Optional, Any, Union
import os
# Ensure Transformers does not import TensorFlow/Keras
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
import asyncio
import aiohttp
import json
import re
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys

# Add the current directory to the path so we can import the modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gpt_insights_service import GPTInsightsService
from competitor_search_service import CompetitorSearchService

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class SentimentAnalyzer:
    """
    Sentiment analysis service for analyzing reviews and comments
    """
    
    def __init__(self):
        self.gpt_service = GPTInsightsService()
        self.competitor_search = CompetitorSearchService()
        # Initialize Hugging Face multilingual sentiment pipeline
        try:
            import torch  # Prefer PyTorch to avoid TensorFlow/Keras dependency issues
            model_name = 'tabularisai/multilingual-sentiment-analysis'
            tokenizer = AutoTokenizer.from_pretrained(model_name)
            model = AutoModelForSequenceClassification.from_pretrained(model_name)
            device = 0 if hasattr(torch, 'cuda') and torch.cuda.is_available() else -1
            self.sentiment_pipeline = pipeline(
                task="text-classification",
                model=model,
                tokenizer=tokenizer,
                device=device
            )
        except Exception as error:
            logging.error(f"Failed to initialize HF sentiment pipeline: {error}")
            self.sentiment_pipeline = None
    
    def setup_browser(self):
        """Initialize and return the Chrome WebDriver in headless mode for servers."""
        from selenium.webdriver.chrome.service import Service
        
        edge_options = Options()
        # Headless mode for servers
        try:
            edge_options.add_argument("--headless=new")
        except Exception:
            edge_options.add_argument("--headless")
        
        # Stability flags
        edge_options.add_argument("--disable-gpu")
        edge_options.add_argument("--no-sandbox")
        edge_options.add_argument("--disable-dev-shm-usage")
        edge_options.add_argument("--disable-software-rasterizer")
        edge_options.add_argument("--disable-blink-features=AutomationControlled")
        edge_options.add_argument("--lang=en-US")
        edge_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        edge_options.add_experimental_option("useAutomationExtension", False)
        
        # Add window size for better visibility
        edge_options.add_argument("--window-size=1920,1080")
        # Do not force start-maximized in headless
        
        try:
            # Try to use the local chromedriver.exe from the project folder
            driver_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chromedriver.exe")
            
            if os.path.exists(driver_path):
                service = Service(executable_path=driver_path)
                return webdriver.Chrome(service=service, options=edge_options)
            else:
                logging.warning(f"Local driver not found at {driver_path}, trying system Chrome driver...")
                return webdriver.Chrome(options=edge_options)
                
        except Exception as e:
            logging.error(f"Error with local driver: {e}")
            logging.info("Falling back to system Chrome driver...")
            try:
                return webdriver.Chrome(options=edge_options)
            except Exception as fallback_error:
                logging.error(f"System driver also failed: {fallback_error}")
                raise Exception(f"Could not initialize Chrome WebDriver. Please ensure Chrome and chromedriver are properly installed. Local driver error: {e}, System driver error: {fallback_error}")

    def expand_review_if_needed(self, browser, review):
        """
        Clicks 'عرض المزيد' inside a single review if present.
        Works even if the button is partially overlapped.
        """
        # Try by class (fast)
        btns = review.find_elements(By.CSS_SELECTOR, 'button.w8nwRe.kyuRq[aria-expanded="false"]')
        # Fallbacks by Arabic label/text (in case classes change)
        if not btns:
            btns = review.find_elements(By.XPATH,
                './/button[contains(@aria-label,"عرض المزيد") or normalize-space(.)="المزيد" or contains(normalize-space(.),"عرض المزيد")]'
            )
        for btn in btns:
            try:
                # wait until it is interactable, then JS-click to avoid intercepted click
                WebDriverWait(browser, 2).until(EC.element_to_be_clickable(btn))
                browser.execute_script("arguments[0].click();", btn)
                WebDriverWait(browser, 2).until(
                    lambda d: btn.get_attribute("aria-expanded") == "true" or not btn.is_displayed()
                )
                break
            except Exception:
                continue

    def _scrape_single_google_reviews(self, url: str, scroll_limit: int = 1000) -> pd.DataFrame:
        """Scrape reviews from a single Google Maps URL."""
        print(f"[DEBUG] _scrape_single_google_reviews starting for URL: {url}")
        print(f"[DEBUG] Scroll limit set to: {scroll_limit}")
        browser = self.setup_browser()
        print(f"[DEBUG] Browser setup complete, navigating to URL...")
        browser.get(url)
        print(f"[DEBUG] Page loaded, waiting 10 seconds...")
        time.sleep(10)

        try:
            action = ActionChains(browser)
            
            # Debug: Check page title and current URL
            print(f"[DEBUG] Current page title: {browser.title}")
            print(f"[DEBUG] Current URL after navigation: {browser.current_url}")
            
            # Try to find reviews tab with multiple selectors
            reviews_tab = None
            tab_selectors = [
                'button[data-tab-index="1"]',
                'button[data-value="Reviews"]',
                'button[aria-label*="Reviews"]',
                'button[aria-label*="مراجعات"]',  # Arabic for reviews
                'div[role="tablist"] button:nth-child(2)',
                'button:contains("Reviews")',
                'button:contains("مراجعات")'
            ]
            
            for selector in tab_selectors:
                try:
                    reviews_tab = browser.find_element(By.CSS_SELECTOR, selector)
                    print(f"[DEBUG] Reviews tab found using selector: {selector}")
                    break
                except Exception as e:
                    print(f"[DEBUG] Reviews tab not found with selector '{selector}': {str(e)}")
                    continue
            
            if reviews_tab is None:
                print(f"[DEBUG] ERROR: Could not find reviews tab with any selector")
                print(f"[DEBUG] Available buttons on page:")
                buttons = browser.find_elements(By.TAG_NAME, "button")
                for i, btn in enumerate(buttons[:10]):  # Show first 10 buttons
                    try:
                        btn_text = btn.text.strip()
                        btn_aria = btn.get_attribute("aria-label")
                        print(f"[DEBUG] Button {i}: text='{btn_text}', aria-label='{btn_aria}'")
                    except:
                        pass
                return pd.DataFrame()
            
            print(f"[DEBUG] Reviews tab found, clicking...")
            reviews_tab.click()
            time.sleep(5)
            
            # Debug: Check page content after clicking reviews tab
            print(f"[DEBUG] Page URL after reviews tab click: {browser.current_url}")
            
            # Try multiple selectors for review container and reviews
            review_selectors = [
                'div.jftiEf.fontBodyMedium',
                'div[data-review-id]',
                'div[jsaction*="review"]',
                'div.review',
                'div[role="article"]',
                'div.jftiEf',
                'div[data-hveid]'
            ]
            
            reviews = []
            for selector in review_selectors:
                try:
                    reviews = browser.find_elements(By.CSS_SELECTOR, selector)
                    if reviews:
                        print(f"[DEBUG] Found {len(reviews)} reviews using selector: {selector}")
                        break
                except Exception as e:
                    print(f"[DEBUG] No reviews found with selector '{selector}': {str(e)}")
                    continue
            
            if not reviews:
                print(f"[DEBUG] ERROR: No reviews found with any selector")
                print(f"[DEBUG] Page source snippet (first 1000 chars):")
                page_source = browser.page_source[:1000]
                print(page_source)
                return pd.DataFrame()
            
            print(f"[DEBUG] Initial reviews found: {len(reviews)}")

            attempts = 0
            print(f"[DEBUG] Starting scroll loop with {len(reviews)} initial reviews, limit: {scroll_limit}")
            while len(reviews) < scroll_limit:
                last_review = reviews[-1] if reviews else None
                if last_review:
                    print(f"[DEBUG] Scrolling from last review element...")
                    scroll_origin = ScrollOrigin.from_element(last_review)
                    action.scroll_from_origin(scroll_origin, 0, 1000).perform()
                    time.sleep(2)

                # Try multiple selectors for new reviews after scrolling
                new_reviews = []
                for selector in review_selectors:
                    try:
                        new_reviews = browser.find_elements(By.CSS_SELECTOR, selector)
                        if new_reviews:
                            print(f"[DEBUG] After scroll, found {len(new_reviews)} reviews using selector: {selector}")
                            break
                    except Exception as e:
                        continue
                
                if len(new_reviews) == len(reviews):
                    attempts += 1
                    print(f"[DEBUG] No new reviews found after scroll, attempt {attempts}/20")
                    if attempts >= 20:
                        print(f"[DEBUG] Reached max scroll attempts, breaking")
                        break
                else:
                    attempts = 0
                    print(f"[DEBUG] Found {len(new_reviews)} total reviews (was {len(reviews)})")
                    reviews = new_reviews

            records = []
            print(f"[DEBUG] Processing {len(reviews)} review elements...")
            for i, review in enumerate(reviews):
                try:
                    print(f"[DEBUG] Processing review {i+1}/{len(reviews)}")
                    
                    # Try multiple selectors for name
                    name = "Unknown"
                    name_selectors = ['div.d4r55', 'div[data-attrid="title"]', 'div.TSUbDb', 'span.X43Kjb']
                    for selector in name_selectors:
                        try:
                            name_elem = review.find_element(By.CSS_SELECTOR, selector)
                            name = name_elem.text.strip()
                            if name:
                                break
                        except:
                            continue
                    
                    # Try multiple selectors for review count
                    reviews_count = "N/A"
                    count_selectors = ['div.RfnDt', 'span.RfnDt', 'div[data-attrid="reviewCount"]']
                    for selector in count_selectors:
                        try:
                            count_elem = review.find_element(By.CSS_SELECTOR, selector)
                            reviews_count = count_elem.text.strip()
                            if reviews_count:
                                break
                        except:
                            continue
                    
                    # Try multiple selectors for stars
                    stars = "No Rating"
                    star_selectors = ['span.kvMYJc', 'div[role="img"]', 'span[aria-label*="star"]']
                    for selector in star_selectors:
                        try:
                            star_elem = review.find_element(By.CSS_SELECTOR, selector)
                            stars = star_elem.get_attribute('aria-label') or star_elem.text
                            if stars:
                                break
                        except:
                            continue
                    
                    self.expand_review_if_needed(browser, review)
                    
                    # Try multiple selectors for review text
                    review_text = "No Review Text"
                    text_selectors = ['span.wiI7pd', 'div[data-attrid="description"]', 'div.MyEned', 'div.review-text']
                    for selector in text_selectors:
                        try:
                            text_elem = review.find_element(By.CSS_SELECTOR, selector)
                            review_text = text_elem.text.strip()
                            if review_text:
                                break
                        except:
                            continue
                    
                    print(f"[DEBUG] Review {i+1} - Name: '{name}', Stars: '{stars}', Text length: {len(review_text)}")
                    
                    # Skip records without actual review content
                    if review_text and review_text.strip() and review_text.lower() != "no review text":
                        records.append((name, reviews_count, stars, review_text, url))
                        print(f"[DEBUG] Added review {i+1} to records")
                    else:
                        print(f"[DEBUG] Skipped review {i+1} - no valid text content")
                        
                except Exception as e:
                    print(f"[DEBUG] Error processing review {i+1}: {str(e)}")
                    continue

            print(f"[DEBUG] Scraping completed for {url}. Total reviews scraped: {len(records)}")
            return pd.DataFrame(records, columns=['Name', 'Reviews Count', 'Stars', 'Review Text', 'Source URL'])

        except Exception as error:
            print(f"[DEBUG] Error occurred while scraping {url}: {error}")
            logging.error(f"Error scraping {url}: {error}")
            return pd.DataFrame()
        finally:
            try:
                browser.quit()
            except Exception:
                pass

    def scrape_google_reviews(self, urls: Union[str, List[str]], scroll_limit: int = 1000) -> pd.DataFrame:
        """Scrape reviews from one or more Google Maps URLs."""
        url_list: List[str] = [urls] if isinstance(urls, str) else list(urls or [])
        print(f"[DEBUG] scrape_google_reviews called with {len(url_list)} URL(s)")
        print(f"[DEBUG] URLs to process: {url_list}")
        print(f"[DEBUG] Scroll limit: {scroll_limit}")
        
        if not url_list:
            print("[DEBUG] No URLs provided, returning empty DataFrame")
            return pd.DataFrame(columns=['Name', 'Reviews Count', 'Stars', 'Review Text', 'Source URL'])

        dataframes: List[pd.DataFrame] = []
        for i, single_url in enumerate(url_list):
            if single_url and isinstance(single_url, str):
                print(f"[DEBUG] Processing URL {i+1}/{len(url_list)}: {single_url}")
                df_single = self._scrape_single_google_reviews(single_url, scroll_limit=scroll_limit)
                if not df_single.empty:
                    dataframes.append(df_single)

        if not dataframes:
            return pd.DataFrame(columns=['Name', 'Reviews Count', 'Stars', 'Review Text', 'Source URL'])

        return pd.concat(dataframes, ignore_index=True)

    def analyze_sentiment_textblob(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment using Hugging Face multilingual model.
        """
        try:
            if not text or not text.strip():
                return {
                    "sentiment": "Neutral",
                    "polarity": 0.0,
                    "subjectivity": 0.0,
                    "confidence": 0.0
                }

            if self.sentiment_pipeline is None:
                raise RuntimeError("HF sentiment pipeline is not initialized")

            result = self.sentiment_pipeline(text, truncation=True)
            # pipeline returns list for batched calls; for single string it's a dict or list depending on version
            if isinstance(result, list):
                result = result[0]

            label = result.get('label', '')
            score = float(result.get('score', 0.0))

            # Model may return: Very Negative, Negative, Neutral, Positive, Very Positive
            label_lower = str(label).strip().lower()
            if 'very negative' in label_lower:
                stars_value = 1
            elif label_lower == 'negative':
                stars_value = 2
            elif label_lower == 'neutral':
                stars_value = 3
            elif label_lower == 'positive':
                stars_value = 4
            elif 'very positive' in label_lower:
                stars_value = 5
            else:
                # Fallback: try to parse possible numeric/star labels; else neutral
                match = re.search(r"(\d)", str(label))
                stars_value = int(match.group(1)) if match else 3

            if stars_value >= 4:
                sentiment_label = "Positive"
            elif stars_value <= 2:
                sentiment_label = "Negative"
            else:
                sentiment_label = "Neutral"

            # Map 1..5 stars to -1..1 polarity
            polarity = (stars_value - 3) / 2.0

            return {
                "sentiment": sentiment_label,
                "polarity": polarity,
                "subjectivity": 0.5,
                "confidence": score
            }
        except Exception as error:
            logging.error(f"Error analyzing sentiment: {error}")
            return {
                "sentiment": "Neutral",
                "polarity": 0.0,
                "subjectivity": 0.0,
                "confidence": 0.0
            }

    def analyze_sentiment_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a batch of texts
        
        Args:
            texts: List of texts to analyze
            
        Returns:
            List of sentiment analysis results
        """
        results = []
        for text in texts:
            if text and text.strip():
                result = self.analyze_sentiment_textblob(text)
                results.append(result)
            else:
                results.append({
                    "sentiment": "Neutral",
                    "polarity": 0.0,
                    "subjectivity": 0.0,
                    "confidence": 0.0
                })
        return results

    def extract_star_rating(self, stars_text: str) -> int:
        """
        Extract numeric star rating from text
        
        Args:
            stars_text: Text containing star rating
            
        Returns:
            Numeric star rating (1-5)
        """
        try:
            # Extract number from text like "5 stars" or "5.0 stars"
            match = re.search(r'(\d+(?:\.\d+)?)', stars_text)
            if match:
                return int(float(match.group(1)))
            return 3  # Default to neutral if can't parse
        except:
            return 3

    def process_reviews_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Process reviews dataframe and add sentiment analysis
        
        Args:
            df: DataFrame with reviews data
            
        Returns:
            DataFrame with added sentiment analysis columns
        """
        if df.empty:
            return df
        
        # Add sentiment analysis
        sentiment_results = self.analyze_sentiment_batch(df['Review Text'].tolist())
        
        # Add sentiment columns
        df['Sentiment'] = [result['sentiment'] for result in sentiment_results]
        df['Polarity'] = [result['polarity'] for result in sentiment_results]
        df['Subjectivity'] = [result['subjectivity'] for result in sentiment_results]
        df['Confidence'] = [result['confidence'] for result in sentiment_results]
        
        # Extract numeric star ratings
        df['Star Rating'] = df['Stars'].apply(self.extract_star_rating)
        
        # Add timestamp
        df['Analysis Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return df

    def generate_sentiment_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics for sentiment analysis
        
        Args:
            df: DataFrame with sentiment analysis results
            
        Returns:
            Dictionary with summary statistics
        """
        if df.empty:
            return {}
        
        total_reviews = len(df)
        sentiment_counts = df['Sentiment'].value_counts()
        
        # Calculate percentages
        sentiment_percentages = {}
        for sentiment in ['Positive', 'Negative', 'Neutral']:
            count = sentiment_counts.get(sentiment, 0)
            sentiment_percentages[sentiment] = (count / total_reviews) * 100
        
        # Calculate average metrics
        avg_polarity = df['Polarity'].mean()
        avg_subjectivity = df['Subjectivity'].mean()
        avg_confidence = df['Confidence'].mean()
        avg_star_rating = df['Star Rating'].mean()
        
        return {
            "total_reviews": total_reviews,
            "sentiment_counts": sentiment_counts.to_dict(),
            "sentiment_percentages": sentiment_percentages,
            "average_polarity": avg_polarity,
            "average_subjectivity": avg_subjectivity,
            "average_confidence": avg_confidence,
            "average_star_rating": avg_star_rating,
            "analysis_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    async def generate_ai_insights(self, df: pd.DataFrame, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI-powered insights for sentiment analysis
        
        Args:
            df: DataFrame with sentiment analysis results
            summary: Summary statistics
            
        Returns:
            Dictionary with AI insights
        """
        try:
            # Prepare data for AI analysis
            analysis_data = {
                "summary": summary,
                "sample_reviews": df.head(10)[['Review Text', 'Sentiment', 'Star Rating']].to_dict('records'),
                "sentiment_distribution": summary.get("sentiment_percentages", {}),
                "average_star_rating": summary.get("average_star_rating", 0)
            }
            
            # Generate insights using GPT service
            insights = await self.gpt_service.generate_sentiment_insights(analysis_data)
            return insights
            
        except Exception as e:
            logging.error(f"Error generating AI insights: {e}")
            return {
                "error": str(e),
                "insights": "Unable to generate AI insights at this time."
            }

    def create_sentiment_visualizations(self, df: pd.DataFrame, summary: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create visualizations for sentiment analysis
        
        Args:
            df: DataFrame with sentiment analysis results
            summary: Summary statistics
            
        Returns:
            Dictionary with plotly figures
        """
        figures = {}
        
        try:
            # Sentiment distribution pie chart
            sentiment_counts = summary.get("sentiment_counts", {})
            if sentiment_counts:
                fig_pie = px.pie(
                    values=list(sentiment_counts.values()),
                    names=list(sentiment_counts.keys()),
                    title="Sentiment Distribution",
                    color_discrete_map={
                        'Positive': '#2E8B57',
                        'Negative': '#DC143C',
                        'Neutral': '#FFA500'
                    }
                )
                figures["sentiment_distribution"] = fig_pie
            
            # Polarity distribution histogram
            if not df.empty:
                fig_hist = px.histogram(
                    df,
                    x='Polarity',
                    title="Sentiment Polarity Distribution",
                    nbins=20,
                    color_discrete_sequence=['#1E88E5']
                )
                fig_hist.update_layout(xaxis_title="Polarity Score", yaxis_title="Number of Reviews")
                figures["polarity_distribution"] = fig_hist
            
            # Star rating vs sentiment scatter plot
            if not df.empty:
                fig_scatter = px.scatter(
                    df,
                    x='Star Rating',
                    y='Polarity',
                    color='Sentiment',
                    title="Star Rating vs Sentiment Polarity",
                    color_discrete_map={
                        'Positive': '#2E8B57',
                        'Negative': '#DC143C',
                        'Neutral': '#FFA500'
                    }
                )
                fig_scatter.update_layout(xaxis_title="Star Rating", yaxis_title="Sentiment Polarity")
                figures["rating_vs_sentiment"] = fig_scatter
            
            # Subjectivity distribution
            if not df.empty:
                fig_subjectivity = px.box(
                    df,
                    y='Subjectivity',
                    title="Review Subjectivity Distribution",
                    color_discrete_sequence=['#FF6B6B']
                )
                fig_subjectivity.update_layout(yaxis_title="Subjectivity Score")
                figures["subjectivity_distribution"] = fig_subjectivity
            
        except Exception as e:
            logging.error(f"Error creating visualizations: {e}")
            figures["error"] = str(e)
        
        return figures
    
    async def analyze_competitors_sentiment(self, industry: str, region: str, max_competitors: int = 10, reviews_per_competitor: int = 50) -> Dict[str, Any]:
        """
        Analyze sentiment for competitors in a specific industry and region
        
        Args:
            industry: The industry to search for (e.g., "diving", "restaurants")
            region: The region to search in (e.g., "Saudi Arabia", "Riyadh")
            max_competitors: Maximum number of competitors to analyze
            reviews_per_competitor: Number of reviews to scrape per competitor
            
        Returns:
            Dictionary containing competitor analysis results
        """
        try:
            # Search for competitors
            competitors = await self.competitor_search.search_and_get_reviews_urls(
                industry, region, max_competitors
            )
            
            if not competitors:
                return {
                    "error": "No competitors found",
                    "competitors": [],
                    "analysis_results": {}
                }
            
            # Analyze each competitor
            competitor_results = []
            all_reviews = []
            
            for competitor in competitors:
                try:
                    # Scrape reviews for this competitor
                    reviews_url = competitor.get("reviews_url")
                    if reviews_url:
                        print(f"[DEBUG] Full Analysis Mode - Processing competitor: {competitor.get('name', 'Unknown')}")
                        print(f"[DEBUG] Full Analysis Mode - Reviews URL: {reviews_url}")
                        print(f"[DEBUG] Full Analysis Mode - Reviews per competitor limit: {reviews_per_competitor}")
                        df = self.scrape_google_reviews(reviews_url, reviews_per_competitor)
                        
                        if not df.empty:
                            # Process reviews with sentiment analysis
                            df_processed = self.process_reviews_dataframe(df)
                            
                            # Generate summary for this competitor
                            summary = self.generate_sentiment_summary(df_processed)
                            
                            # Generate per-competitor AI insights based on labeled reviews
                            try:
                                competitor_ai_input = {
                                    "summary": {
                                        "total_reviews": summary.get("total_reviews", 0),
                                        "sentiment_percentages": summary.get("sentiment_percentages", {}),
                                        "average_polarity": summary.get("average_polarity", 0),
                                        "average_subjectivity": summary.get("average_subjectivity", 0),
                                        "average_star_rating": summary.get("average_star_rating", 0)
                                    },
                                    # Provide a representative sample of labeled reviews
                                    "sample_reviews": df_processed.head(15)[["Review Text", "Sentiment", "Star Rating"]].to_dict("records"),
                                    "competitor": {
                                        "name": competitor.get("name", "Unknown"),
                                        "rating": competitor.get("rating", 0),
                                        "review_count": competitor.get("review_count", 0)
                                    }
                                }
                                competitor_ai_insights = await self.gpt_service.generate_sentiment_insights(competitor_ai_input)
                            except Exception as _:
                                competitor_ai_insights = {"insights": {"summary": "AI insights unavailable.", "full_analysis": ""}}
                            
                            # Add competitor info to the results
                            competitor_result = {
                                "competitor_info": competitor,
                                "reviews_data": df_processed,
                                "sentiment_summary": summary,
                                "total_reviews_analyzed": len(df_processed),
                                "ai_insights": competitor_ai_insights
                            }
                            
                            competitor_results.append(competitor_result)
                            
                            # Add to combined dataset
                            df_processed["competitor_name"] = competitor["name"]
                            df_processed["competitor_rating"] = competitor["rating"]
                            all_reviews.append(df_processed)
                            
                except Exception as e:
                    logging.warning(f"Error analyzing competitor {competitor.get('name', 'Unknown')}: {str(e)}")
                    continue
            
            # Combine all reviews for overall analysis
            combined_analysis = {}
            if all_reviews:
                combined_df = pd.concat(all_reviews, ignore_index=True)
                combined_summary = self.generate_sentiment_summary(combined_df)
                combined_analysis = {
                    "combined_summary": combined_summary,
                    "combined_data": combined_df,
                    "total_competitors_analyzed": len(competitor_results),
                    "total_reviews_analyzed": len(combined_df)
                }
            
            # Generate AI insights for the industry analysis
            ai_insights = await self.generate_competitor_insights(competitor_results, combined_analysis, industry, region)
            
            return {
                "industry": industry,
                "region": region,
                "competitors": competitors,
                "competitor_results": competitor_results,
                "combined_analysis": combined_analysis,
                "ai_insights": ai_insights,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error in competitor sentiment analysis: {str(e)}")
            return {
                "error": str(e),
                "competitors": [],
                "analysis_results": {}
            }
    
    async def generate_competitor_insights(self, competitor_results: List[Dict[str, Any]], combined_analysis: Dict[str, Any], industry: str, region: str) -> Dict[str, Any]:
        """
        Generate AI-powered insights for competitor analysis
        
        Args:
            competitor_results: List of competitor analysis results
            combined_analysis: Combined analysis across all competitors
            industry: The industry being analyzed
            region: The region being analyzed
            
        Returns:
            Dictionary containing AI insights
        """
        try:
            # Prepare data for AI analysis
            insights_data = {
                "industry": industry,
                "region": region,
                "competitor_count": len(competitor_results),
                "combined_summary": combined_analysis.get("combined_summary", {}),
                "competitor_summaries": []
            }
            
            # Add individual competitor summaries
            for result in competitor_results:
                competitor_info = result["competitor_info"]
                summary = result["sentiment_summary"]
                
                insights_data["competitor_summaries"].append({
                    "name": competitor_info["name"],
                    "rating": competitor_info["rating"],
                    "review_count": competitor_info["review_count"],
                    "sentiment_percentages": summary.get("sentiment_percentages", {}),
                    "average_rating": summary.get("average_star_rating", 0),
                    "total_reviews_analyzed": result["total_reviews_analyzed"]
                })
            
            # Generate insights using GPT service
            prompt = self._create_competitor_analysis_prompt(insights_data)
            
            if self.gpt_service.api_key:
                response = await self.gpt_service._call_ai_api(prompt, max_tokens=1500)
                insights = self._parse_competitor_insights(response)
            else:
                insights = self._generate_mock_competitor_insights(insights_data)
            
            return insights
            
        except Exception as e:
            logging.error(f"Error generating competitor insights: {str(e)}")
            return {"error": str(e)}
    
    def _create_competitor_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Create prompt for competitor sentiment analysis"""
        
        industry = data["industry"]
        region = data["region"]
        competitor_count = data["competitor_count"]
        combined_summary = data["combined_summary"]
        
        # Format competitor data
        competitor_data = ""
        for comp in data["competitor_summaries"]:
            sentiment_pct = comp["sentiment_percentages"]
            competitor_data += f"\n- {comp['name']}: {comp['rating']}/5 stars, {comp['total_reviews_analyzed']} reviews analyzed\n"
            competitor_data += f"  Sentiment: {sentiment_pct.get('Positive', 0):.1f}% positive, {sentiment_pct.get('Negative', 0):.1f}% negative, {sentiment_pct.get('Neutral', 0):.1f}% neutral\n"
        
        return f"""
        Analyze the following competitor sentiment data for the {industry} industry in {region}:

        INDUSTRY OVERVIEW:
        - Industry: {industry}
        - Region: {region}
        - Competitors Analyzed: {competitor_count}
        - Total Reviews Analyzed: {combined_summary.get('total_reviews', 0)}

        OVERALL SENTIMENT DISTRIBUTION:
        - Positive: {combined_summary.get('sentiment_percentages', {}).get('Positive', 0):.1f}%
        - Negative: {combined_summary.get('sentiment_percentages', {}).get('Negative', 0):.1f}%
        - Neutral: {combined_summary.get('sentiment_percentages', {}).get('Neutral', 0):.1f}%
        - Average Star Rating: {combined_summary.get('average_star_rating', 0):.1f}/5

        COMPETITOR BREAKDOWN:
        {competitor_data}

        Please provide:
        1. **Industry Sentiment Health Score** (1-100) for the {industry} industry in {region}
        2. **Key Insights** about customer satisfaction trends in this industry
        3. **Top 3 Competitors** with the best sentiment scores and why they're successful
        4. **Common Pain Points** identified across competitors from negative reviews
        5. **Market Opportunities** based on sentiment gaps
        6. **Strategic Recommendations** for businesses in this industry
        7. **Customer Experience Priorities** that should be addressed
        8. **Competitive Advantages** that successful companies have

        Focus on actionable insights that can help businesses improve their customer experience and competitive positioning in the {industry} industry.
        """
    
    def _parse_competitor_insights(self, response: str) -> Dict[str, Any]:
        """Parse competitor analysis insights from AI response"""
        return {
            "summary": response[:300] + "..." if len(response) > 300 else response,
            "full_analysis": response,
            "generated_at": datetime.now().isoformat()
        }
    
    def _generate_mock_competitor_insights(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock competitor insights when AI is unavailable"""
        industry = data["industry"]
        region = data["region"]
        
        return {
            "summary": f"Mock analysis: The {industry} industry in {region} shows mixed customer sentiment with opportunities for improvement in customer experience.",
            "full_analysis": f"This is a mock competitor analysis for the {industry} industry in {region}. Connect Google AI API for detailed insights about market sentiment trends and competitive positioning.",
            "generated_at": datetime.now().isoformat()
        }
    
    def create_competitor_visualizations(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create visualizations for competitor sentiment analysis
        
        Args:
            analysis_results: Results from competitor sentiment analysis
            
        Returns:
            Dictionary with plotly figures
        """
        figures = {}
        
        try:
            competitor_results = analysis_results.get("competitor_results", [])
            combined_analysis = analysis_results.get("combined_analysis", {})
            
            if not competitor_results:
                return {"error": "No competitor data available for visualization"}
            
            # 1. Competitor Sentiment Comparison Bar Chart
            competitor_names = []
            positive_percentages = []
            negative_percentages = []
            neutral_percentages = []
            
            for result in competitor_results:
                competitor_names.append(result["competitor_info"]["name"])
                sentiment_pct = result["sentiment_summary"].get("sentiment_percentages", {})
                positive_percentages.append(sentiment_pct.get("Positive", 0))
                negative_percentages.append(sentiment_pct.get("Negative", 0))
                neutral_percentages.append(sentiment_pct.get("Neutral", 0))
            
            # Create stacked bar chart
            fig_comparison = go.Figure()
            fig_comparison.add_trace(go.Bar(name='Positive', x=competitor_names, y=positive_percentages, marker_color='#2E8B57'))
            fig_comparison.add_trace(go.Bar(name='Neutral', x=competitor_names, y=neutral_percentages, marker_color='#FFA500'))
            fig_comparison.add_trace(go.Bar(name='Negative', x=competitor_names, y=negative_percentages, marker_color='#DC143C'))
            
            fig_comparison.update_layout(
                title="Competitor Sentiment Comparison",
                xaxis_title="Competitors",
                yaxis_title="Percentage (%)",
                barmode='stack',
                height=500
            )
            figures["competitor_sentiment_comparison"] = fig_comparison
            
            # 2. Competitor Rating vs Sentiment Scatter Plot
            ratings = [result["competitor_info"]["rating"] for result in competitor_results]
            avg_sentiment = [result["sentiment_summary"].get("average_polarity", 0) for result in competitor_results]
            
            fig_scatter = px.scatter(
                x=ratings,
                y=avg_sentiment,
                text=competitor_names,
                title="Competitor Rating vs Average Sentiment",
                labels={'x': 'Google Rating', 'y': 'Average Sentiment Polarity'},
                color=ratings,
                color_continuous_scale='RdYlGn'
            )
            fig_scatter.update_traces(textposition="top center")
            figures["rating_vs_sentiment"] = fig_scatter
            
            # 3. Overall Industry Sentiment Distribution
            if combined_analysis.get("combined_summary"):
                combined_summary = combined_analysis["combined_summary"]
                sentiment_counts = combined_summary.get("sentiment_counts", {})
                
                if sentiment_counts:
                    fig_pie = px.pie(
                        values=list(sentiment_counts.values()),
                        names=list(sentiment_counts.keys()),
                        title=f"Overall {analysis_results.get('industry', 'Industry')} Sentiment Distribution",
                        color_discrete_map={
                            'Positive': '#2E8B57',
                            'Negative': '#DC143C',
                            'Neutral': '#FFA500'
                        }
                    )
                    figures["industry_sentiment_distribution"] = fig_pie
            
            # 4. Reviews Count by Competitor
            review_counts = [result["total_reviews_analyzed"] for result in competitor_results]
            
            fig_reviews = px.bar(
                x=competitor_names,
                y=review_counts,
                title="Number of Reviews Analyzed per Competitor",
                labels={'x': 'Competitors', 'y': 'Number of Reviews'},
                color=review_counts,
                color_continuous_scale='Blues'
            )
            figures["reviews_count"] = fig_reviews
            
        except Exception as e:
            logging.error(f"Error creating competitor visualizations: {e}")
            figures["error"] = str(e)
        
        return figures
