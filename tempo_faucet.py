"""
Tempo Testnet Faucet automation module
"""
import time
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

import config
from metamask_helper import MetaMaskHelper

logger = logging.getLogger(__name__)


class TempoFaucetAutomation:
    """Automates Tempo Testnet faucet interactions."""
    
    def __init__(self, driver: webdriver.Chrome, metamask: MetaMaskHelper):
        self.driver = driver
        self.metamask = metamask
    
    def _wait_and_click(self, by: By, value: str, timeout: int = None, description: str = ""):
        """Wait for element and click it."""
        timeout = timeout or config.ELEMENT_WAIT_TIMEOUT
        wait = WebDriverWait(self.driver, timeout)
        
        element = wait.until(EC.element_to_be_clickable((by, value)))
        element.click()
        
        if description:
            logger.info(f"Clicked: {description}")
        
        return element
    
    def navigate_to_faucet(self) -> bool:
        """Navigate to Tempo faucet page."""
        try:
            self.driver.get(config.TEMPO_FAUCET_URL)
            time.sleep(3)  # Wait for page to fully load
            
            logger.info(f"Navigated to: {config.TEMPO_FAUCET_URL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to faucet: {e}")
            return False
    
    def connect_metamask(self) -> bool:
        """Click MetaMask button and approve connection."""
        try:
            # Find and click the MetaMask connect button
            # Button with MetaMask image and text
            metamask_btn_selectors = [
                '//button[contains(., "MetaMask")]',
                'button:has(img[alt="MetaMask"])',
                '//button[.//img[@alt="MetaMask"]]',
            ]
            
            clicked = False
            for selector in metamask_btn_selectors:
                try:
                    if selector.startswith('//'):
                        self._wait_and_click(
                            By.XPATH, selector, timeout=10,
                            description="MetaMask connect button"
                        )
                    else:
                        self._wait_and_click(
                            By.CSS_SELECTOR, selector, timeout=10,
                            description="MetaMask connect button"
                        )
                    clicked = True
                    break
                except TimeoutException:
                    continue
            
            if not clicked:
                logger.error("Could not find MetaMask connect button")
                return False
            
            time.sleep(2)
            
            # Approve connection in MetaMask popup
            if not self.metamask.connect_to_dapp():
                logger.error("Failed to approve MetaMask connection")
                return False
            
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect MetaMask: {e}")
            return False
    
    def add_tempo_network(self) -> bool:
        """Click 'Add Tempo to MetaMask' and approve network addition."""
        try:
            # Find and click "Add Tempo to MetaMask" button
            add_network_selectors = [
                '//button[contains(., "Add Tempo to MetaMask")]',
                '//button[contains(text(), "Add Tempo")]',
                'button:contains("Add Tempo")',
            ]
            
            clicked = False
            for selector in add_network_selectors:
                try:
                    if selector.startswith('//'):
                        self._wait_and_click(
                            By.XPATH, selector, timeout=10,
                            description="Add Tempo to MetaMask button"
                        )
                    else:
                        self._wait_and_click(
                            By.CSS_SELECTOR, selector, timeout=10,
                            description="Add Tempo to MetaMask button"
                        )
                    clicked = True
                    break
                except TimeoutException:
                    continue
            
            if not clicked:
                logger.warning("Add Tempo network button not found, network might already be added")
                return True
            
            time.sleep(2)
            
            # Approve network addition in MetaMask
            if not self.metamask.approve_add_network():
                logger.error("Failed to approve network addition in MetaMask")
                return False
            
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Failed to add Tempo network: {e}")
            return False
    
    def request_faucet_funds(self) -> bool:
        """Click 'Add funds' button to request test tokens."""
        try:
            # Find and click "Add funds" button
            add_funds_selectors = [
                '//button[contains(., "Add funds")]',
                '//button[contains(text(), "Add funds")]',
                'button:contains("Add funds")',
            ]
            
            clicked = False
            for selector in add_funds_selectors:
                try:
                    if selector.startswith('//'):
                        self._wait_and_click(
                            By.XPATH, selector, timeout=10,
                            description="Add funds button"
                        )
                    else:
                        self._wait_and_click(
                            By.CSS_SELECTOR, selector, timeout=10,
                            description="Add funds button"
                        )
                    clicked = True
                    break
                except TimeoutException:
                    continue
            
            if not clicked:
                logger.error("Could not find Add funds button")
                return False
            
            # Wait for funds to be added (this operation may not require MetaMask confirmation)
            time.sleep(5)
            
            logger.info("Faucet funds requested successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to request faucet funds: {e}")
            return False
    
    def set_fee_token(self) -> bool:
        """Click 'Set fee token' and confirm transaction."""
        try:
            # Find and click "Set fee token" button
            fee_token_selectors = [
                '//button[contains(., "Set fee token")]',
                '//button[contains(text(), "Set fee token")]',
                'button:contains("Set fee token")',
            ]
            
            clicked = False
            for selector in fee_token_selectors:
                try:
                    if selector.startswith('//'):
                        self._wait_and_click(
                            By.XPATH, selector, timeout=10,
                            description="Set fee token button"
                        )
                    else:
                        self._wait_and_click(
                            By.CSS_SELECTOR, selector, timeout=10,
                            description="Set fee token button"
                        )
                    clicked = True
                    break
                except TimeoutException:
                    continue
            
            if not clicked:
                logger.warning("Set fee token button not found, might already be set")
                return True
            
            time.sleep(2)
            
            # Confirm transaction in MetaMask
            if not self.metamask.confirm_transaction():
                logger.error("Failed to confirm fee token transaction")
                return False
            
            time.sleep(3)
            
            logger.info("Fee token set successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to set fee token: {e}")
            return False
    
    def run_full_flow(self) -> bool:
        """
        Run the complete Tempo faucet automation flow.
        
        Steps:
        1. Navigate to faucet page
        2. Connect MetaMask
        3. Add Tempo network
        4. Request faucet funds
        5. Set fee token
        """
        logger.info("Starting Tempo Faucet automation flow")
        
        steps = [
            ("Navigate to faucet", self.navigate_to_faucet),
            ("Connect MetaMask", self.connect_metamask),
            ("Add Tempo network", self.add_tempo_network),
            ("Request faucet funds", self.request_faucet_funds),
            ("Set fee token", self.set_fee_token),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Executing step: {step_name}")
            
            if not step_func():
                logger.error(f"Step failed: {step_name}")
                return False
            
            time.sleep(1)  # Small delay between steps
        
        logger.info("Tempo Faucet automation completed successfully")
        return True
