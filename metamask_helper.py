"""
MetaMask browser extension interaction helpers
"""
import time
import logging
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchWindowException

import config

logger = logging.getLogger(__name__)

# MetaMask extension URL patterns
METAMASK_POPUP_PATTERN = "chrome-extension://"
METAMASK_NOTIFICATION_PATTERN = "notification.html"


class MetaMaskHelper:
    """Helper class for MetaMask browser extension interactions."""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.main_window = driver.current_window_handle
        self._original_window = None
    
    def _wait_for_element(self, by: By, value: str, timeout: int = None, clickable: bool = False):
        """Wait for element to be present or clickable."""
        timeout = timeout or config.ELEMENT_WAIT_TIMEOUT
        wait = WebDriverWait(self.driver, timeout)
        
        if clickable:
            return wait.until(EC.element_to_be_clickable((by, value)))
        return wait.until(EC.presence_of_element_located((by, value)))
    
    def _switch_to_metamask_popup(self, timeout: int = 15) -> bool:
        """
        Switch to MetaMask popup/notification window.
        
        Returns True if switched successfully, False otherwise.
        """
        self._original_window = self.driver.current_window_handle
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                windows = self.driver.window_handles
                
                for window in windows:
                    if window == self._original_window:
                        continue
                    
                    self.driver.switch_to.window(window)
                    current_url = self.driver.current_url
                    
                    if METAMASK_POPUP_PATTERN in current_url:
                        logger.info(f"Switched to MetaMask popup: {current_url}")
                        time.sleep(0.5)  # Wait for popup to fully load
                        return True
                
            except NoSuchWindowException:
                pass
            
            time.sleep(0.5)
        
        logger.warning("MetaMask popup not found")
        return False
    
    def _switch_back_to_main(self):
        """Switch back to main/original window."""
        if self._original_window:
            try:
                self.driver.switch_to.window(self._original_window)
                logger.debug("Switched back to original window")
            except NoSuchWindowException:
                # Try to switch to first available window
                windows = self.driver.window_handles
                if windows:
                    self.driver.switch_to.window(windows[0])
    
    def unlock_metamask(self, password: str, timeout: int = 20) -> bool:
        """
        Unlock MetaMask with password.
        
        This navigates to MetaMask extension popup and enters the password.
        """
        try:
            # Try to find password field if MetaMask is locked
            password_input = self._wait_for_element(
                By.CSS_SELECTOR,
                'input[data-testid="unlock-password"]',
                timeout=timeout
            )
            
            password_input.clear()
            password_input.send_keys(password)
            
            # Click unlock button
            unlock_btn = self._wait_for_element(
                By.CSS_SELECTOR,
                'button[data-testid="unlock-submit"]',
                clickable=True
            )
            unlock_btn.click()
            
            # Wait for unlock to complete
            time.sleep(2)
            
            logger.info("MetaMask unlocked successfully")
            return True
            
        except TimeoutException:
            logger.info("MetaMask appears to be already unlocked")
            return True
        except Exception as e:
            logger.error(f"Failed to unlock MetaMask: {e}")
            return False
    
    def connect_to_dapp(self, timeout: int = 30) -> bool:
        """
        Approve MetaMask connection request from dApp.
        
        Handles the 'Connect' popup that appears when a site requests wallet connection.
        """
        try:
            if not self._switch_to_metamask_popup(timeout=timeout):
                return False
            
            # Wait for popup content to load
            time.sleep(1)
            
            # Look for Connect/Next button - different versions have different texts
            connect_selectors = [
                'button[data-testid="page-container-footer-next"]',
                'button[data-testid="confirm-btn"]',
                'button.btn-primary',
                '//button[contains(text(), "Далее")]',
                '//button[contains(text(), "Next")]',
                '//button[contains(text(), "Подключить")]',
                '//button[contains(text(), "Connect")]',
            ]
            
            for selector in connect_selectors:
                try:
                    if selector.startswith('//'):
                        btn = self._wait_for_element(By.XPATH, selector, timeout=3, clickable=True)
                    else:
                        btn = self._wait_for_element(By.CSS_SELECTOR, selector, timeout=3, clickable=True)
                    
                    btn.click()
                    logger.info(f"Clicked connect button: {selector}")
                    time.sleep(1)
                    break
                except TimeoutException:
                    continue
            
            # Some flows require a second confirmation
            time.sleep(1)
            for selector in connect_selectors:
                try:
                    if selector.startswith('//'):
                        btn = self._wait_for_element(By.XPATH, selector, timeout=3, clickable=True)
                    else:
                        btn = self._wait_for_element(By.CSS_SELECTOR, selector, timeout=3, clickable=True)
                    
                    btn.click()
                    logger.info(f"Clicked second confirmation: {selector}")
                    break
                except TimeoutException:
                    continue
            
            time.sleep(1)
            self._switch_back_to_main()
            
            logger.info("Successfully connected to dApp")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to dApp: {e}")
            self._switch_back_to_main()
            return False
    
    def approve_add_network(self, timeout: int = 30) -> bool:
        """
        Approve adding a new network to MetaMask.
        
        Handles 'Approve' and 'Switch network' buttons.
        """
        try:
            if not self._switch_to_metamask_popup(timeout=timeout):
                return False
            
            time.sleep(1)
            
            # Click Approve button
            approve_selectors = [
                'button[data-testid="confirmation-submit-button"]',
                'button.btn-primary',
                '//button[contains(text(), "Одобрить")]',
                '//button[contains(text(), "Approve")]',
            ]
            
            for selector in approve_selectors:
                try:
                    if selector.startswith('//'):
                        btn = self._wait_for_element(By.XPATH, selector, timeout=5, clickable=True)
                    else:
                        btn = self._wait_for_element(By.CSS_SELECTOR, selector, timeout=5, clickable=True)
                    
                    btn.click()
                    logger.info(f"Clicked approve network button: {selector}")
                    time.sleep(2)
                    break
                except TimeoutException:
                    continue
            
            # Click Switch network if prompted
            switch_selectors = [
                'button[data-testid="confirmation-submit-button"]',
                '//button[contains(text(), "Переключить")]',
                '//button[contains(text(), "Switch")]',
            ]
            
            for selector in switch_selectors:
                try:
                    if selector.startswith('//'):
                        btn = self._wait_for_element(By.XPATH, selector, timeout=5, clickable=True)
                    else:
                        btn = self._wait_for_element(By.CSS_SELECTOR, selector, timeout=5, clickable=True)
                    
                    btn.click()
                    logger.info(f"Clicked switch network button: {selector}")
                    break
                except TimeoutException:
                    continue
            
            time.sleep(1)
            self._switch_back_to_main()
            
            logger.info("Successfully approved network addition")
            return True
            
        except Exception as e:
            logger.error(f"Failed to approve add network: {e}")
            self._switch_back_to_main()
            return False
    
    def confirm_transaction(self, timeout: int = 60) -> bool:
        """
        Confirm a transaction in MetaMask popup.
        
        Handles the standard transaction confirmation flow.
        """
        try:
            if not self._switch_to_metamask_popup(timeout=timeout):
                return False
            
            time.sleep(1)
            
            # Click Confirm button
            confirm_selectors = [
                'button[data-testid="confirm-footer-button"]',
                'button[data-testid="page-container-footer-next"]',
                'button[data-testid="confirmation-submit-button"]',
                'button.btn-primary',
                '//button[contains(text(), "Подтвердить")]',
                '//button[contains(text(), "Confirm")]',
            ]
            
            for selector in confirm_selectors:
                try:
                    if selector.startswith('//'):
                        btn = self._wait_for_element(By.XPATH, selector, timeout=5, clickable=True)
                    else:
                        btn = self._wait_for_element(By.CSS_SELECTOR, selector, timeout=5, clickable=True)
                    
                    btn.click()
                    logger.info(f"Clicked confirm transaction button: {selector}")
                    break
                except TimeoutException:
                    continue
            
            time.sleep(2)
            self._switch_back_to_main()
            
            logger.info("Transaction confirmed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to confirm transaction: {e}")
            self._switch_back_to_main()
            return False
    
    def reject_all_pending(self):
        """Reject all pending MetaMask popups (cleanup)."""
        try:
            windows = self.driver.window_handles
            current = self.driver.current_window_handle
            
            for window in windows:
                if window == current:
                    continue
                
                self.driver.switch_to.window(window)
                if METAMASK_POPUP_PATTERN in self.driver.current_url:
                    try:
                        reject_btn = self._wait_for_element(
                            By.CSS_SELECTOR,
                            'button[data-testid="page-container-footer-cancel"]',
                            timeout=2,
                            clickable=True
                        )
                        reject_btn.click()
                        logger.info("Rejected pending MetaMask request")
                    except TimeoutException:
                        pass
            
            self.driver.switch_to.window(current)
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")
