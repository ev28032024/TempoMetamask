"""
OnChainGM transaction automation module
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


class GMTransactionAutomation:
    """Automates GM transaction on onchaingm.com for Tempo Testnet."""
    
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
    
    def _scroll_to_element(self, element):
        """Scroll element into view."""
        self.driver.execute_script(
            "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
            element
        )
        time.sleep(0.5)
    
    def navigate_to_onchaingm(self) -> bool:
        """Navigate to onchaingm.com."""
        try:
            self.driver.get(config.ONCHAINGM_URL)
            time.sleep(3)  # Wait for page to fully load
            
            logger.info(f"Navigated to: {config.ONCHAINGM_URL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to onchaingm: {e}")
            return False
    
    def find_tempo_card(self) -> bool:
        """Find and scroll to Tempo Testnet card."""
        try:
            wait = WebDriverWait(self.driver, config.ELEMENT_WAIT_TIMEOUT)
            
            # Find Tempo Testnet card by network ID or name
            card_selectors = [
                f'[data-network-id="{config.TEMPO_NETWORK_ID}"]',
                f'//div[contains(@class, "card") and .//h3[contains(text(), "{config.TEMPO_NETWORK_NAME}")]]',
                f'//*[contains(text(), "{config.TEMPO_NETWORK_NAME}")]//ancestor::div[contains(@class, "card")]',
            ]
            
            card = None
            for selector in card_selectors:
                try:
                    if selector.startswith('//') or selector.startswith('//*'):
                        card = wait.until(
                            EC.presence_of_element_located((By.XPATH, selector))
                        )
                    else:
                        card = wait.until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                    break
                except TimeoutException:
                    continue
            
            if card:
                self._scroll_to_element(card)
                logger.info("Found Tempo Testnet card")
                return True
            
            logger.error("Tempo Testnet card not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to find Tempo card: {e}")
            return False
    
    def click_connect_button(self) -> bool:
        """Click Connect button on Tempo card."""
        try:
            # Find Connect button within Tempo card context
            connect_selectors = [
                f'[data-network-id="{config.TEMPO_NETWORK_ID}"] button',
                f'//div[@data-network-id="{config.TEMPO_NETWORK_ID}"]//button[contains(., "Connect")]',
                f'//*[contains(text(), "{config.TEMPO_NETWORK_NAME}")]//ancestor::div[contains(@class, "card")]//button',
            ]
            
            clicked = False
            for selector in connect_selectors:
                try:
                    if selector.startswith('//') or selector.startswith('//*'):
                        self._wait_and_click(
                            By.XPATH, selector, timeout=10,
                            description="Tempo Connect button"
                        )
                    else:
                        self._wait_and_click(
                            By.CSS_SELECTOR, selector, timeout=10,
                            description="Tempo Connect button"
                        )
                    clicked = True
                    break
                except TimeoutException:
                    continue
            
            if not clicked:
                logger.error("Could not find Connect button on Tempo card")
                return False
            
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Failed to click Connect button: {e}")
            return False
    
    def select_metamask_wallet(self) -> bool:
        """Select MetaMask from wallet selection modal."""
        try:
            # Wait for wallet selection modal
            time.sleep(1)
            
            # Find and click MetaMask option
            metamask_wallet_selectors = [
                '[data-testid="rk-wallet-option-io.metamask"]',
                '//button[contains(., "MetaMask")]',
                '//div[contains(@class, "wallet")]//button[.//span[contains(text(), "MetaMask")]]',
                '//button[.//img[@alt="MetaMask"] or .//div[text()="MetaMask"]]',
            ]
            
            clicked = False
            for selector in metamask_wallet_selectors:
                try:
                    if selector.startswith('//'):
                        self._wait_and_click(
                            By.XPATH, selector, timeout=10,
                            description="MetaMask wallet option"
                        )
                    else:
                        self._wait_and_click(
                            By.CSS_SELECTOR, selector, timeout=10,
                            description="MetaMask wallet option"
                        )
                    clicked = True
                    break
                except TimeoutException:
                    continue
            
            if not clicked:
                logger.error("Could not find MetaMask wallet option")
                return False
            
            time.sleep(2)
            
            # Approve connection in MetaMask popup
            if not self.metamask.connect_to_dapp():
                logger.error("Failed to approve MetaMask connection")
                return False
            
            time.sleep(2)
            return True
            
        except Exception as e:
            logger.error(f"Failed to select MetaMask wallet: {e}")
            return False
    
    def click_gm_button(self) -> bool:
        """Click GM button to send transaction."""
        try:
            # After connecting, the button should change to GM
            gm_selectors = [
                f'[data-network-id="{config.TEMPO_NETWORK_ID}"] button',
                f'//div[@data-network-id="{config.TEMPO_NETWORK_ID}"]//button[contains(., "GM")]',
                f'//div[@data-network-id="{config.TEMPO_NETWORK_ID}"]//button',
                f'//*[contains(text(), "{config.TEMPO_NETWORK_NAME}")]//ancestor::div[contains(@class, "card")]//button',
            ]
            
            # Wait a moment for button state to update
            time.sleep(2)
            
            clicked = False
            for selector in gm_selectors:
                try:
                    if selector.startswith('//') or selector.startswith('//*'):
                        btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        btn = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    # Check if button text contains GM or is clickable
                    btn_text = btn.text.lower()
                    if 'gm' in btn_text or 'say' in btn_text or btn.is_enabled():
                        self._scroll_to_element(btn)
                        btn.click()
                        logger.info(f"Clicked GM button: {btn_text}")
                        clicked = True
                        break
                        
                except TimeoutException:
                    continue
            
            if not clicked:
                logger.error("Could not find GM button")
                return False
            
            time.sleep(2)
            
            # Confirm transaction in MetaMask
            if not self.metamask.confirm_transaction():
                logger.error("Failed to confirm GM transaction")
                return False
            
            time.sleep(3)
            
            logger.info("GM transaction sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send GM transaction: {e}")
            return False
    
    def run_full_flow(self) -> bool:
        """
        Run the complete GM transaction flow.
        
        Steps:
        1. Navigate to onchaingm.com
        2. Find Tempo Testnet card
        3. Click Connect button
        4. Select MetaMask wallet
        5. Click GM button
        6. Confirm transaction
        """
        logger.info("Starting GM Transaction automation flow")
        
        steps = [
            ("Navigate to OnChainGM", self.navigate_to_onchaingm),
            ("Find Tempo Testnet card", self.find_tempo_card),
            ("Click Connect button", self.click_connect_button),
            ("Select MetaMask wallet", self.select_metamask_wallet),
            ("Click GM button", self.click_gm_button),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Executing step: {step_name}")
            
            if not step_func():
                logger.error(f"Step failed: {step_name}")
                return False
            
            time.sleep(1)  # Small delay between steps
        
        logger.info("GM Transaction automation completed successfully")
        return True
