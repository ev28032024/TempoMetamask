"""
Модуль для работы с MetaMask
Адаптировано для Tempo Testnet Automation
"""

from typing import Tuple, Optional
from loguru import logger
import re
import time

from playwright.sync_api import TimeoutError as PWTimeout, Page, BrowserContext

import config

_MM_EXTENSION_ID = "dngheoenokkefbpbnhemmiefpcbggmfd"
_MM_HOME_URL     = f"chrome-extension://{_MM_EXTENSION_ID}/home.html"
_MM_HOME_RE      = re.compile(rf"^chrome-extension://{_MM_EXTENSION_ID}/home\.html", re.I)
_MM_NOTIFY_RE    = re.compile(rf"^chrome-extension://{_MM_EXTENSION_ID}/notification\.html", re.I)
_MM_PHISHING_RE  = re.compile(r"phishing-warning", re.I)


def random_sleep(min_sec: float, max_sec: float):
    """Random sleep between min and max seconds."""
    import random
    time.sleep(random.uniform(min_sec, max_sec))


class Metamask:
    """
    Класс для работы с MetaMask.
    """

    def __init__(self, context: BrowserContext, page: Page, password: str) -> None:
        self._url = _MM_HOME_URL
        self.context = context
        self.page = page
        self.password = password

    # ---------- общие внутренние утилиты ----------

    @staticmethod
    def _mm_close_phishing_tabs(ctx):
        try:
            for p in list(ctx.pages):
                try:
                    url = p.url or ""
                except Exception:
                    url = ""
                if url and _MM_PHISHING_RE.search(url):
                    try:
                        p.close()
                        logger.warning(f"[MM] Closed phishing-warning tab: {url}")
                    except Exception:
                        ...
        except Exception:
            ...

    @staticmethod
    def _mm_pick_home_tab(ctx):
        """Возвращает вкладку MetaMask home.html, если есть. Иначе None."""
        for p in ctx.pages:
            try:
                if _MM_HOME_RE.search(p.url or ""):
                    return p
            except Exception:
                ...
        return None
    
    def _mm_dismiss_overlays(self, page, total_wait: float = 6.0) -> None:
        """
        Закрывает всплывающие подсказки/оверлеи MetaMask (onboarding поповеры).
        """
        end = time.time() + float(total_wait)
        tried_remove = False

        def _click_if(selector: str) -> bool:
            try:
                el = page.locator(selector).first
                if el.count() and el.is_visible(timeout=250):
                    el.click()
                    time.sleep(0.15)
                    return True
            except Exception:
                pass
            return False

        while time.time() < end:
            clicked = False

            for sel in (
                "button:has-text('Got it')",
                "button:has-text('OK')",
                "button:has-text('Ок')",
                "button:has-text('Понятно')",
                ".popover-container button.btn-primary",
                "[data-testid='popover-close']",
                "[aria-label='Close']",
                "[aria-label='close']",
                "button[aria-label='Close']",
                "button[aria-label='close']",
            ):
                if _click_if(sel):
                    clicked = True

            if clicked:
                continue

            try:
                has_bg = page.locator(".popover-bg, #popover-content .popover-bg").first
                if has_bg.count():
                    if not tried_remove:
                        page.evaluate("""
                            () => {
                            const bg = document.querySelector('.popover-bg');
                            if (bg) { bg.style.display = 'none'; bg.style.pointerEvents = 'none'; }
                            const pc = document.querySelector('#popover-content');
                            if (pc) { pc.style.pointerEvents = 'none'; }
                            }
                        """)
                        tried_remove = True
                        time.sleep(0.15)
                        continue
            except Exception:
                pass

            time.sleep(0.2)

    def _dismiss_quick(self, page) -> None:
        """Quick dismissal of popups - called during wait loops."""
        dismiss_selectors = [
            # Common dismissals
            "button:has-text('Got it')",
            "button:has-text('OK')",
            "button:has-text('Понятно')",
            "button:has-text('Not now')",
            "button:has-text('Не сейчас')",
            "button:has-text('Skip')",
            "button:has-text('Пропустить')",
            "button:has-text('Later')",
            "button:has-text('Позже')",
            "button:has-text('Maybe later')",
            "button:has-text('No thanks')",
            "button:has-text('Close')",
            "button:has-text('Закрыть')",
            # Close buttons
            "[data-testid='popover-close']",
            "[data-testid='not-now-button']",
            "[aria-label='Close']",
            "button[aria-label='Close']",
            ".mm-modal-header button",
            "[data-testid='whats-new-popup-close']",
            "[data-testid='survey-close']",
        ]
        
        for sel in dismiss_selectors:
            try:
                el = page.locator(sel).first
                if el.count() and el.is_visible(timeout=100):
                    try:
                        el.click(force=True, timeout=500)
                    except:
                        # JavaScript fallback
                        try:
                            el.evaluate("el => el.click()")
                        except:
                            pass
                    time.sleep(0.1)
            except:
                pass
        
        # Extra: try clicking any button with dismiss-like text
        try:
            for text in ['Not now', 'Skip', 'Later', 'Close']:
                btn = page.get_by_role("button", name=text).first
                if btn.count() and btn.is_visible(timeout=100):
                    btn.click(force=True, timeout=500)
                    time.sleep(0.1)
        except:
            pass

    # ---------- базовые действия ----------

    def open_metamask(self):
        """Открывает вкладку MM."""
        self.page.goto(self._url, wait_until="domcontentloaded")
        random_sleep(3, 4)

    def auth_metamask(self) -> None:
        """
        Надёжная авторизация в MetaMask с фокусом на home.html.
        """
        if not self.password:
            raise Exception('Не указан пароль для авторизации в MetaMask')

        ctx = self.context
        page = self.page

        # 1) Закрыть внезапные phishing-warning вкладки
        self._mm_close_phishing_tabs(ctx)

        # 2) Перейти на home.html
        try:
            self.open_metamask()
        except Exception:
            try:
                page.goto(_MM_HOME_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception:
                pass

        mm_home = self._mm_pick_home_tab(ctx)
        if not mm_home:
            try:
                page.goto(_MM_HOME_URL, wait_until="domcontentloaded")
                random_sleep(1, 2)
                mm_home = self._mm_pick_home_tab(ctx)
            except Exception:
                ...
        if not mm_home:
            raise Exception("MetaMask home.html tab not found")

        try:
            mm_home.bring_to_front()
        except Exception:
            ...

        # 3) Закрыть notification окна до разблокировки
        for p in list(ctx.pages):
            try:
                url = p.url or ""
                if _MM_NOTIFY_RE.search(url):
                    try:
                        p.close()
                    except Exception:
                        ...
            except Exception:
                ...

        # 4) Ждём форму разблокировки и вводим пароль
        try:
            mm_home.get_by_test_id('unlock-password').wait_for(state="visible", timeout=10000)
        except PWTimeout:
            # возможно уже разблокирован
            has_main = False
            for sel in (
                '[data-testid="account-menu-icon"]',
                '[data-testid="account-options-menu-button"]',
                '[data-testid="eth-overview-send"]',
            ):
                try:
                    if mm_home.locator(sel).first.is_visible():
                        has_main = True
                        break
                except Exception:
                    ...
            if has_main:
                logger.success('MetaMask уже разблокирован')
                return
            try:
                mm_home.reload(wait_until="domcontentloaded", timeout=15000)
                mm_home.get_by_test_id('unlock-password').wait_for(state="visible", timeout=8000)
            except Exception:
                raise Exception("Не удалось найти форму разблокировки MetaMask")

        # 4.1 Ввод пароля
        try:
            pwd_input = mm_home.get_by_test_id('unlock-password')
            pwd_input.click()
            time.sleep(0.2)
            
            # Clear field first
            pwd_input.press("Control+a")
            pwd_input.press("Delete")
            time.sleep(0.1)
            
            # Try fill() first
            try:
                pwd_input.fill(self.password)
            except Exception as e1:
                logger.warning(f"fill() failed: {e1}, trying type()...")
                # Fallback to type() with slow delay
                pwd_input.type(self.password, delay=50)
                logger.info("Password entered via type()")
            
            time.sleep(0.3)
        except Exception as e:
            raise Exception(f"Не удалось ввести пароль в MetaMask: {e}")

        # 4.2 Click Unlock
        clicked = False
        for testid in ('unlock-submit', 'page-container-footer-next'):
            try:
                btn = mm_home.get_by_test_id(testid)
                if btn.count() and btn.is_visible(timeout=1000):
                    btn.click(timeout=3000)
                    clicked = True
                    break
            except Exception:
                pass
        if not clicked:
            logger.info("Trying Enter key as fallback...")
            try:
                mm_home.keyboard.press("Enter")
                logger.info("Pressed Enter")
            except Exception as e:
                logger.error(f"Failed to press Enter: {e}")
        # 5) Wait for unlock
        time.sleep(2)
        
        t0 = time.time()
        unlocked = False
        while time.time() - t0 < 15:
            # Check for error message
            try:
                err_txt = (mm_home.inner_text("body") or "").lower()
                if "incorrect password" in err_txt or "неверный пароль" in err_txt:
                    logger.error("Detected 'Incorrect password' error!")
                    raise Exception("Incorrect MetaMask password")
            except Exception as ex:
                if "Incorrect" in str(ex):
                    raise
            
            # Try to dismiss any overlays that might be blocking
            self._dismiss_quick(mm_home)
            
            # Check for main panel elements
            for sel in (
                '[data-testid="account-menu-icon"]',
                '[data-testid="account-options-menu-button"]',
                '[data-testid="eth-overview-send"]',
                '[data-testid="home__asset-tab"]',
            ):
                try:
                    if mm_home.locator(sel).first.is_visible():
                        unlocked = True
                        break
                except Exception:
                    ...
            if unlocked:
                break
            random_sleep(0.3, 0.5)

        if not unlocked:
            # Try one more time after dismissing overlays
            self._mm_dismiss_overlays(mm_home, total_wait=3.0)
            for sel in (
                '[data-testid="account-menu-icon"]',
                '[data-testid="eth-overview-send"]',
            ):
                try:
                    if mm_home.locator(sel).first.is_visible():
                        unlocked = True
                        break
                except:
                    pass
        
        if not unlocked:
            raise Exception("MetaMask не разблокировался")

        try:
            self._mm_dismiss_overlays(mm_home, total_wait=3.0)
        except Exception:
            pass

        logger.success('Успешная авторизация в MetaMask')

    # ---------- подтверждения/подписи ----------

    def universal_confirm(self, total_wait: float = 8.0, rounds: int = 1) -> None:
        """
        Универсальный «кликатель» для попапов MetaMask (Next/Connect/Approve/Sign/Switch/Add).
        """
        ctx = self.context

        # All known test-ids for confirm buttons
        test_ids = [
            'page-container-footer-next',
            'confirm-footer-button',
            'confirmation-submit-button',
            'connect-button',
            'connect-approve-button',
            'signature-request-confirm-button',
            'approve-button',
            'page-container-footer-approve',
            'confirm-btn',
            'confirmFooterButton',
            'confirm-approve-button',
        ]
        
        # Button text patterns
        button_texts = [
            'Confirm', 'Подтвердить',
            'Approve', 'Одобрить', 
            'Next', 'Далее',
            'Connect', 'Подключить',
            'Sign', 'Подписать',
            'Allow', 'Разрешить',
        ]

        for _round in range(max(1, int(rounds))):
            # Open MM home tab to wake it up
            waker = None
            try:
                waker = ctx.new_page()
                waker.goto(_MM_HOME_URL, wait_until="domcontentloaded")
                time.sleep(0.5)
            except Exception:
                pass

            deadline = time.time() + float(total_wait)
            clicked_total = 0
            
            try:
                while time.time() < deadline:
                    for tab in list(ctx.pages):
                        try:
                            url = tab.url or ""
                        except Exception:
                            continue
                        
                        # Only work with MM tabs
                        if not (_MM_HOME_RE.search(url) or _MM_NOTIFY_RE.search(url)):
                            continue
                        
                        # Scroll to bottom to see confirm button
                        try:
                            tab.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        except:
                            pass

                        # Try clicking by test-id
                        for tid in test_ids:
                            try:
                                el = tab.get_by_test_id(tid).first
                                if el.count() and el.is_visible(timeout=200):
                                    el.scroll_into_view_if_needed(timeout=1000)
                                    el.click()
                                    logger.info(f"Clicked button: {tid}")
                                    clicked_total += 1
                                    time.sleep(0.5)
                            except Exception:
                                continue
                        
                        # Try clicking by button text
                        for btn_text in button_texts:
                            try:
                                btn = tab.locator(f'button:has-text("{btn_text}")').first
                                if btn.count() and btn.is_visible(timeout=200):
                                    btn.scroll_into_view_if_needed(timeout=1000)
                                    btn.click()
                                    logger.info(f"Clicked button: '{btn_text}'")
                                    clicked_total += 1
                                    time.sleep(0.5)
                            except Exception:
                                continue
                    
                    if clicked_total > 0:
                        time.sleep(0.5)
                    else:
                        time.sleep(0.3)
                        
            finally:
                if waker:
                    try: 
                        waker.close()
                    except Exception: 
                        pass

    def connect_wallet(self) -> bool:
        """Подтвердить подключение кошелька."""
        try:
            self.universal_confirm(total_wait=10.0)
            return True
        except Exception as e:
            logger.error(f"Failed to connect wallet: {e}")
            return False

    def confirm_transaction(self) -> bool:
        """Подтвердить транзакцию."""
        try:
            # Wait a moment for popup to appear
            time.sleep(2)
            self.universal_confirm(total_wait=20.0, rounds=2)
            return True
        except Exception as e:
            logger.error(f"Failed to confirm transaction: {e}")
            return False

    def approve_network(self) -> bool:
        """Подтвердить добавление сети."""
        try:
            self.universal_confirm(total_wait=10.0, rounds=2)
            return True
        except Exception as e:
            logger.error(f"Failed to approve network: {e}")
            return False
