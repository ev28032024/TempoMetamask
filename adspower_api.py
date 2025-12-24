"""
AdsPower API wrapper for browser profile management with Playwright
"""
import time
import logging
import requests
from typing import Optional, Tuple

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

import config

logger = logging.getLogger(__name__)


class AdsPowerAPI:
    """API wrapper for AdsPower browser management with Playwright."""
    
    def __init__(self, api_url: str = None, api_key: str = None):
        self.api_url = (api_url or config.ADSPOWER_API_URL).rstrip('/')
        self.api_key = api_key or config.ADSPOWER_API_KEY
        self._session = requests.Session()
        self._playwright = None
        self._browser = None
    
    def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make API request to AdsPower."""
        url = f"{self.api_url}{endpoint}"
        
        if params is None:
            params = {}
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        try:
            response = self._session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('code') != 0:
                raise Exception(f"AdsPower API error: {data.get('msg', 'Unknown error')}")
            
            return data.get('data', {})
            
        except requests.RequestException as e:
            logger.error(f"AdsPower API request failed: {e}")
            raise
    
    def check_connection(self) -> bool:
        """Check if AdsPower is running and accessible."""
        try:
            self._make_request('/status')
            return True
        except Exception as e:
            logger.error(f"AdsPower connection check failed: {e}")
            return False
    
    def get_profiles(self, page: int = 1, page_size: int = 100) -> list[dict]:
        """Get list of browser profiles."""
        data = self._make_request('/api/v1/user/list', {
            'page': page,
            'page_size': page_size
        })
        return data.get('list', [])
    
    def get_profile_by_serial_number(self, serial_number: int, max_retries: int = 3) -> Optional[dict]:
        """Get profile by its serial number with retry logic."""
        for attempt in range(max_retries):
            try:
                data = self._make_request('/api/v1/user/list', {
                    'serial_number': str(serial_number)
                })
                profiles = data.get('list', [])
                
                if profiles:
                    return profiles[0]
                
                return None
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to get profile {serial_number}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise
        
        return None
    
    def open_browser(self, user_id: str, headless: bool = False) -> dict:
        """
        Open browser for specified profile.
        
        Returns dict with:
            - ws: WebSocket connection info
            - webdriver: path to chromedriver
        """
        params = {
            'user_id': user_id,
            'open_tabs': 1
        }
        
        if headless:
            params['headless'] = 1
        
        data = self._make_request('/api/v1/browser/start', params)
        
        logger.info(f"Browser opened for user_id: {user_id}")
        return data
    
    def close_browser(self, user_id: str) -> bool:
        """Close browser for specified profile."""
        try:
            self._make_request('/api/v1/browser/stop', {'user_id': user_id})
            logger.info(f"Browser closed for user_id: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to close browser for user_id {user_id}: {e}")
            return False
    
    def check_browser_status(self, user_id: str) -> dict:
        """Check if browser is running for specified profile."""
        try:
            data = self._make_request('/api/v1/browser/active', {'user_id': user_id})
            return data
        except Exception:
            return {'status': 'Inactive'}
    
    def get_playwright_browser(self, browser_data: dict) -> Tuple[BrowserContext, Page]:
        """
        Create Playwright connection from AdsPower browser data.
        
        Args:
            browser_data: Response from open_browser() method
            
        Returns:
            Tuple of (BrowserContext, Page)
        """
        ws_info = browser_data.get('ws', {})
        puppeteer_ws = ws_info.get('puppeteer')
        
        if not puppeteer_ws:
            raise ValueError("No puppeteer websocket address in browser data")
        
        # Start Playwright and connect via CDP
        self._playwright = sync_playwright().start()
        
        # Connect to existing browser via CDP endpoint
        self._browser = self._playwright.chromium.connect_over_cdp(puppeteer_ws)
        
        # Get default context and page
        context = self._browser.contexts[0] if self._browser.contexts else self._browser.new_context()
        page = context.pages[0] if context.pages else context.new_page()
        
        logger.info(f"Playwright connected to: {puppeteer_ws}")
        return context, page
    
    def cleanup(self):
        """Cleanup Playwright resources."""
        try:
            if self._browser:
                # Don't close browser - AdsPower manages it
                self._browser = None
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")


def get_adspower_api() -> AdsPowerAPI:
    """Factory function to get configured AdsPower API instance."""
    return AdsPowerAPI()
