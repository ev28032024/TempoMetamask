"""
OnChainGM transaction automation module with Playwright
"""
import time
import logging

from playwright.sync_api import Page, BrowserContext, TimeoutError as PWTimeout

import config
from metamask_helper import Metamask

logger = logging.getLogger(__name__)


class GMTransactionAutomation:
    """Automates GM transaction on onchaingm.com for Tempo Testnet using Playwright."""
    
    def __init__(self, context: BrowserContext, page: Page, metamask: Metamask):
        self.context = context
        self.page = page
        self.metamask = metamask
    
    def _scroll_to_element(self, element):
        """Scroll element into view."""
        try:
            element.scroll_into_view_if_needed(timeout=3000)
        except Exception:
            pass
        time.sleep(0.5)
    
    def navigate_to_onchaingm(self) -> bool:
        """Navigate to onchaingm.com."""
        try:
            self.page.goto(config.ONCHAINGM_URL, wait_until="domcontentloaded")
            time.sleep(3)
            
            logger.info(f"Navigated to: {config.ONCHAINGM_URL}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to navigate to onchaingm: {e}")
            return False
    
    def find_tempo_card(self) -> bool:
        """Find and scroll to Tempo Testnet card."""
        try:
            card_selectors = [
                f'[data-network-id="{config.TEMPO_NETWORK_ID}"]',
                f'text="{config.TEMPO_NETWORK_NAME}"',
            ]
            
            for selector in card_selectors:
                try:
                    card = self.page.locator(selector).first
                    if card.count():
                        self._scroll_to_element(card)
                        logger.info("Found Tempo Testnet card")
                        return True
                except Exception:
                    continue
            
            logger.error("Tempo Testnet card not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to find Tempo card: {e}")
            return False
    
    def click_connect_button(self) -> str:
        """Click Connect button on Tempo card. Returns 'connected', 'clicked', or 'failed'."""
        try:
            # First check if already connected (GM button visible instead of Connect)
            gm_button_selectors = [
                '[aria-label="GM on Tempo Testnet"]',
                'button:has-text("GM On")',
                'button:has-text("GM on")', 
                'button:has-text("Send GM")',
            ]
            
            for selector in gm_button_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() and btn.is_visible(timeout=1000):
                        logger.info("Wallet already connected (GM button visible)")
                        return "connected"  # Already connected, skip wallet selection
                except:
                    continue
            
            # More specific selectors to avoid clicking heart/favorite icons
            connect_selectors = [
                # Button with exact "Connect" text
                'button:text-is("Connect")',
                # Button containing "Connect" but not heart icons  
                'button:has-text("Connect"):not(:has(svg[class*="heart"]))',
                # Button in a card with network ID
                f'[data-network-id="{config.TEMPO_NETWORK_ID}"] button:has-text("Connect")',
            ]
            
            for selector in connect_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() and btn.is_visible(timeout=3000):
                        # Verify it's the right button by checking text
                        btn_text = btn.text_content() or ""
                        if "Connect" in btn_text and len(btn_text) < 20:
                            btn.click()
                            logger.info(f"Clicked Connect button: '{btn_text}'")
                            time.sleep(2)
                            return "clicked"
                except Exception:
                    continue
            
            # Fallback: find all buttons and click the one with "Connect" text
            try:
                all_buttons = self.page.locator('button').all()
                for btn in all_buttons:
                    try:
                        text = btn.text_content() or ""
                        if text.strip() == "Connect" and btn.is_visible():
                            btn.click()
                            logger.info("Clicked Connect button (fallback)")
                            time.sleep(2)
                            return "clicked"
                    except:
                        continue
            except:
                pass
            
            # If still not found, maybe already connected
            logger.warning("Connect button not found, assuming already connected")
            return "connected"
            
        except Exception as e:
            logger.error(f"Failed to click Connect: {e}")
            return "failed"
    
    def select_metamask_wallet(self) -> bool:
        """Select MetaMask from wallet selection modal."""
        try:
            time.sleep(1)
            
            metamask_selectors = [
                '[data-testid="rk-wallet-option-io.metamask"]',
                'button:has-text("MetaMask")',
            ]
            
            clicked = False
            for selector in metamask_selectors:
                try:
                    btn = self.page.locator(selector).first
                    if btn.count() and btn.is_visible(timeout=5000):
                        btn.click()
                        logger.info("Clicked MetaMask wallet option")
                        clicked = True
                        break
                except Exception:
                    continue
            
            if not clicked:
                logger.error("Could not find MetaMask wallet option")
                return False
            
            time.sleep(2)
            
            # Handle MetaMask connection popup
            self.metamask.connect_wallet()
            
            time.sleep(2)
            
            # Reload page to refresh UI after wallet connection
            logger.info("Reloading page after wallet connection...")
            self.page.reload(wait_until="domcontentloaded")
            time.sleep(3)
            
            logger.info("Wallet connection completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to select MetaMask: {e}")
            return False
    
    def click_gm_button(self) -> tuple[bool, str]:
        """Click GM button to send transaction. Returns (success, status_note)."""
        try:
            # Scroll the page and wait
            try:
                self.page.evaluate("window.scrollTo(0, 500)")
            except:
                pass
            time.sleep(2)
            
            # Check if already sent successfully
            success_selectors = [
                'h3:has-text("GM Successfully Sent on Tempo Testnet")',
                'text="GM Successfully Sent on Tempo Testnet!"',
            ]
            for sel in success_selectors:
                try:
                    success = self.page.locator(sel).first
                    if success.count() and success.is_visible(timeout=500):
                        logger.info("GM already sent successfully!")
                        return True, "OK"
                except:
                    pass
            
            # Check for orange timer (cooldown - GM already sent today)
            try:
                timer_indicator = self.page.locator('.bg-orange-500').first
                if timer_indicator.count() and timer_indicator.is_visible(timeout=500):
                    # Try to get timer text
                    timer_text = ""
                    try:
                        # Look for time text near the timer
                        timer_parent = timer_indicator.locator('xpath=../..')
                        full_text = timer_parent.text_content() or ""
                        # Extract just the time (e.g., "07h 27m" from "Tempo Testnet07h 27m")
                        import re
                        time_match = re.search(r'(\d+h\s*\d+m)', full_text)
                        if time_match:
                            timer_text = time_match.group(1).replace(' ', '')
                    except:
                        pass
                    logger.info(f"Orange timer found - GM already sent. Timer: {timer_text}")
                    return True, f"CD {timer_text}" if timer_text else "Cooldown"
            except:
                pass
            
            # Find Tempo card first
            self.find_tempo_card()
            time.sleep(1)
            
            # Try up to 3 times to click and confirm
            for click_attempt in range(3):
                logger.info(f"GM click attempt {click_attempt + 1}/3")
                
                # Check if already succeeded
                for sel in success_selectors:
                    try:
                        success = self.page.locator(sel).first
                        if success.count() and success.is_visible(timeout=300):
                            logger.info("GM Successfully Sent!")
                            return True
                    except:
                        pass
                
                # Wait before first click attempt
                if click_attempt == 0:
                    time.sleep(2)
                
                # Find and click GM button
                gm_selectors = [
                    '[aria-label="GM on Tempo Testnet"]',
                    'button:has-text("GM on Tempo Testnet")',
                    'button:has-text("GM On Tempo")',
                    'button:has-text("Send GM")',
                    'button:has-text("Say GM")',
                ]
                
                clicked = False
                for selector in gm_selectors:
                    try:
                        btn = self.page.locator(selector).first
                        if btn.count() and btn.is_visible(timeout=1000):
                            btn_text = btn.text_content() or ""
                            if "Connect" in btn_text and "GM" not in btn_text:
                                continue
                            self._scroll_to_element(btn)
                            time.sleep(0.5)  # Small pause before click
                            
                            # Execute ALL click methods TWICE for reliability
                            for repeat in range(2):
                                try:
                                    # Double click first
                                    btn.dblclick(force=True, timeout=1000)
                                except:
                                    pass
                                time.sleep(0.2)
                                try:
                                    # Force click
                                    btn.click(force=True, timeout=1000)
                                except:
                                    pass
                                time.sleep(0.2)
                                try:
                                    # JS click
                                    btn.evaluate("el => el.click()")
                                except:
                                    pass
                                try:
                                    # dispatchEvent
                                    btn.evaluate("""el => {
                                        el.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true, view: window}));
                                    }""")
                                except:
                                    pass
                                time.sleep(0.3)
                            
                            logger.info(f"Clicked GM button (all methods): '{btn_text}'")
                            clicked = True
                            break
                    except:
                        continue
                
                if not clicked:
                    logger.warning("Could not click GM button, retrying...")
                    time.sleep(2)
                    continue
                
                time.sleep(2)
                
                # Confirm in MetaMask (might need password or confirm)
                logger.info("Confirming in MetaMask...")
                self.metamask.confirm_transaction()
                
                time.sleep(3)
                
                # Check for success message
                for check in range(15):
                    try:
                        # Try multiple selectors
                        success_selectors = [
                            'h3:has-text("GM Successfully Sent on Tempo Testnet")',
                            'text="GM Successfully Sent on Tempo Testnet!"',
                        ]
                        for sel in success_selectors:
                            try:
                                success = self.page.locator(sel).first
                                if success.count() and success.is_visible(timeout=300):
                                    logger.info("GM Successfully Sent on Tempo Testnet!")
                                    return True, "OK"
                            except:
                                pass
                    except:
                        pass
                    time.sleep(1)
                
                logger.warning("Success message not found, retrying...")
            
            # Final check
            try:
                success_selectors = [
                    'h3:has-text("GM Successfully Sent on Tempo Testnet")',
                    'text="GM Successfully Sent on Tempo Testnet!"',
                ]
                for sel in success_selectors:
                    try:
                        success = self.page.locator(sel).first
                        if success.count() and success.is_visible(timeout=500):
                            logger.info("GM Successfully Sent!")
                            return True, "OK"
                    except:
                        pass
            except:
                pass
            
            logger.error("GM transaction failed - success message not found")
            return False, "Failed"
            
        except Exception as e:
            logger.error(f"Failed to send GM: {e}")
            return False, str(e)
    
    def run_full_flow(self) -> tuple[bool, str]:
        """Run the complete GM transaction flow. Returns (success, status_note)."""
        logger.info("Starting GM Transaction automation flow")
        
        # Step 1: Navigate to OnChainGM
        logger.info("Executing: Navigate to OnChainGM")
        if not self.navigate_to_onchaingm():
            logger.error("Failed: Navigate to OnChainGM")
            return False, "Failed: Navigate"
        time.sleep(1)
        
        # Step 2: Find Tempo card
        logger.info("Executing: Find Tempo card")
        if not self.find_tempo_card():
            logger.error("Failed: Find Tempo card")
            return False, "Failed: Find card"
        time.sleep(1)
        
        # Step 3: Click Connect (might already be connected)
        logger.info("Executing: Click Connect")
        connect_result = self.click_connect_button()
        
        if connect_result == "failed":
            logger.error("Failed: Click Connect")
            return False, "Failed: Connect"
        
        # Step 4: Select MetaMask (skip if already connected)
        if connect_result == "clicked":
            logger.info("Executing: Select MetaMask")
            if not self.select_metamask_wallet():
                logger.error("Failed: Select MetaMask")
                return False, "Failed: MetaMask"
            time.sleep(1)
        else:
            logger.info("Skipping MetaMask selection (already connected)")
        
        # Step 5: Click GM
        logger.info("Executing: Click GM")
        gm_success, gm_status = self.click_gm_button()
        if not gm_success:
            logger.error("Failed: Click GM")
            return False, gm_status
        
        logger.info("GM Transaction completed successfully")
        return True, gm_status
