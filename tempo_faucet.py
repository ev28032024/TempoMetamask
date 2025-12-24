"""
Tempo Testnet Faucet automation module with Playwright
"""
import time
import logging

from playwright.sync_api import Page, BrowserContext, TimeoutError as PWTimeout

import config
from metamask_helper import Metamask

logger = logging.getLogger(__name__)


class TempoFaucetAutomation:
    """Automates Tempo Testnet faucet interactions using Playwright."""
    
    def __init__(self, context: BrowserContext, page: Page, metamask: Metamask):
        self.context = context
        self.page = page
        self.metamask = metamask
    
    def _wait_and_click(self, selector: str, timeout: int = None, description: str = ""):
        """Wait for element and click it."""
        timeout = (timeout or config.ELEMENT_WAIT_TIMEOUT) * 1000  # Convert to ms
        
        try:
            element = self.page.locator(selector).first
            element.wait_for(state="visible", timeout=timeout)
            element.click()
            
            if description:
                logger.info(f"Clicked: {description}")
            
            return element
        except PWTimeout:
            raise Exception(f"Timeout waiting for {description or selector}")
    
    def navigate_to_faucet(self) -> bool:
        """Navigate to Tempo faucet page."""
        try:
            self.page.goto(config.TEMPO_FAUCET_URL, wait_until="domcontentloaded")
            time.sleep(3)
            
            logger.info(f"Navigated to: {config.TEMPO_FAUCET_URL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to faucet: {e}")
            return False
    
    def connect_metamask(self) -> bool:
        """Click MetaMask button and approve connection."""
        try:
            # Navigate to faucet
            self.page.goto(config.TEMPO_FAUCET_URL, wait_until="domcontentloaded")
            time.sleep(3)
            
            # Check if already connected (look for wallet address only)
            already_connected = False
            connected_indicators = [
                'button:has-text("0x")',  # Wallet address shown - proves connection
                '[data-testid*="account"]',  # Account indicator
            ]
            
            for selector in connected_indicators:
                try:
                    el = self.page.locator(selector).first
                    if el.count() and el.is_visible(timeout=1000):
                        text = el.text_content() or ""
                        # Only consider connected if we see an actual address
                        if "0x" in text:
                            logger.info(f"Wallet already connected (found address: {text[:15]}...)")
                            already_connected = True
                            break
                except Exception:
                    continue
            
            if already_connected:
                logger.info("Wallet already connected, skipping connection step")
                return True
            
            # Find and click the MetaMask connect button
            metamask_btn_selectors = [
                'button:has-text("MetaMask")',
                'button:has(img[alt="MetaMask"])',
                'button:has-text("Connect")',
            ]
            
            clicked = False
            for selector in metamask_btn_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() and btn.is_visible(timeout=3000):
                        btn.click()
                        logger.info(f"Clicked button: {selector}")
                        clicked = True
                        break
                except Exception:
                    continue
            
            if not clicked:
                # If no connect button found, maybe already connected
                logger.warning("No MetaMask connect button found, assuming already connected")
                return True
            
            time.sleep(2)
            
            # Handle MetaMask connection popup
            self.metamask.connect_wallet()
            
            time.sleep(2)
            logger.info("MetaMask connection completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect MetaMask: {e}")
            return False
    
    def add_tempo_network(self) -> bool:
        """Click 'Add Tempo to MetaMask' and approve network addition."""
        try:
            # Navigate back to faucet if needed
            if "tempo.xyz" not in self.page.url:
                self.page.goto(config.TEMPO_FAUCET_URL, wait_until="domcontentloaded")
                time.sleep(2)
            
            # Find and click "Add Tempo to MetaMask" button
            add_network_selectors = [
                'button:has-text("Add Tempo to MetaMask")',
                'button:has-text("Add Tempo")',
            ]
            
            clicked = False
            for selector in add_network_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() and btn.is_visible(timeout=5000):
                        btn.click()
                        logger.info("Clicked Add Tempo to MetaMask button")
                        clicked = True
                        break
                except Exception:
                    continue
            
            if not clicked:
                logger.warning("Add Tempo network button not found, network might already be added")
                return True
            
            time.sleep(2)
            
            # Approve network addition in MetaMask
            self.metamask.approve_network()
            
            time.sleep(2)
            logger.info("Network addition completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add Tempo network: {e}")
            return False
    
    def request_faucet_funds(self) -> bool:
        """Click 'Add funds' button to request test tokens."""
        try:
            # Navigate back to faucet if needed
            if "tempo.xyz" not in self.page.url:
                self.page.goto(config.TEMPO_FAUCET_URL, wait_until="domcontentloaded")
                time.sleep(2)
            
            # Check if already completed (3 checkmarks visible)
            try:
                checkmarks = self.page.locator('svg.text-green9').all()
                if len(checkmarks) >= 3:
                    logger.info("Skipping Add Funds - 3 checkmarks already visible")
                    return True
            except:
                pass
            
            # Find and click "Add funds" button
            add_funds_selectors = [
                'button:has-text("Add funds")',
            ]
            
            clicked = False
            for selector in add_funds_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() and btn.is_visible(timeout=5000):
                        btn.click()
                        logger.info("Clicked Add funds button")
                        clicked = True
                        break
                except Exception:
                    continue
            
            if not clicked:
                logger.error("Could not find Add funds button")
                return False
            
            # Wait for funds to be added
            time.sleep(5)
            
            # Check for green checkmarks (success indicators)
            try:
                checkmarks = self.page.locator('svg.text-green9').all()
                if len(checkmarks) >= 3:
                    logger.info("3 checkmarks found - all steps completed")
                    return True
            except:
                pass
            
            # Check for error messages (only if no checkmarks)
            error_selectors = [
                '.bg-destructiveTint',
                'text="Request exceeds defined limit"',
                'text="rate limited"',
                ':has-text("reverted")',
            ]
            for sel in error_selectors:
                try:
                    error_el = self.page.locator(sel).first
                    if error_el.count() and error_el.is_visible(timeout=500):
                        error_text = error_el.text_content() or "Unknown error"
                        logger.error(f"Faucet error: {error_text[:50]}")
                        return False
                except:
                    pass
            
            logger.info("Faucet funds requested successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to request faucet funds: {e}")
            return False
    
    def set_fee_token(self) -> bool:
        """Click 'Set fee token' and confirm transaction with retry."""
        
        for attempt in range(3):
            try:
                # Navigate back to faucet if needed
                if "tempo.xyz" not in self.page.url or attempt > 0:
                    self.page.goto(config.TEMPO_FAUCET_URL, wait_until="domcontentloaded")
                    time.sleep(3)
                
                # Check if already completed (3 checkmarks visible)
                try:
                    checkmarks = self.page.locator('svg.text-green9').all()
                    if len(checkmarks) >= 3:
                        logger.info("Skipping Set Fee Token - 3 checkmarks already visible")
                        return True
                except:
                    pass
                
                # Find and click "Set fee token" button
                fee_token_selectors = [
                    'button:has-text("Set fee token")',
                ]
                
                clicked = False
                for selector in fee_token_selectors:
                    try:
                        btn = self.page.locator(selector).first
                        if btn.count() and btn.is_visible(timeout=5000):
                            btn.click()
                            logger.info("Clicked Set fee token button")
                            clicked = True
                            break
                    except Exception:
                        continue
                
                if not clicked:
                    logger.warning("Set fee token button not found, might already be set")
                    return True
                
                time.sleep(2)
                
                # Confirm transaction in MetaMask
                self.metamask.confirm_transaction()
                
                time.sleep(5)
                
                # Check for green checkmarks (success indicators)
                try:
                    checkmarks = self.page.locator('svg.text-green9').all()
                    if len(checkmarks) >= 3:
                        logger.info("3 checkmarks found - all steps completed")
                        return True
                except:
                    pass
                
                # Check for error messages (only if no checkmarks)
                has_error = False
                error_selectors = [
                    '.bg-destructiveTint',
                    'text="Request exceeds defined limit"',
                    'text="rate limited"',
                    ':has-text("reverted")',
                    ':has-text("setUserToken")',
                ]
                for sel in error_selectors:
                    try:
                        error_el = self.page.locator(sel).first
                        if error_el.count() and error_el.is_visible(timeout=500):
                            error_text = error_el.text_content() or "Unknown error"
                            logger.warning(f"Set fee token error (attempt {attempt + 1}/3): {error_text[:50]}")
                            has_error = True
                            break
                    except:
                        pass
                
                if has_error:
                    if attempt < 2:
                        logger.info("Retrying after page reload...")
                        continue
                    else:
                        logger.error("Set fee token failed after 3 attempts")
                        return False
                
                logger.info("Fee token set successfully")
                return True
                
            except Exception as e:
                logger.warning(f"Set fee token attempt {attempt + 1} failed: {e}")
                if attempt < 2:
                    continue
                logger.error(f"Failed to set fee token: {e}")
                return False
        
        return False
    
    def run_full_flow(self) -> bool:
        """
        Run the complete Tempo faucet automation flow.
        """
        logger.info("Starting Tempo Faucet automation flow")
        
        steps = [
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
            
            time.sleep(1)
        
        logger.info("Tempo Faucet automation completed successfully")
        return True
