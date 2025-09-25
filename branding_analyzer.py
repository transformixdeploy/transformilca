from gpt_insights_service import GPTInsightsService
import base64
import asyncio
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from selenium.webdriver.common.keys import Keys

class BrandingAnalyzer:
    """
    Analyzer for brand visual elements using screenshots and LLM analysis.
    """
    
    def __init__(self):
        self.gpt_insights = GPTInsightsService()

    def take_screenshot(self, url: str) -> bytes:
        """Takes a screenshot of a given URL using Selenium."""
        try:
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Run in headless mode
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--allow-running-insecure-content")
            
            # Create driver with automatic ChromeDriver management
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                # Navigate to URL
                driver.get(url)
                
                # Wait for page to load completely
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Additional wait for popup to appear
                time.sleep(3)

                # If on Instagram, try to close the login popup
                if "instagram.com" in url.lower():
                    try:
                        # Updated selector for the close button
                        close_button_selector = "svg[aria-label='Close']"
                        close_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, close_button_selector))
                        )
                        print("Found Instagram login popup close button. Clicking...")
                        close_button.click()
                        print("Successfully closed Instagram login popup.")
                        time.sleep(2)  # Wait for popup to close and page to re-render
                    except Exception:
                        print("Could not find or click the Instagram login popup close button. Trying with Escape key.")
                        try:
                            # Fallback: try pressing the escape key
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            print("Attempted to close popup with Escape key.")
                            time.sleep(2) # wait for close
                        except Exception:
                             print("Failed to close popup with Escape key. Proceeding with screenshot.")

                # Scroll to ensure all content is loaded
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2) # Wait for lazy-loaded content
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
                
                # Take a full-page screenshot using Chrome DevTools Protocol
                page_rect = driver.execute_cdp_cmd('Page.getLayoutMetrics', {})
                screenshot_config = {
                    'captureBeyondViewport': True,
                    'format': 'png',
                    'clip': {
                        'width': page_rect['contentSize']['width'],
                        'height': page_rect['contentSize']['height'],
                        'x': 0,
                        'y': 0,
                        'scale': 1
                    }
                }
                result = driver.execute_cdp_cmd('Page.captureScreenshot', screenshot_config)
                screenshot_bytes = base64.b64decode(result['data'])
                
                # Check if screenshot is mostly black (simple check)
                if len(screenshot_bytes) < 1000:  # Very small file might be black
                    print(f"Warning: Screenshot for {url} seems too small ({len(screenshot_bytes)} bytes)")
                
                return screenshot_bytes
                
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"Error taking screenshot of {url}: {str(e)}")
            # Return a minimal mock image as fallback
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01\x00\x9a\x9c\x18\x00\x00\x00\x07tIME\x07\xe6\x06\x16\x0e\x1c\x0c\xc8\xc8\xc8\x00\x00\x00\x0cIDATx\x9cc```\x00\x00\x00\x04\x00\x01\xf5\xf7\xd0\xc4\x00\x00\x00\x00IEND\xaeB`\x82'

    async def analyze_branding(self, urls: list[str], branding_profile=None):
        """
        Analyze branding for a list of URLs.
        
        Args:
            urls: List of URLs to analyze
            branding_profile: Optional company branding profile with logo and colors
            
        Returns:
            Dictionary containing branding analysis results
        """
        screenshots = []
        for url in urls:
            try:
                # Take screenshot using Selenium
                screenshot_bytes = self.take_screenshot(url)
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                screenshots.append({
                    "url": url,
                    "screenshot": screenshot_base64
                })
            except Exception as e:
                print(f"Failed to process {url}: {str(e)}")
                continue
        
        if not screenshots:
            return {"error": "Failed to capture any screenshots"}
        
        # Generate branding insights using the GPT service
        branding_analysis = await self.gpt_insights.generate_branding_insights(screenshots, branding_profile)
        
        return {
            "urls_analyzed": [s["url"] for s in screenshots],
            "screenshots": screenshots,  # Include screenshots for debugging
            "branding_analysis": branding_analysis,
            "company_branding_profile": branding_profile  # Include the company profile for reference
        }