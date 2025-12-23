"""
Columbia Insurance Automation
Single file for login and quote automation
"""
import asyncio
import logging
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import (
    COLUMBIA_USERNAME, COLUMBIA_PASSWORD, COLUMBIA_LOGIN_URL, COLUMBIA_QUOTE_URL,
    BROWSER_HEADLESS, BROWSER_TIMEOUT, SESSION_DIR, SCREENSHOT_DIR, TRACE_DIR, ENABLE_TRACING
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ColumbiaAutomation:
    def __init__(self, task_id: str = "default", trace_id: str = None, clear_session: bool = False, **quote_data):
        """
        Initialize Columbia Automation
        
        Args:
            task_id: Unique identifier for this task
            trace_id: Custom trace file identifier (e.g., quote_company_name)
            clear_session: If True, clears existing session/cookies before starting
            **quote_data: Quote data fields (to be implemented based on form structure)
        """
        self.task_id = task_id
        self.trace_id = trace_id or f"columbia_{task_id}"
        self.quote_data = quote_data
        
        # Browser components
        self.playwright = None
        self.context: BrowserContext = None  # Persistent context (no separate browser object)
        self.page: Page = None
        
        # Session directory
        self.session_dir = SESSION_DIR / f"browser_data_{task_id}"
        
        # Clear session if requested
        if clear_session and self.session_dir.exists():
            import shutil
            logger.info(f"🧹 Clearing existing session: {self.session_dir}")
            shutil.rmtree(self.session_dir)
            logger.info("✅ Session cleared")
        
        self.session_dir.mkdir(parents=True, exist_ok=True)
        
        # Screenshot directory
        self.screenshot_dir = SCREENSHOT_DIR / task_id
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Trace settings (like Guard)
        self.enable_tracing = ENABLE_TRACING
        self.trace_path = None
        if self.enable_tracing:
            self.trace_path = TRACE_DIR / f"{self.trace_id}.zip"
        
        logger.info(f"ColumbiaAutomation initialized - Task ID: {task_id}, Trace ID: {self.trace_id}")
        if self.enable_tracing:
            logger.info(f"Trace will be saved to: {self.trace_path}")
        logger.info(f"Quote Data received: {quote_data}")
        logger.info(f"Person Entering Risk: {quote_data.get('person_entering_risk', 'NOT PROVIDED')}")
        logger.info(f"Email: {quote_data.get('person_entering_risk_email', 'NOT PROVIDED')}")
    
    async def init_browser(self):
        """Initialize browser with persistent session (saves cookies)"""
        logger.info("Initializing browser with persistent session...")
        
        self.playwright = await async_playwright().start()
        
        # Browser arguments
        args = [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--disable-gpu',
            '--window-size=1920,1080'
        ]
        
        logger.info(f"Using browser data from: {self.session_dir}")
        logger.info("✅ Persistent session enabled - cookies will be saved automatically")
        if self.enable_tracing:
            logger.info(f"Tracing ENABLED - will save to: {self.trace_path}")
        
        # Launch persistent context (automatically saves cookies and session data)
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.session_dir),
            headless=BROWSER_HEADLESS,
            args=args,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Start tracing if enabled (like Guard)
        if self.enable_tracing:
            await self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
            logger.info("Trace recording started")
        
        # Get the first page (or create new one)
        pages = self.context.pages
        if pages:
            self.page = pages[0]
        else:
            self.page = await self.context.new_page()
        
        self.page.set_default_timeout(BROWSER_TIMEOUT)
        
        logger.info(f"✅ Browser initialized with persistent session (Headless: {BROWSER_HEADLESS})")
    
    async def login(self):
        """
        Perform login to Columbia portal
        Sets "Remember Me" toggle to YES, then logs in
        
        Returns:
            bool: True if login successful
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 1: LOGIN")
        logger.info("=" * 80)
        
        # Check if already logged in (try navigating to quote page first)
        logger.info("Checking if already logged in via persistent session...")
        try:
            await self.page.goto(COLUMBIA_QUOTE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            current_url = self.page.url
            
            # If we're not on login page, we're already logged in
            if "Login" not in current_url and "login" not in current_url.lower():
                logger.info("✅ Already logged in via persistent session!")
                logger.info(f"Current URL: {current_url}")
                return True
        except Exception as e:
            logger.info(f"Session check failed, will login fresh: {e}")
        
        # Need to login
        logger.info(f"Login URL: {COLUMBIA_LOGIN_URL}")
        
        try:
            # Navigate to login page
            logger.info("Navigating to login page...")
            try:
                await self.page.goto(COLUMBIA_LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as nav_error:
                logger.warning(f"Navigation error (might be redirect): {nav_error}")
                # Wait a bit and check current URL
                await asyncio.sleep(2)
                current_url = self.page.url
                logger.info(f"Current URL after navigation attempt: {current_url}")
                # If we're already on a login page, continue
                if "login" not in current_url.lower():
                    raise nav_error
            
            await asyncio.sleep(2)
            
            # Take screenshot before login
            screenshot_path = self.screenshot_dir / "01_login_page.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Fill username
            logger.info("Filling username...")
            username_input = await self.page.wait_for_selector('#username', timeout=15000, state="visible")
            await username_input.fill(COLUMBIA_USERNAME)
            await asyncio.sleep(0.5)
            logger.info(f"✅ Username filled: {COLUMBIA_USERNAME}")
            
            # Fill password
            logger.info("Filling password...")
            password_input = await self.page.wait_for_selector('#password', timeout=15000, state="visible")
            await password_input.fill(COLUMBIA_PASSWORD)
            await asyncio.sleep(0.5)
            logger.info("✅ Password filled")
            
            # Set "Remember Me" toggle to YES
            logger.info("Setting 'Remember Me' toggle to YES...")
            remember_me_selectors = [
                'input[type="checkbox"][id="saveUsername"]',
                'input[type="checkbox"][name="saveUsername"]',
                'input[id="saveUsername"]',
                'input[name="saveUsername"]',
            ]
            
            remember_me_checkbox = None
            for selector in remember_me_selectors:
                try:
                    remember_me_checkbox = await self.page.query_selector(selector)
                    if remember_me_checkbox:
                        is_checked = await remember_me_checkbox.is_checked()
                        logger.info(f"✅ Found Remember Me checkbox with selector: {selector}, currently checked: {is_checked}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if remember_me_checkbox:
                # Check if already checked
                is_checked = await remember_me_checkbox.is_checked()
                logger.info(f"Remember Me checkbox current state: {is_checked}")
                
                if not is_checked:
                    # Try clicking the label first (more reliable for toggle switches)
                    try:
                        label = await self.page.query_selector('label[for="saveUsername"]')
                        if label:
                            logger.info("Clicking Remember Me label...")
                            await label.click()
                            await asyncio.sleep(0.5)
                        else:
                            # Fallback: click checkbox directly
                            logger.info("Clicking Remember Me checkbox directly...")
                            await remember_me_checkbox.click()
                            await asyncio.sleep(0.5)
                    except Exception as e:
                        logger.warning(f"Error clicking label, trying checkbox: {e}")
                        await remember_me_checkbox.click()
                        await asyncio.sleep(0.5)
                    
                    # Verify it's now checked
                    is_checked_after = await remember_me_checkbox.is_checked()
                    if is_checked_after:
                        logger.info("✅ Remember Me toggle set to YES (verified)")
                    else:
                        logger.warning("⚠️ Remember Me toggle click didn't work, trying JavaScript...")
                        # Try JavaScript click as fallback
                        await self.page.evaluate('''() => {
                            const checkbox = document.getElementById('saveUsername');
                            if (checkbox) {
                                checkbox.checked = true;
                                checkbox.dispatchEvent(new Event('change', { bubbles: true }));
                                checkbox.dispatchEvent(new Event('click', { bubbles: true }));
                            }
                        }''')
                        await asyncio.sleep(0.5)
                        is_checked_final = await remember_me_checkbox.is_checked()
                        if is_checked_final:
                            logger.info("✅ Remember Me toggle set to YES via JavaScript")
                        else:
                            logger.warning("⚠️ Remember Me toggle still not checked")
                else:
                    logger.info("✅ Remember Me toggle already set to YES")
            else:
                logger.warning("⚠️ Could not find Remember Me checkbox, continuing anyway...")
            
            # Take screenshot before clicking login
            screenshot_path = self.screenshot_dir / "02_before_login.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Click LOGIN button
            logger.info("Clicking LOGIN button...")
            # Try multiple selectors for login button
            login_button = None
            login_selectors = [
                'input[type="submit"][value*="Login"]',
                'input[type="submit"][value*="LOGIN"]',
                'button:has-text("LOGIN")',
                'button:has-text("Login")',
                'button[type="submit"]',
                'input[type="button"][value*="LOGIN"]',
            ]
            
            for selector in login_selectors:
                try:
                    login_button = await self.page.query_selector(selector)
                    if login_button:
                        button_text = await login_button.text_content()
                        button_value = await login_button.get_attribute('value')
                        logger.info(f"✅ Found login button with selector: {selector}, text: '{button_text}', value: '{button_value}'")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not login_button:
                raise Exception("Could not find login button")
            
            await login_button.click()
            await asyncio.sleep(3)
            
            # Wait for navigation after login
            logger.info("Waiting for login to complete...")
            await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            
            # Take screenshot after login
            screenshot_path = self.screenshot_dir / "03_after_login.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Check if login was successful
            current_url = self.page.url
            logger.info(f"Current URL after login: {current_url}")
            
            # Check for login error
            error_message = await self.page.query_selector('text="Login Failed", text="unable to verify"')
            if error_message:
                error_text = await error_message.text_content()
                logger.error(f"❌ Login failed: {error_text}")
                return False
            
            # Check if we're redirected away from login page
            if "Login-Legacy" not in current_url and "Login.html" not in current_url:
                logger.info("✅ Login successful - redirected away from login page")
                logger.info("✅ Cookies and session saved automatically via persistent context")
                return True
            else:
                logger.warning("⚠️ Still on login page - login may have failed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Login error: {e}", exc_info=True)
            screenshot_path = self.screenshot_dir / "error_login.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Error screenshot saved: {screenshot_path}")
            return False
    
    async def navigate_to_quote(self):
        """
        Navigate to quote page after login
        
        Returns:
            bool: True if navigation successful
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 2: NAVIGATE TO QUOTE PAGE")
        logger.info("=" * 80)
        
        try:
            # Check if we're already on the quote page (from login session check)
            current_url = self.page.url
            if "touchpoint" in current_url.lower() or "colinsgrp.com" in current_url:
                logger.info(f"✅ Already on quote page (from login check)")
                logger.info(f"Current URL: {current_url}")
                # Take screenshot anyway
                screenshot_path = self.screenshot_dir / "04_quote_page.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
                return True
            
            # Need to navigate
            logger.info(f"Navigating to quote URL: {COLUMBIA_QUOTE_URL}")
            await self.page.goto(COLUMBIA_QUOTE_URL, wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(3)
            
            # Take screenshot
            screenshot_path = self.screenshot_dir / "04_quote_page.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            logger.info(f"✅ Successfully navigated to quote page")
            logger.info(f"Current URL: {self.page.url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Navigation failed: {e}")
            screenshot_path = self.screenshot_dir / "error_navigation.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            return False
    
    async def fill_quote_details(self):
        """
        Fill quote details on the page
        1. Click "New Quote" button
        2. Wait for modal to open
        3. Click "Start Quote" button in modal
        4. Fill Policy Information form
        """
        logger.info("\n" + "=" * 80)
        logger.info("STEP 3: FILL QUOTE DETAILS")
        logger.info("=" * 80)
        
        try:
            # Wait for page to load
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
            
            # Check if we're already on the quote form page
            current_url = self.page.url
            if "quote/generalInformation" in current_url:
                logger.info("✅ Already on Policy Information page")
                logger.info(f"Current URL: {current_url}")
            else:
                # Need to start a new quote first
                # Take screenshot of quote page (before clicking New Quote)
                screenshot_path = self.screenshot_dir / "05_quote_list_page.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
                
                # Step 1: Click "New Quote" button
                logger.info("Clicking 'New Quote' button...")
                new_quote_selectors = [
                    'button[id="NewQuote"]',
                    'button#NewQuote',
                    'button:has-text("New Quote")',
                    'button.ui.button.white:has-text("New Quote")'
                ]
                
                new_quote_button = None
                for selector in new_quote_selectors:
                    try:
                        new_quote_button = await self.page.query_selector(selector)
                        if new_quote_button:
                            logger.info(f"✅ Found New Quote button with selector: {selector}")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not new_quote_button:
                    # Try waiting for it
                    logger.info("Waiting for New Quote button to appear...")
                    new_quote_button = await self.page.wait_for_selector('button[id="NewQuote"]', timeout=10000, state="visible")
                
                await new_quote_button.click()
                logger.info("✅ New Quote button clicked")
                await asyncio.sleep(2)
                
                # Take screenshot after clicking New Quote (modal should be open)
                screenshot_path = self.screenshot_dir / "06_modal_opened.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
                
                # Step 2: Wait for modal to open and click "Start Quote" button
                logger.info("Waiting for 'Select Products to Quote' modal to open...")
                try:
                    # Wait for modal to appear
                    await self.page.wait_for_selector('text="Select Products to Quote", .ui.modal:has-text("Select Products")', timeout=10000, state="visible")
                    logger.info("✅ Modal opened")
                except Exception as e:
                    logger.warning(f"Modal detection issue: {e}, continuing anyway...")
                
                await asyncio.sleep(1)
                
                # Click "Start Quote" button in modal
                logger.info("Clicking 'Start Quote' button in modal...")
                start_quote_selectors = [
                    'button:has-text("Start Quote")',
                    'button.ui.primary.button:has-text("Start Quote")',
                    'button[class*="primary"]:has-text("Start Quote")',
                ]
                
                start_quote_button = None
                for selector in start_quote_selectors:
                    try:
                        start_quote_button = await self.page.query_selector(selector)
                        if start_quote_button:
                            button_text = await start_quote_button.text_content()
                            logger.info(f"✅ Found Start Quote button with selector: {selector}, text: '{button_text}'")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not start_quote_button:
                    # Try waiting for it
                    logger.info("Waiting for Start Quote button to appear...")
                    start_quote_button = await self.page.wait_for_selector('button:has-text("Start Quote")', timeout=10000, state="visible")
                
                await start_quote_button.click()
                logger.info("✅ Start Quote button clicked")
                await asyncio.sleep(3)
                
                # Wait for navigation to Policy Information page
                await self.page.wait_for_load_state("domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # Verify we're on the Policy Information page
                current_url = self.page.url
                if "quote/generalInformation" not in current_url:
                    logger.warning(f"Expected Policy Information page, but URL is: {current_url}")
                else:
                    logger.info(f"✅ Navigated to Policy Information page: {current_url}")
            
            # ================================================================
            # FILL POLICY INFORMATION FORM
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("FILLING POLICY INFORMATION FORM")
            logger.info("=" * 80)
            
            # Take screenshot before filling
            screenshot_path = self.screenshot_dir / "08_policy_info_before.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Field 1: "Is this a new venture?" - Select "No"
            logger.info("Selecting 'No' for 'Is this a new venture?'...")
            new_venture_selectors = [
                'input[type="radio"][id="newVenture_N"]',
                'input[type="radio"][name="newVenture"][value="N"]',
                '#newVenture_N',
                'input#newVenture_N'
            ]
            
            new_venture_radio = None
            for selector in new_venture_selectors:
                try:
                    new_venture_radio = await self.page.query_selector(selector)
                    if new_venture_radio:
                        logger.info(f"✅ Found newVenture radio button with selector: {selector}")
                        break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if new_venture_radio:
                # Try clicking the label first (more reliable)
                try:
                    label = await self.page.query_selector('label[for="newVenture_N"]')
                    if label:
                        await label.click()
                        await asyncio.sleep(0.5)
                        logger.info("✅ Selected 'No' for new venture (via label)")
                    else:
                        await new_venture_radio.click()
                        await asyncio.sleep(0.5)
                        logger.info("✅ Selected 'No' for new venture (via radio)")
                except Exception as e:
                    logger.warning(f"Error clicking newVenture radio: {e}, trying JavaScript...")
                    await self.page.evaluate('''() => {
                        const radio = document.getElementById('newVenture_N');
                        if (radio) {
                            radio.checked = true;
                            radio.dispatchEvent(new Event('change', { bubbles: true }));
                            radio.dispatchEvent(new Event('click', { bubbles: true }));
                        }
                    }''')
                    logger.info("✅ Selected 'No' for new venture (via JavaScript)")
            else:
                logger.warning("⚠️ Could not find newVenture radio button")
            
            await asyncio.sleep(0.5)
            
            # Field 2: Effective Date - Format: mm/dd/yyyy (current + 1 day)
            logger.info("Filling Effective Date...")
            effective_date = self.quote_data.get('effective_date', None)
            if not effective_date:
                # Default to today's date + 1 day
                from datetime import datetime, timedelta
                effective_date = (datetime.now() + timedelta(days=1)).strftime("%m/%d/%Y")
            
            try:
                await self.page.wait_for_selector('#effectiveDate', timeout=10000, state="visible")
                await self.page.click('#effectiveDate')
                await asyncio.sleep(0.3)
                await self.page.fill('#effectiveDate', "")  # Clear existing value
                await self.page.fill('#effectiveDate', effective_date)
                await asyncio.sleep(0.5)
                
                # Verify it was filled
                filled_value = await self.page.input_value('#effectiveDate')
                if filled_value == effective_date:
                    logger.info(f"✅ Effective Date filled: {effective_date}")
                else:
                    logger.warning(f"⚠️ Effective Date value mismatch. Expected: {effective_date}, Got: {filled_value}")
            except Exception as e:
                logger.warning(f"⚠️ Could not fill effectiveDate input: {e}")
            
            await asyncio.sleep(0.5)
            
            # Field 3: Person Entering Risk (Contact Name)
            logger.info("Filling Person Entering Risk...")
            person_entering_risk = self.quote_data.get('person_entering_risk', self.quote_data.get('contact_name', ''))
            if person_entering_risk:
                try:
                    await self.page.wait_for_selector('#personEnteringRisk', timeout=10000, state="visible")
                    await self.page.click('#personEnteringRisk')
                    await asyncio.sleep(0.3)
                    await self.page.fill('#personEnteringRisk', "")  # Clear any existing value
                    await self.page.fill('#personEnteringRisk', person_entering_risk)
                    await asyncio.sleep(0.5)
                    
                    # Verify it was filled
                    filled_value = await self.page.input_value('#personEnteringRisk')
                    if filled_value == person_entering_risk:
                        logger.info(f"✅ Person Entering Risk filled: {person_entering_risk}")
                    else:
                        logger.warning(f"⚠️ Person Entering Risk value mismatch. Expected: {person_entering_risk}, Got: {filled_value}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill personEnteringRisk input: {e}")
            else:
                logger.warning("⚠️ Person Entering Risk not provided in quote_data")
            
            await asyncio.sleep(0.5)
            
            # Field 4: Email of Person Entering Risk
            logger.info("Filling Email of Person Entering Risk...")
            person_email = self.quote_data.get('person_entering_risk_email', self.quote_data.get('email', ''))
            if person_email:
                try:
                    await self.page.wait_for_selector('#personEnteringRiskEmail', timeout=10000, state="visible")
                    await self.page.click('#personEnteringRiskEmail')
                    await asyncio.sleep(0.3)
                    await self.page.fill('#personEnteringRiskEmail', "")  # Clear any existing value
                    await self.page.fill('#personEnteringRiskEmail', person_email)
                    await asyncio.sleep(0.5)
                    
                    # Verify it was filled
                    filled_value = await self.page.input_value('#personEnteringRiskEmail')
                    if filled_value == person_email:
                        logger.info(f"✅ Email of Person Entering Risk filled: {person_email}")
                    else:
                        logger.warning(f"⚠️ Email value mismatch. Expected: {person_email}, Got: {filled_value}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill personEnteringRiskEmail input: {e}")
            else:
                logger.warning("⚠️ Email of Person Entering Risk not provided in quote_data")
            
            await asyncio.sleep(0.5)
            
            # Field 5: Business Type - Select "LIMITED LIABILITY COMPANY" (default)
            business_type = self.quote_data.get('business_type', 'LIMITED LIABILITY COMPANY')
            logger.info(f"Filling Business Type dropdown with: {business_type}...")
            try:
                # Wait for the Business Type dropdown to be visible
                await self.page.wait_for_selector('#businessType', timeout=10000, state="visible")
                
                # Click on the dropdown to open it
                await self.page.click('#businessType')
                await asyncio.sleep(0.5)
                
                # Wait for the dropdown menu to appear and select the business type
                # Look for the option with text matching the business_type
                option_selector = f'div[role="option"]:has-text("{business_type}")'
                try:
                    await self.page.wait_for_selector(option_selector, timeout=10000, state="visible")
                    await self.page.click(option_selector)
                    await asyncio.sleep(0.5)
                except:
                    # Fallback: Find all options and click the one with matching text
                    logger.info("Trying alternative method to select Business Type...")
                    options = await self.page.query_selector_all('div[role="option"]')
                    option_found = False
                    for option in options:
                        text = await option.text_content()
                        if text and business_type.upper() in text.upper():
                            await option.click()
                            await asyncio.sleep(0.5)
                            option_found = True
                            break
                    if not option_found:
                        raise Exception(f"Could not find Business Type option: {business_type}")
                
                # Verify it was selected by checking the displayed text
                selected_text = await self.page.text_content('#businessType .text')
                if selected_text and business_type.upper() in selected_text.upper():
                    logger.info(f"✅ Business Type selected: {selected_text.strip()}")
                else:
                    logger.warning(f"⚠️ Business Type selection verification failed. Expected: {business_type}, Got: {selected_text}")
            except Exception as e:
                logger.warning(f"⚠️ Could not fill Business Type dropdown: {e}")
            
            await asyncio.sleep(1)
            
            # Wait for page to fully load
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            await asyncio.sleep(1)
            
            # Field 6: Company Name (geosuggest input)
            company_name = self.quote_data.get('company_name', self.quote_data.get('business_name', ''))
            if company_name:
                logger.info(f"Filling Company Name: {company_name}...")
                try:
                    # Use locator which is more flexible
                    company_field = self.page.locator('#geosuggest_input--insuredName.company').or_(self.page.locator('input[name="insuredName.company"]'))
                    await company_field.wait_for(state="visible", timeout=15000)
                    await company_field.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await company_field.click()
                    await asyncio.sleep(0.3)
                    await company_field.fill("")
                    await company_field.fill(company_name)
                    await asyncio.sleep(0.5)
                    
                    # Click outside to dismiss dropdown suggestions
                    await self.page.click('body', position={'x': 100, 'y': 100})
                    await asyncio.sleep(0.3)
                    
                    # Verify it was filled
                    filled_value = await company_field.input_value()
                    if filled_value == company_name:
                        logger.info(f"✅ Company Name filled: {company_name}")
                    else:
                        logger.warning(f"⚠️ Company Name value mismatch. Expected: {company_name}, Got: {filled_value}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill Company Name: {e}")
                    # Take screenshot for debugging
                    screenshot_path = self.screenshot_dir / "error_company_name.png"
                    await self.page.screenshot(path=str(screenshot_path), full_page=True)
            else:
                logger.warning("⚠️ Company Name not provided in quote_data")
            
            await asyncio.sleep(0.5)
            
            # Field 7: DBA (Optional)
            dba_name = self.quote_data.get('dba', self.quote_data.get('dba_name', ''))
            if dba_name:
                logger.info(f"Filling DBA (Optional): {dba_name}...")
                try:
                    # Wait a bit after Company Name is filled, as DBA might appear conditionally
                    await asyncio.sleep(1)
                    
                    # Use Playwright's fill method with proper selector (more reliable than JavaScript)
                    try:
                        # Try using attribute selector which handles dots better
                        dba_field = self.page.locator('input[name="insuredName.dba"]').or_(self.page.locator('input[id="insuredName.dba"]'))
                        await dba_field.wait_for(state="visible", timeout=15000)
                        await dba_field.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        
                        # Click to focus the field
                        await dba_field.click()
                        await asyncio.sleep(0.3)
                        
                        # Clear the field first
                        await dba_field.fill("")
                        await asyncio.sleep(0.2)
                        
                        # Type the value character by character to simulate real typing
                        await dba_field.type(dba_name, delay=50)
                        await asyncio.sleep(0.5)
                        
                        # Click outside to dismiss dropdown suggestions
                        await self.page.click('body', position={'x': 100, 'y': 100})
                        await asyncio.sleep(0.3)
                        
                        # Verify it was filled
                        filled_value = await dba_field.input_value()
                        if filled_value == dba_name:
                            logger.info(f"✅ DBA filled: {dba_name}")
                        else:
                            # If typing didn't work, try JavaScript as fallback
                            logger.warning(f"⚠️ DBA value mismatch after typing. Expected: {dba_name}, Got: {filled_value}. Trying JavaScript...")
                            await self.page.evaluate(f'''() => {{
                                const el = document.getElementById('insuredName.dba');
                                if (el) {{
                                    el.focus();
                                    el.select();
                                    el.value = '';
                                    // Set value and trigger all necessary events
                                    el.value = '{dba_name}';
                                    // Trigger input event
                                    const inputEvent = new Event('input', {{ bubbles: true, cancelable: true }});
                                    el.dispatchEvent(inputEvent);
                                    // Trigger change event
                                    const changeEvent = new Event('change', {{ bubbles: true, cancelable: true }});
                                    el.dispatchEvent(changeEvent);
                                    // Trigger keyup event (some forms listen to this)
                                    const keyupEvent = new KeyboardEvent('keyup', {{ bubbles: true, cancelable: true }});
                                    el.dispatchEvent(keyupEvent);
                                    // Trigger blur event
                                    el.blur();
                                }}
                            }}''')
                            await asyncio.sleep(0.5)
                            
                            # Click outside to dismiss dropdown suggestions
                            await self.page.click('body', position={'x': 100, 'y': 100})
                            await asyncio.sleep(0.3)
                            
                            # Verify again
                            filled_value = await dba_field.input_value()
                            if filled_value == dba_name:
                                logger.info(f"✅ DBA filled using JavaScript fallback: {dba_name}")
                            else:
                                logger.warning(f"⚠️ DBA value still incorrect. Expected: {dba_name}, Got: {filled_value}")
                    except Exception as selector_error:
                        logger.warning(f"CSS selector approach failed: {selector_error}, trying JavaScript...")
                        # Fallback to JavaScript
                        await self.page.evaluate(f'''() => {{
                            const el = document.getElementById('insuredName.dba');
                            if (el) {{
                                el.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                                el.focus();
                                el.select();
                                el.value = '';
                                el.value = '{dba_name}';
                                // Trigger all necessary events
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                el.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
                                el.blur();
                            }}
                        }}''')
                        await asyncio.sleep(0.5)
                        
                        # Click outside to dismiss dropdown suggestions
                        await self.page.click('body', position={'x': 100, 'y': 100})
                        await asyncio.sleep(0.3)
                        
                        logger.info(f"✅ DBA filled using JavaScript: {dba_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill DBA (field might not be present or hidden): {e}")
                    # Take screenshot for debugging
                    screenshot_path = self.screenshot_dir / "error_dba.png"
                    await self.page.screenshot(path=str(screenshot_path), full_page=True)
            else:
                logger.info("ℹ️ DBA not provided (optional field skipped)")
            
            await asyncio.sleep(0.5)
            
            # Field 8: Mailing Address (geosuggest input)
            mailing_address = self.quote_data.get('mailing_address', self.quote_data.get('address', ''))
            if not mailing_address:
                # Default address if not provided
                mailing_address = "280 Griffin Street, McDonough, GA 30253"
                logger.info(f"Using default mailing address: {mailing_address}")
            
            logger.info(f"Filling Mailing Address: {mailing_address}...")
            try:
                address_field = self.page.locator('#geosuggest_input--address.fullAddress').or_(self.page.locator('input[name="address.fullAddress"]'))
                await address_field.wait_for(state="visible", timeout=15000)
                await address_field.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await address_field.click()
                await asyncio.sleep(0.3)
                await address_field.fill("")
                
                # Type the address character by character
                await address_field.type(mailing_address, delay=50)
                await asyncio.sleep(1)  # Wait for suggestions dropdown to appear
                
                # Wait for suggestions dropdown to appear and select the first suggestion
                logger.info("Waiting for address suggestions to appear...")
                try:
                    # Wait for the geosuggest dropdown menu to appear (check for visible suggestions)
                    # Try multiple selectors for the suggestions container
                    suggestions_selectors = [
                        'div.geosuggest__suggests',
                        'div[class*="geosuggest__suggests"]',
                        'ul.geosuggest__suggests',
                        'div.geosuggest__suggests-wrapper ul',
                    ]
                    
                    suggestions_visible = False
                    for selector in suggestions_selectors:
                        try:
                            suggestions_container = self.page.locator(selector).first
                            await suggestions_container.wait_for(state="visible", timeout=3000)
                            suggestions_visible = True
                            logger.info(f"✅ Address suggestions dropdown appeared (selector: {selector})")
                            break
                        except:
                            continue
                    
                    if suggestions_visible:
                        # Try multiple selectors for the first suggestion item
                        suggestion_item_selectors = [
                            'div.geosuggest__suggests li:first-child',
                            'div.geosuggest__suggests > div:first-child',
                            'div.geosuggest__item:first-child',
                            'div[class*="geosuggest__item"]:first-child',
                            'li.geosuggest__item:first-child',
                        ]
                        
                        suggestion_selected = False
                        for item_selector in suggestion_item_selectors:
                            try:
                                first_suggestion = self.page.locator(item_selector).first
                                if await first_suggestion.count() > 0:
                                    # Get the text of the first suggestion for logging
                                    suggestion_text = await first_suggestion.text_content()
                                    logger.info(f"Selecting first suggestion: {suggestion_text}")
                                    
                                    # Click the first suggestion
                                    await first_suggestion.click()
                                    await asyncio.sleep(0.5)
                                    logger.info("✅ First address suggestion selected")
                                    suggestion_selected = True
                                    break
                            except:
                                continue
                        
                        if not suggestion_selected:
                            # Fallback: Use arrow down + Enter
                            logger.info("Could not click suggestion, trying arrow down + Enter...")
                            await address_field.press("ArrowDown")
                            await asyncio.sleep(0.3)
                            await address_field.press("Enter")
                            await asyncio.sleep(0.5)
                            logger.info("✅ Selected suggestion using arrow down + Enter")
                    else:
                        # If suggestions don't appear, use arrow down + Enter anyway
                        logger.info("Suggestions dropdown not found, trying arrow down + Enter...")
                        await address_field.press("ArrowDown")
                        await asyncio.sleep(0.3)
                        await address_field.press("Enter")
                        await asyncio.sleep(0.5)
                        logger.info("✅ Selected suggestion using arrow down + Enter")
                except Exception as suggest_error:
                    logger.warning(f"Error selecting suggestion: {suggest_error}, trying arrow down + Enter...")
                    # Fallback: Try arrow down + Enter on the input field
                    await address_field.press("ArrowDown")
                    await asyncio.sleep(0.3)
                    await address_field.press("Enter")
                    await asyncio.sleep(0.5)
                    logger.info("✅ Selected suggestion using arrow down + Enter (fallback)")
                
                # Verify it was filled (it should now have the selected address value)
                filled_value = await address_field.input_value()
                logger.info(f"✅ Mailing Address filled: {filled_value}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not fill Mailing Address: {e}")
                # Take screenshot for debugging
                screenshot_path = self.screenshot_dir / "error_mailing_address.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
            
            await asyncio.sleep(1)
            
            # Take screenshot after filling all fields
            screenshot_path = self.screenshot_dir / "09_policy_info_filled.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Click Next button
            logger.info("Clicking Next button...")
            try:
                await self.page.wait_for_selector('#Next', timeout=10000, state="visible")
                await self.page.click('#Next')
                await asyncio.sleep(2)
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                logger.info("✅ Next button clicked")
                
                # Take screenshot after clicking Next
                screenshot_path = self.screenshot_dir / "10_after_next.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not click Next button: {e}")
                raise
            
            logger.info("✅ Policy Information form filled and submitted")
            
            # ================================================================
            # SAFEGUARD / POLICY INFORMATION PAGE
            # URL: https://touchpoint01.colinsgrp.com/quote/safeguard/policyInformation
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("SAFEGUARD / POLICY INFORMATION PAGE")
            logger.info("=" * 80)
            
            # Wait for the new page URL
            logger.info("Waiting for Safeguard/Policy Information page...")
            try:
                await self.page.wait_for_url("**/quote/safeguard/policyInformation", timeout=30000)
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                logger.info(f"✅ Navigated to Safeguard/Policy Information page: {self.page.url}")
            except Exception as e:
                logger.error(f"❌ Failed to navigate to Safeguard/Policy Information page: {e}")
                screenshot_path = self.screenshot_dir / "error_safeguard_navigation.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # Take screenshot of the new page
            screenshot_path = self.screenshot_dir / "11_safeguard_page.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Fill Business Type dropdown - Select "Mercantile"
            logger.info("Filling Business Type dropdown with: Mercantile...")
            try:
                # Wait for page to fully load
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(1)
                
                # The dropdown ID is sfg.businessType (with a dot), need to use attribute selector
                # Use JavaScript to click the dropdown directly since the ID has a dot
                dropdown_clicked = await self.page.evaluate('''() => {
                    const dropdown = document.getElementById('sfg.businessType');
                    if (dropdown) {
                        dropdown.scrollIntoView({behavior: 'smooth', block: 'center'});
                        dropdown.click();
                        return true;
                    }
                    return false;
                }''')
                
                if dropdown_clicked:
                    logger.info("✅ Clicked Business Type dropdown (sfg.businessType)")
                    await asyncio.sleep(0.5)
                else:
                    # Fallback: Try using attribute selector
                    logger.info("JavaScript click failed, trying attribute selector...")
                    dropdown = self.page.locator('[id="sfg.businessType"]').first
                    if await dropdown.count() > 0:
                        await dropdown.scroll_into_view_if_needed()
                        await asyncio.sleep(0.5)
                        await dropdown.click()
                        await asyncio.sleep(0.5)
                    else:
                        raise Exception("Could not find Business Type dropdown")
                
                # Wait for the dropdown menu to appear and select "Mercantile"
                logger.info("Waiting for Business Type dropdown menu to appear...")
                await asyncio.sleep(0.5)
                
                # Use JavaScript to find and click the Mercantile option
                # Based on the HTML, the option with text "Mercantile" should be clicked
                result = await self.page.evaluate('''() => {
                    // Wait a bit for menu to appear
                    const menu = document.querySelector('div.menu.transition');
                    if (!menu) return false;
                    
                    // Find the option with "Mercantile" text
                    const options = Array.from(document.querySelectorAll('div[role="option"], div.item'));
                    const mercantileOption = options.find(opt => {
                        const text = opt.textContent || '';
                        return text.trim() === 'Mercantile' || text.includes('Mercantile');
                    });
                    
                    if (mercantileOption) {
                        mercantileOption.scrollIntoView({behavior: 'smooth', block: 'center'});
                        mercantileOption.click();
                        return true;
                    }
                    return false;
                }''')
                
                if result:
                    await asyncio.sleep(0.5)
                    logger.info("✅ Business Type selected: Mercantile")
                    
                    # Verify it was selected by checking the divider text
                    selected_text = await self.page.evaluate('''() => {
                        const dropdown = document.getElementById('sfg.businessType');
                        if (dropdown) {
                            const textDiv = dropdown.querySelector('.divider.text');
                            return textDiv ? textDiv.textContent.trim() : null;
                        }
                        return null;
                    }''')
                    
                    if selected_text and 'Mercantile' in selected_text:
                        logger.info(f"✅ Verified Business Type selection: {selected_text}")
                    else:
                        logger.warning(f"⚠️ Could not verify selection. Got: {selected_text}")
                else:
                    raise Exception("Could not find Mercantile option in dropdown")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not fill Business Type dropdown: {e}")
                screenshot_path = self.screenshot_dir / "error_business_type_safeguard.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # Take screenshot after filling Business Type
            screenshot_path = self.screenshot_dir / "12_business_type_filled.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Click Next button on Safeguard page
            logger.info("Clicking Next button on Safeguard page...")
            try:
                await self.page.wait_for_selector('#Next', timeout=10000, state="visible")
                await self.page.click('#Next')
                await asyncio.sleep(2)
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                logger.info("✅ Next button clicked on Safeguard page")
                
                # Take screenshot after clicking Next
                screenshot_path = self.screenshot_dir / "13_after_safeguard_next.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
            
            except Exception as e:
                logger.warning(f"⚠️ Could not click Next button on Safeguard page: {e}")
                raise
            
            # ================================================================
            # LOCATIONS PAGE
            # URL: https://touchpoint01.colinsgrp.com/quote/safeguard/locations
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("LOCATIONS PAGE")
            logger.info("=" * 80)
            
            # Wait for the Locations page URL
            logger.info("Waiting for Locations page...")
            try:
                await self.page.wait_for_url("**/quote/safeguard/locations", timeout=30000)
                await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
                await asyncio.sleep(2)
                logger.info(f"✅ Navigated to Locations page: {self.page.url}")
            except Exception as e:
                logger.error(f"❌ Failed to navigate to Locations page: {e}")
                screenshot_path = self.screenshot_dir / "error_locations_navigation.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # Take screenshot of the Locations page
            screenshot_path = self.screenshot_dir / "14_locations_page.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Click "New Location" button
            logger.info("Clicking 'New Location' button...")
            try:
                # Try multiple selectors for the New Location button
                new_location_selectors = [
                    'button.newLocationButton',
                    'button:has-text("New Location")',
                    'button.ui.primary.button:has-text("New Location")',
                    'button[class*="newLocationButton"]',
                ]
                
                button_found = False
                for selector in new_location_selectors:
                    try:
                        new_location_button = self.page.locator(selector).first
                        if await new_location_button.count() > 0:
                            await new_location_button.wait_for(state="visible", timeout=10000)
                            await new_location_button.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await new_location_button.click()
                            await asyncio.sleep(2)
                            logger.info(f"✅ New Location button clicked (selector: {selector})")
                            button_found = True
                            break
                    except:
                        continue
                
                if not button_found:
                    raise Exception("Could not find New Location button")
                
                # Take screenshot after clicking New Location button
                screenshot_path = self.screenshot_dir / "15_after_new_location_click.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not click New Location button: {e}")
                screenshot_path = self.screenshot_dir / "error_new_location_button.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # Wait for Location Information modal to appear and click "Address Same As Mailing" button
            logger.info("Waiting for Location Information modal to appear...")
            await asyncio.sleep(1)
            
            logger.info("Clicking 'Address Same As Mailing' button...")
            try:
                # Try multiple selectors for the Address Same As Mailing button
                address_same_selectors = [
                    'button:has-text("Address Same As Mailing")',
                    'button.ui.primary.button:has-text("Address Same As Mailing")',
                    'button[class*="primary"]:has-text("Address Same As Mailing")',
                ]
                
                button_found = False
                for selector in address_same_selectors:
                    try:
                        address_same_button = self.page.locator(selector).first
                        if await address_same_button.count() > 0:
                            await address_same_button.wait_for(state="visible", timeout=10000)
                            await address_same_button.scroll_into_view_if_needed()
                            await asyncio.sleep(0.5)
                            await address_same_button.click()
                            await asyncio.sleep(1)
                            logger.info(f"✅ Address Same As Mailing button clicked (selector: {selector})")
                            button_found = True
                            break
                    except:
                        continue
                
                if not button_found:
                    raise Exception("Could not find Address Same As Mailing button")
                
                # Take screenshot after clicking Address Same As Mailing button
                screenshot_path = self.screenshot_dir / "16_after_address_same_click.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not click Address Same As Mailing button: {e}")
                screenshot_path = self.screenshot_dir / "error_address_same_button.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # Wait for Protection Class section to appear and select the appropriate option
            logger.info("Waiting for Protection Class section to appear...")
            # Wait for the protection class label to appear
            try:
                await self.page.wait_for_selector('label[for="protectionClass"], label:has-text("Protection Class")', timeout=15000, state="visible")
                logger.info("✅ Protection Class section appeared")
                await asyncio.sleep(20)  # Give additional time for options to load (20 seconds)
            except:
                logger.warning("⚠️ Protection Class label not found, continuing anyway...")
                await asyncio.sleep(20)  # Wait a bit longer (20 seconds)
            
            logger.info("Selecting Protection Class...")
            try:
                # Use JavaScript to find all protection class radio options
                selection_result = await self.page.evaluate('''() => {
                    // Try multiple selectors to find protection class radio options
                    let radioOptions = Array.from(document.querySelectorAll('div.radioOption[id*="radio_protectionClass"]'));
                    
                    // If not found, try finding by the parent container
                    if (radioOptions.length === 0) {
                        const protectionClassLabel = Array.from(document.querySelectorAll('label')).find(
                            label => label.textContent && label.textContent.includes('Protection Class')
                        );
                        if (protectionClassLabel) {
                            const fieldContainer = protectionClassLabel.closest('.field');
                            if (fieldContainer) {
                                radioOptions = Array.from(fieldContainer.querySelectorAll('div.radioOption'));
                            }
                        }
                    }
                    
                    // Try alternative: find by input name
                    if (radioOptions.length === 0) {
                        const inputs = Array.from(document.querySelectorAll('input[name="protectionClass"]'));
                        if (inputs.length > 0) {
                            radioOptions = inputs.map(input => input.closest('div.radioOption')).filter(el => el !== null);
                        }
                    }
                    
                    if (radioOptions.length === 0) {
                        return {status: 'not_found', message: 'No protection class options found'};
                    }
                    
                    if (radioOptions.length === 1) {
                        // Only one option, check if it's already selected
                        const radio = radioOptions[0].querySelector('input[type="radio"]');
                        if (radio && radio.checked) {
                            return {status: 'already_selected', message: 'Only one option and already selected'};
                        } else {
                            // Select the single option
                            const label = radioOptions[0].querySelector('label');
                            if (label) {
                                label.click();
                                return {status: 'selected', message: 'Single option selected'};
                            }
                        }
                    }
                    
                    // Multiple options - need to find the one with minimum number pattern (without x)
                    const optionsWithPatterns = [];
                    
                    for (const option of radioOptions) {
                        const label = option.querySelector('label');
                        if (!label) continue;
                        
                        const text = label.textContent || '';
                        // Match patterns like (01), (02), (03) etc. (without x)
                        const match = text.match(/\\((\\d{2})\\)/);
                        if (match) {
                            const number = parseInt(match[1], 10);
                            optionsWithPatterns.push({
                                element: label,
                                number: number,
                                text: text.trim()
                            });
                        }
                    }
                    
                    if (optionsWithPatterns.length === 0) {
                        return {status: 'no_pattern', message: 'No options with number patterns found'};
                    }
                    
                    // Sort by number and select the minimum (lowest number)
                    optionsWithPatterns.sort((a, b) => a.number - b.number);
                    const selectedOption = optionsWithPatterns[0];
                    
                    // Click the option with minimum number
                    selectedOption.element.click();
                    
                    return {
                        status: 'selected',
                        message: `Selected option with minimum number: ${selectedOption.text}`,
                        selectedText: selectedOption.text,
                        selectedNumber: selectedOption.number
                    };
                }''')
                
                if selection_result['status'] == 'not_found':
                    logger.warning("⚠️ Protection Class options not found - may not have appeared yet")
                elif selection_result['status'] == 'already_selected':
                    logger.info("✅ Protection Class: Only one option available and already selected")
                elif selection_result['status'] == 'selected':
                    logger.info(f"✅ Protection Class selected: {selection_result.get('selectedText', 'N/A')}")
                    if 'selectedNumber' in selection_result:
                        logger.info(f"   Selected number pattern: ({selection_result['selectedNumber']:02d})")
                elif selection_result['status'] == 'no_pattern':
                    logger.warning("⚠️ No protection class options with number patterns found")
                else:
                    logger.warning(f"⚠️ Unknown selection status: {selection_result.get('status')}")
                
                await asyncio.sleep(1)
                
                # Take screenshot after selecting Protection Class
                screenshot_path = self.screenshot_dir / "17_after_protection_class_selected.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not select Protection Class: {e}")
                screenshot_path = self.screenshot_dir / "error_protection_class.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                # Don't raise - continue even if protection class selection fails
            
            # Fill Property Deductible Amount - Select $2,500 (second option)
            logger.info("Selecting Property Deductible Amount: $2,500...")
            try:
                # Wait for Property Deductible Amount section to be visible
                await self.page.wait_for_selector('label[for="propertyDeductibleAmount"], label:has-text("Property Deductible Amount")', timeout=10000, state="visible")
                await asyncio.sleep(0.5)
                
                # Use JavaScript to find and click the $2,500 option (most reliable method)
                result = await self.page.evaluate('''() => {
                    // Find the $2,500 option div
                    const optionDiv = document.getElementById('radio_propertyDeductibleAmount_2500');
                    if (!optionDiv) {
                        return {success: false, message: 'Option div not found'};
                    }
                    
                    // Try clicking the label first (most reliable)
                    const label = optionDiv.querySelector('label[for="propertyDeductibleAmount_2500"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'smooth', block: 'center'});
                        label.click();
                        // Wait a bit and check if it was selected
                        setTimeout(() => {
                            const input = document.getElementById('propertyDeductibleAmount_2500');
                            if (input && input.checked) {
                                return {success: true, method: 'label'};
                            }
                        }, 100);
                        return {success: true, method: 'label'};
                    }
                    
                    // Fallback: click the input directly
                    const input = optionDiv.querySelector('input[type="radio"]');
                    if (input) {
                        input.scrollIntoView({behavior: 'smooth', block: 'center'});
                        input.click();
                        return {success: true, method: 'input'};
                    }
                    
                    // Last resort: click the div itself
                    optionDiv.scrollIntoView({behavior: 'smooth', block: 'center'});
                    optionDiv.click();
                    return {success: true, method: 'div'};
                }''')
                
                await asyncio.sleep(0.5)
                
                if result.get('success'):
                    logger.info(f"✅ Property Deductible Amount clicked: $2,500 (method: {result.get('method')})")
                else:
                    logger.warning(f"⚠️ JavaScript click returned: {result}")
                
                # Verify selection by checking multiple ways
                verification = await self.page.evaluate('''() => {
                    // Method 1: Check if input is checked
                    const input = document.getElementById('propertyDeductibleAmount_2500');
                    if (input && input.checked) {
                        return {verified: true, method: 'input_checked'};
                    }
                    
                    // Method 2: Check if the checkbox div has "checked" class
                    const optionDiv = document.getElementById('radio_propertyDeductibleAmount_2500');
                    if (optionDiv) {
                        const checkboxDiv = optionDiv.querySelector('.ui.radio.checkbox');
                        if (checkboxDiv && checkboxDiv.classList.contains('checked')) {
                            return {verified: true, method: 'checked_class'};
                        }
                    }
                    
                    // Method 3: Check what value is actually selected
                    const checkedInput = document.querySelector('input[name="propertyDeductibleAmount"]:checked');
                    if (checkedInput) {
                        const checkedId = checkedInput.id;
                        if (checkedId === 'propertyDeductibleAmount_2500') {
                            return {verified: true, method: 'checked_input_id', value: checkedId};
                        }
                        return {verified: false, method: 'wrong_selection', selectedId: checkedId};
                    }
                    
                    return {verified: false, method: 'no_selection'};
                }''')
                
                if verification.get('verified'):
                    logger.info(f"✅ Verified Property Deductible Amount selection: $2,500 (method: {verification.get('method')})")
                else:
                    logger.warning(f"⚠️ Could not verify Property Deductible Amount selection. Method: {verification.get('method')}, Details: {verification}")
                    # Try clicking again with a different approach
                    logger.info("Retrying Property Deductible Amount selection...")
                    await self.page.evaluate('''() => {
                        const label = document.querySelector('label[for="propertyDeductibleAmount_2500"]');
                        if (label) {
                            label.click();
                        }
                    }''')
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.warning(f"⚠️ Could not select Property Deductible Amount: {e}")
                screenshot_path = self.screenshot_dir / "error_property_deductible.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                # Don't raise - continue even if this fails
            
            # Fill Wind/Hail Deductible dropdown - Select $2,500
            logger.info("Selecting Wind/Hail Deductible: $2,500...")
            try:
                # Wait for Wind/Hail Deductible dropdown to be visible
                await self.page.wait_for_selector('label[for="windHailDeductible"], label:has-text("Wind/Hail Deductible")', timeout=10000, state="visible")
                await asyncio.sleep(0.5)
                
                # Use JavaScript to click the dropdown and select $2,500
                result = await self.page.evaluate('''() => {
                    // Find the Wind/Hail Deductible dropdown
                    const dropdown = document.getElementById('windHailDeductible');
                    if (!dropdown) {
                        return {success: false, message: 'Dropdown not found'};
                    }
                    
                    // Click to open the dropdown
                    dropdown.scrollIntoView({behavior: 'smooth', block: 'center'});
                    dropdown.click();
                    
                    return {success: true};
                }''')
                
                if result.get('success'):
                    logger.info("✅ Wind/Hail Deductible dropdown opened")
                    await asyncio.sleep(0.5)
                    
                    # Wait for the dropdown menu to appear and select $2,500
                    option_selected = await self.page.evaluate('''() => {
                        // Find the $2,500 option
                        const option = document.getElementById('windHailDeductible_2500');
                        if (option) {
                            option.scrollIntoView({behavior: 'smooth', block: 'center'});
                            option.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    if option_selected:
                        await asyncio.sleep(0.5)
                        logger.info("✅ Wind/Hail Deductible selected: $2,500")
                        
                        # Close the dropdown by pressing Enter or clicking inside the modal
                        logger.info("Closing Wind/Hail Deductible dropdown...")
                        try:
                            # Try pressing Enter first (this should close the dropdown)
                            await self.page.keyboard.press('Enter')
                            await asyncio.sleep(0.3)
                            
                            # Verify dropdown is closed by checking if menu is hidden
                            dropdown_closed = await self.page.evaluate('''() => {
                                const dropdown = document.getElementById('windHailDeductible');
                                if (dropdown) {
                                    const menu = dropdown.querySelector('.menu');
                                    if (menu) {
                                        // Check if menu is visible
                                        const style = window.getComputedStyle(menu);
                                        return style.display === 'none' || !menu.classList.contains('visible');
                                    }
                                    // Check aria-expanded
                                    return dropdown.getAttribute('aria-expanded') === 'false';
                                }
                                return true;
                            }''')
                            
                            if not dropdown_closed:
                                # If Enter didn't work, try clicking the dropdown again to close it
                                logger.info("Dropdown still open, clicking dropdown again to close...")
                                dropdown_element = self.page.locator('#windHailDeductible')
                                if await dropdown_element.count() > 0:
                                    await dropdown_element.click()
                                    await asyncio.sleep(0.3)
                                else:
                                    # Fallback: click on Gross Sales label (inside the modal)
                                    logger.info("Trying to click Gross Sales label to close dropdown...")
                                    gross_sales_label = self.page.locator('label[for="grossSales"]')
                                    if await gross_sales_label.count() > 0:
                                        await gross_sales_label.click()
                                        await asyncio.sleep(0.3)
                            
                            logger.info("✅ Wind/Hail Deductible dropdown closed")
                        except Exception as e:
                            logger.warning(f"⚠️ Could not close dropdown: {e}, continuing anyway...")
                        
                        # Verify selection
                        selected_text = await self.page.evaluate('''() => {
                            const dropdown = document.getElementById('windHailDeductible');
                            if (dropdown) {
                                const textDiv = dropdown.querySelector('.divider.text');
                                return textDiv ? textDiv.textContent.trim() : null;
                            }
                            return null;
                        }''')
                        
                        if selected_text and '2,500' in selected_text:
                            logger.info(f"✅ Verified Wind/Hail Deductible selection: {selected_text}")
                        else:
                            logger.warning(f"⚠️ Could not verify Wind/Hail Deductible selection. Got: {selected_text}")
                    else:
                        logger.warning("⚠️ Could not find $2,500 option in Wind/Hail Deductible dropdown")
                else:
                    logger.warning(f"⚠️ Could not open Wind/Hail Deductible dropdown: {result.get('message')}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not select Wind/Hail Deductible: {e}")
                screenshot_path = self.screenshot_dir / "error_wind_hail_deductible.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                # Don't raise - continue even if this fails
            
            # Fill Gross Sales input field
            logger.info("Filling Gross Sales...")
            gross_sales = self.quote_data.get('gross_sales', self.quote_data.get('gross_sales_amount', ''))
            if not gross_sales:
                # Default value if not provided
                gross_sales = "100000"
                logger.info(f"Using default Gross Sales: ${gross_sales}")
            
            try:
                # Wait for Gross Sales input to be visible
                await self.page.wait_for_selector('#grossSales, input[name="grossSales"]', timeout=10000, state="visible")
                await asyncio.sleep(0.5)
                
                # Fill the Gross Sales input
                gross_sales_input = self.page.locator('#grossSales').or_(self.page.locator('input[name="grossSales"]'))
                await gross_sales_input.wait_for(state="visible", timeout=10000)
                await gross_sales_input.scroll_into_view_if_needed()
                await asyncio.sleep(0.3)
                await gross_sales_input.click()
                await asyncio.sleep(0.3)
                await gross_sales_input.fill("")  # Clear any existing value
                await gross_sales_input.fill(gross_sales)
                await asyncio.sleep(0.5)
                
                # Verify it was filled (account for comma formatting)
                filled_value = await gross_sales_input.input_value()
                # Remove commas and compare
                filled_clean = filled_value.replace(',', '').replace('$', '').strip()
                gross_sales_clean = str(gross_sales).replace(',', '').replace('$', '').strip()
                if filled_clean == gross_sales_clean:
                    logger.info(f"✅ Gross Sales filled: ${filled_value}")
                else:
                    logger.warning(f"⚠️ Gross Sales value mismatch. Expected: {gross_sales}, Got: {filled_value}")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not fill Gross Sales: {e}")
                screenshot_path = self.screenshot_dir / "error_gross_sales.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                # Don't raise - continue even if this fails
            
            await asyncio.sleep(1)
            
            # Take screenshot after filling all fields
            screenshot_path = self.screenshot_dir / "18_location_info_filled.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # Click Next button on Location Information modal
            logger.info("Clicking Next button on Location Information modal...")
            try:
                await asyncio.sleep(1)
                
                # There are 2 Next buttons on the page - one in main content, one in modal
                # We need to click the one inside the modal form (has "Select information" text)
                button_clicked = False
                
                # Method 1: Target the Next button inside the modal form specifically
                try:
                    logger.info("Trying to click Next button inside modal form...")
                    # The modal form contains "Select information on this page"
                    modal_next = self.page.locator('form:has-text("Select information") button#Next')
                    if await modal_next.count() > 0:
                        await modal_next.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await modal_next.click(timeout=5000)
                        button_clicked = 'modal_form_next'
                        logger.info("✅ Clicked Next button inside modal form")
                except Exception as e:
                    logger.info(f"Modal form Next click failed: {e}")
                
                # Method 2: Use nth(1) to get the second Next button (modal's button)
                if not button_clicked:
                    try:
                        logger.info("Trying to click second Next button (modal)...")
                        next_btns = self.page.locator('button#Next')
                        count = await next_btns.count()
                        logger.info(f"Found {count} Next buttons")
                        if count >= 2:
                            # The second button is inside the modal
                            await next_btns.nth(1).scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await next_btns.nth(1).click(timeout=5000)
                            button_clicked = 'nth_1_next'
                            logger.info("✅ Clicked second Next button (nth=1)")
                    except Exception as e:
                        logger.info(f"nth(1) Next click failed: {e}")
                
                # Method 3: Click navigateRight inside modal
                if not button_clicked:
                    try:
                        logger.info("Trying to click navigateRight inside modal...")
                        modal_nav_right = self.page.locator('form:has-text("Select information") #navigateRight')
                        if await modal_nav_right.count() > 0:
                            await modal_nav_right.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await modal_nav_right.click(timeout=5000)
                            button_clicked = 'modal_navigateRight'
                            logger.info("✅ Clicked navigateRight inside modal")
                    except Exception as e:
                        logger.info(f"Modal navigateRight click failed: {e}")
                
                # Method 4: JavaScript to find and click the visible Next button in modal
                if not button_clicked:
                    try:
                        logger.info("Trying JavaScript to click modal Next button...")
                        result = await self.page.evaluate('''() => {
                            // Find all Next buttons and click the one that's inside the modal
                            const buttons = document.querySelectorAll('button#Next');
                            for (const btn of buttons) {
                                // Check if this button is inside a form with "Select information"
                                const form = btn.closest('form');
                                if (form && form.textContent.includes('Select information')) {
                                    btn.scrollIntoView({behavior: 'instant', block: 'center'});
                                    btn.click();
                                    return 'js_modal_next';
                                }
                            }
                            // Fallback: click the last Next button (usually the modal one)
                            if (buttons.length > 0) {
                                const lastBtn = buttons[buttons.length - 1];
                                lastBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                                lastBtn.click();
                                return 'js_last_next';
                            }
                            return false;
                        }''')
                        if result:
                            button_clicked = result
                            logger.info(f"✅ Clicked via JavaScript: {result}")
                    except Exception as e:
                        logger.info(f"JavaScript modal Next click failed: {e}")
                
                if not button_clicked:
                    raise Exception("Could not click Next button with any method")
                
                # Wait for navigation/modal change
                await asyncio.sleep(3)
                
                # Verify the modal actually changed - look for "New Building" or "Class Code" text
                logger.info("Verifying modal changed to New Building Information...")
                page_content = await self.page.content()
                if "New Building" in page_content or "Class Code" in page_content:
                    logger.info(f"✅ Next button clicked and modal changed (method: {button_clicked})")
                else:
                    logger.warning("⚠️ Modal may not have changed - still on Location Information?")
                    # Take a debug screenshot
                    screenshot_path = self.screenshot_dir / "debug_modal_not_changed.png"
                    await self.page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"Debug screenshot saved: {screenshot_path}")
                
                # Take screenshot after clicking Next
                screenshot_path = self.screenshot_dir / "19_after_location_next.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                logger.error(f"❌ Could not click Next button on Location Information modal: {e}")
                screenshot_path = self.screenshot_dir / "error_location_next.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # ================================================================
            # NEW BUILDING INFORMATION MODAL
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("NEW BUILDING INFORMATION MODAL")
            logger.info("=" * 80)
            
            # Wait for New Building Information modal to appear
            logger.info("Waiting for New Building Information modal to appear...")
            await asyncio.sleep(2)
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # Take screenshot of the modal
            screenshot_path = self.screenshot_dir / "20_building_info_modal.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # ----------------------------------------------------------------
            # Select "No" for "Is this building an ancillary or secondary building?"
            # ----------------------------------------------------------------
            logger.info("Selecting 'No' for ancillary/secondary building question...")
            try:
                ancillary_selectors = [
                    'input[id="ancillaryBuilding_N"]',
                    'input[name="ancillaryBuilding"][value="N"]',
                    'label[for="ancillaryBuilding_N"]',
                    '#radio_ancillaryBuilding_N',
                ]
                
                ancillary_selected = False
                for selector in ancillary_selectors:
                    try:
                        element = self.page.locator(selector).first
                        if await element.count() > 0:
                            await element.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            
                            # If it's a label, click directly; if input, click label
                            if 'label' in selector:
                                await element.click()
                            else:
                                # Try clicking the associated label
                                element_id = await element.get_attribute('id')
                                if element_id:
                                    label = self.page.locator(f'label[for="{element_id}"]')
                                    if await label.count() > 0:
                                        await label.click()
                                    else:
                                        await element.click(force=True)
                                else:
                                    await element.click(force=True)
                            
                            await asyncio.sleep(0.5)
                            ancillary_selected = True
                            logger.info(f"✅ Ancillary/Secondary Building 'No' selected (selector: {selector})")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not ancillary_selected:
                    # Fallback: JavaScript
                    result = await self.page.evaluate('''() => {
                        const inputs = document.querySelectorAll('input[name*="ancillary"], input[id*="ancillary"]');
                        for (const input of inputs) {
                            if (input.value === 'N' || input.id.includes('_N')) {
                                const label = document.querySelector(`label[for="${input.id}"]`);
                                if (label) { label.click(); return true; }
                                input.click();
                                return true;
                            }
                        }
                        return false;
                    }''')
                    if result:
                        ancillary_selected = True
                        logger.info("✅ Ancillary/Secondary Building 'No' selected (JavaScript)")
                
                if not ancillary_selected:
                    logger.warning("⚠️ Could not find ancillary building radio button")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select ancillary building option: {e}")
            
            # ----------------------------------------------------------------
            # Fill Class Code dropdown with "09321"
            # ----------------------------------------------------------------
            logger.info("Filling Class Code with: 09321...")
            try:
                # Wait for the modal to be fully loaded
                await asyncio.sleep(2)
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                
                # Find the Class Code dropdown - it's a search selection dropdown
                # Try multiple selectors - look for the search input in dropdowns
                class_code_selectors = [
                    '.ui.search.selection.dropdown input.search',
                    'input.search[type="text"]',
                    'input[name*="classCode"]',
                    'input[id*="classCode"]',
                ]
                
                class_code_filled = False
                for selector in class_code_selectors:
                    try:
                        class_code_input = self.page.locator(selector).first
                        if await class_code_input.count() > 0:
                            await class_code_input.wait_for(state="visible", timeout=5000)
                            await class_code_input.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await class_code_input.click()
                            await asyncio.sleep(0.3)
                            await class_code_input.fill("09321")
                            await asyncio.sleep(0.5)
                            # Press Enter to select
                            await class_code_input.press("Enter")
                            await asyncio.sleep(1)
                            logger.info(f"✅ Class Code filled: 09321 (selector: {selector})")
                            class_code_filled = True
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not class_code_filled:
                    # Fallback: Use JavaScript to find and fill
                    logger.info("Trying JavaScript method to fill Class Code...")
                    result = await self.page.evaluate('''() => {
                        // Find all search input fields in dropdowns
                        const inputs = document.querySelectorAll('.ui.search.selection.dropdown input.search');
                        for (const input of inputs) {
                            const label = input.closest('.field')?.querySelector('label');
                            if (label && (label.textContent.includes('Class Code') || label.getAttribute('for')?.includes('classCode'))) {
                                input.focus();
                                input.value = '09321';
                                input.dispatchEvent(new Event('input', { bubbles: true }));
                                input.dispatchEvent(new Event('change', { bubbles: true }));
                                // Trigger Enter key
                                const enterEvent = new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', bubbles: true });
                                input.dispatchEvent(enterEvent);
                                return true;
                            }
                        }
                        return false;
                    }''')
                    
                    if result:
                        await asyncio.sleep(1)
                        logger.info("✅ Class Code filled: 09321 (JavaScript method)")
                        class_code_filled = True
                
                if not class_code_filled:
                    raise Exception("Could not find or fill Class Code field")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not fill Class Code: {e}")
                screenshot_path = self.screenshot_dir / "error_class_code.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # Select "Yes" for "If the applicant is insuring the canopy is it listed as a separate building?"
            logger.info("Selecting 'Yes' for canopy separate building question...")
            try:
                # Wait for the radio button section to be visible
                await asyncio.sleep(1)
                
                # Find the "Yes" radio button for separateCanopy
                # Based on the image, the ID is "separateCanopy_Y"
                separate_canopy_selectors = [
                    'input[id="separateCanopy_Y"]',
                    'input[name="separateCanopy"][value="Y"]',
                    'label[for="separateCanopy_Y"]',
                    '#radio_separateCanopy_Y',
                ]
                
                option_selected = False
                for selector in separate_canopy_selectors:
                    try:
                        if selector.startswith('label'):
                            # Click the label
                            label = self.page.locator(selector).first
                            if await label.count() > 0:
                                await label.wait_for(state="visible", timeout=5000)
                                await label.scroll_into_view_if_needed()
                                await asyncio.sleep(0.3)
                                await label.click()
                                await asyncio.sleep(0.5)
                                logger.info(f"✅ Separate Canopy 'Yes' selected (method: label)")
                                option_selected = True
                                break
                        elif selector.startswith('#'):
                            # Click the radio option div
                            div = self.page.locator(selector).first
                            if await div.count() > 0:
                                await div.wait_for(state="visible", timeout=5000)
                                await div.scroll_into_view_if_needed()
                                await asyncio.sleep(0.3)
                                await div.click()
                                await asyncio.sleep(0.5)
                                logger.info(f"✅ Separate Canopy 'Yes' selected (method: div)")
                                option_selected = True
                                break
                        else:
                            # Click the input or find its label
                            input_elem = self.page.locator(selector).first
                            if await input_elem.count() > 0:
                                # Try to find associated label
                                label_for = await input_elem.get_attribute('id')
                                if label_for:
                                    label = self.page.locator(f'label[for="{label_for}"]').first
                                    if await label.count() > 0:
                                        await label.wait_for(state="visible", timeout=5000)
                                        await label.scroll_into_view_if_needed()
                                        await asyncio.sleep(0.3)
                                        await label.click()
                                        await asyncio.sleep(0.5)
                                        logger.info(f"✅ Separate Canopy 'Yes' selected (method: input->label)")
                                        option_selected = True
                                        break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not option_selected:
                    # Fallback: Use JavaScript
                    logger.info("Trying JavaScript method to select 'Yes'...")
                    result = await self.page.evaluate('''() => {
                        const input = document.getElementById('separateCanopy_Y');
                        if (input) {
                            const label = document.querySelector('label[for="separateCanopy_Y"]');
                            if (label) {
                                label.click();
                                return true;
                            }
                            input.click();
                            return true;
                        }
                        return false;
                    }''')
                    
                    if result:
                        await asyncio.sleep(0.5)
                        logger.info("✅ Separate Canopy 'Yes' selected (JavaScript method)")
                        option_selected = True
                
                if not option_selected:
                    raise Exception("Could not find or select 'Yes' for separate canopy question")
                
                # Verify selection
                is_selected = await self.page.evaluate('''() => {
                    const input = document.getElementById('separateCanopy_Y');
                    if (input && input.checked) {
                        return true;
                    }
                    const div = document.getElementById('radio_separateCanopy_Y');
                    if (div && div.querySelector('.checked')) {
                        return true;
                    }
                    return false;
                }''')
                
                if is_selected:
                    logger.info("✅ Verified Separate Canopy selection: Yes")
                else:
                    logger.warning("⚠️ Could not verify Separate Canopy selection")
                
            except Exception as e:
                logger.warning(f"⚠️ Could not select Separate Canopy 'Yes': {e}")
                screenshot_path = self.screenshot_dir / "error_separate_canopy.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # ----------------------------------------------------------------
            # Fill "Number Of Mortgagees/Loss Payees" with 0
            # ----------------------------------------------------------------
            logger.info("Filling Number Of Mortgagees/Loss Payees with: 0...")
            try:
                await asyncio.sleep(0.5)
                
                mortgagees_selectors = [
                    'input[id="numberOfMortgageesLossPayees"]',
                    'input[name="numberOfMortgageesLossPayees"]',
                    'input[id*="Mortgagees"]',
                    'input[name*="Mortgagees"]',
                ]
                
                mortgagees_filled = False
                for selector in mortgagees_selectors:
                    try:
                        input_elem = self.page.locator(selector).first
                        if await input_elem.count() > 0:
                            await input_elem.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await input_elem.click()
                            await input_elem.fill("0")
                            await asyncio.sleep(0.3)
                            mortgagees_filled = True
                            logger.info(f"✅ Number Of Mortgagees/Loss Payees filled: 0 (selector: {selector})")
                            break
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                if not mortgagees_filled:
                    # Fallback: JavaScript
                    result = await self.page.evaluate('''() => {
                        const input = document.getElementById('numberOfMortgageesLossPayees');
                        if (input) {
                            input.focus();
                            input.value = '0';
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            input.dispatchEvent(new Event('change', { bubbles: true }));
                            return true;
                        }
                        return false;
                    }''')
                    if result:
                        mortgagees_filled = True
                        logger.info("✅ Number Of Mortgagees/Loss Payees filled: 0 (JavaScript)")
                
                if not mortgagees_filled:
                    logger.warning("⚠️ Could not find Number Of Mortgagees/Loss Payees input")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not fill Number Of Mortgagees/Loss Payees: {e}")
            
            # ----------------------------------------------------------------
            # Select "No" for "Additional Interests"
            # ----------------------------------------------------------------
            logger.info("Selecting 'No' for Additional Interests...")
            try:
                await asyncio.sleep(0.3)
                
                additional_selected = False
                
                # Use JavaScript first - it's faster and more reliable
                result = await self.page.evaluate('''() => {
                    // Try clicking label directly - this is what works
                    const label = document.querySelector('label[for="additionalInsureds_N"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        label.click();
                        return 'label';
                    }
                    // Fallback: click input
                    const input = document.getElementById('additionalInsureds_N');
                    if (input) {
                        input.scrollIntoView({behavior: 'instant', block: 'center'});
                        input.click();
                        return 'input';
                    }
                    return false;
                }''')
                
                if result:
                    await asyncio.sleep(0.3)
                    additional_selected = True
                    logger.info(f"✅ Additional Interests 'No' selected (method: {result})")
                
                if not additional_selected:
                    logger.warning("⚠️ Could not find Additional Interests radio button")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select Additional Interests 'No': {e}")
            
            # ----------------------------------------------------------------
            # Select "Applicant is" radio button
            # Options: 
            #   1. "Owner and occupying over 90% of the building" (id="ownerOccupied_N1")
            #   2. "Owner and leasing the building to others" 
            #   3. "Tenant of the building" (id="ownerOccupied_N2")
            # Logic: If input contains "tenant" → select 3rd option (N2)
            #        If input contains "owner" → select 1st option (N1)
            # ----------------------------------------------------------------
            logger.info("Selecting 'Applicant is' radio button...")
            try:
                await asyncio.sleep(0.3)
                
                # Get the applicant type from quote_data (default to "tenant" if not provided)
                applicant_type = self.quote_data.get('applicant_is', self.quote_data.get('applicant_type', 'tenant')).lower()
                
                # Determine which radio button to select
                if 'tenant' in applicant_type:
                    # Select 3rd option: "Tenant of the building" (id="ownerOccupied_N2")
                    radio_id = "ownerOccupied_N2"
                    option_description = "Tenant of the building"
                elif 'owner' in applicant_type:
                    # Select 1st option: "Owner and occupying over 90% of the building" (id="ownerOccupied_N1")
                    radio_id = "ownerOccupied_N1"
                    option_description = "Owner and occupying over 90% of the building"
                else:
                    # Default to tenant if unclear
                    radio_id = "ownerOccupied_N2"
                    option_description = "Tenant of the building (default)"
                    logger.warning(f"⚠️ Unknown applicant type '{applicant_type}', defaulting to tenant")
                
                logger.info(f"Selecting '{option_description}' (id={radio_id})...")
                
                # Use JavaScript to click the label (faster and more reliable)
                result = await self.page.evaluate('''(radioId) => {
                    // Try clicking label directly
                    const label = document.querySelector('label[for="' + radioId + '"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        label.click();
                        return 'label';
                    }
                    // Fallback: click input
                    const input = document.getElementById(radioId);
                    if (input) {
                        input.scrollIntoView({behavior: 'instant', block: 'center'});
                        input.click();
                        return 'input';
                    }
                    return false;
                }''', radio_id)
                
                if result:
                    await asyncio.sleep(0.3)
                    logger.info(f"✅ Applicant is '{option_description}' selected (method: {result})")
                else:
                    logger.warning(f"⚠️ Could not find 'Applicant is' radio button (id={radio_id})")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select 'Applicant is' radio button: {e}")
            
            # ----------------------------------------------------------------
            # Fill "Original Construction Year"
            # ----------------------------------------------------------------
            logger.info("Filling Original Construction Year...")
            try:
                await asyncio.sleep(0.3)
                
                # Get construction year from quote_data (default to current year - 20 if not provided)
                construction_year = self.quote_data.get('construction_year', self.quote_data.get('original_construction_year', ''))
                if not construction_year:
                    from datetime import datetime
                    construction_year = str(datetime.now().year - 20)  # Default: 20 years ago
                    logger.info(f"Using default Construction Year: {construction_year}")
                
                try:
                    construction_year_input = self.page.locator('#constructionYear').first
                    if await construction_year_input.count() > 0:
                        await construction_year_input.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await construction_year_input.click()
                        await construction_year_input.fill(str(construction_year))
                        await asyncio.sleep(0.3)
                        logger.info(f"✅ Original Construction Year filled: {construction_year}")
                    else:
                        raise Exception("Construction Year input not found")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill Original Construction Year: {e}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error filling Original Construction Year: {e}")
            
            # ----------------------------------------------------------------
            # Select "Construction Type" - "Frame" (1st option, id="constructionType_01")
            # ----------------------------------------------------------------
            logger.info("Selecting 'Construction Type' - Frame (1st option)...")
            try:
                await asyncio.sleep(0.3)
                
                # Use JavaScript to click the label for Frame (1st option)
                result = await self.page.evaluate('''(radioId) => {
                    // Try clicking label directly
                    const label = document.querySelector('label[for="' + radioId + '"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        label.click();
                        return 'label';
                    }
                    // Fallback: click input
                    const input = document.getElementById(radioId);
                    if (input) {
                        input.scrollIntoView({behavior: 'instant', block: 'center'});
                        input.click();
                        return 'input';
                    }
                    return false;
                }''', 'constructionType_01')
                
                if result:
                    await asyncio.sleep(0.3)
                    logger.info(f"✅ Construction Type 'Frame' selected (method: {result})")
                else:
                    logger.warning("⚠️ Could not find Construction Type 'Frame' radio button")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select Construction Type 'Frame': {e}")
            
            # ----------------------------------------------------------------
            # Select "Roof Type" - "Other" (4th option, id="roofType_Other")
            # ----------------------------------------------------------------
            logger.info("Selecting 'Roof Type' - Other (4th option)...")
            try:
                await asyncio.sleep(0.3)
                
                # Use JavaScript to click the label for Other (4th option)
                result = await self.page.evaluate('''(radioId) => {
                    // Try clicking label directly
                    const label = document.querySelector('label[for="' + radioId + '"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        label.click();
                        return 'label';
                    }
                    // Fallback: click input
                    const input = document.getElementById(radioId);
                    if (input) {
                        input.scrollIntoView({behavior: 'instant', block: 'center'});
                        input.click();
                        return 'input';
                    }
                    return false;
                }''', 'roofType_Other')
                
                if result:
                    await asyncio.sleep(0.3)
                    logger.info(f"✅ Roof Type 'Other' selected (method: {result})")
                else:
                    logger.warning("⚠️ Could not find Roof Type 'Other' radio button")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select Roof Type 'Other': {e}")
            
            # ----------------------------------------------------------------
            # Fill "Number of Stories" with "1" (default)
            # ----------------------------------------------------------------
            logger.info("Filling Number of Stories with: 1...")
            try:
                await asyncio.sleep(0.3)
                
                # Get number of stories from quote_data (default to "1")
                # Handle empty string case - if empty or None, default to "1"
                number_of_stories = self.quote_data.get('number_of_stories') or self.quote_data.get('stories') or '1'
                # Ensure it's not an empty string after stripping whitespace
                if not str(number_of_stories).strip():
                    number_of_stories = '1'
                
                try:
                    stories_input = self.page.locator('#numberOfStories').first
                    if await stories_input.count() > 0:
                        await stories_input.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await stories_input.click()
                        await stories_input.fill(str(number_of_stories))
                        await asyncio.sleep(0.3)
                        logger.info(f"✅ Number of Stories filled: {number_of_stories}")
                    else:
                        raise Exception("Number of Stories input not found")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill Number of Stories: {e}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error filling Number of Stories: {e}")
            
            # ----------------------------------------------------------------
            # Fill "Square Footage" (above 3000, default: 3500)
            # ----------------------------------------------------------------
            logger.info("Filling Square Footage...")
            try:
                await asyncio.sleep(0.3)
                
                # Get square footage from quote_data (default to 3500 if not provided)
                square_footage = self.quote_data.get('square_footage', self.quote_data.get('square_feet', ''))
                if not square_footage:
                    square_footage = "3500"  # Default: above 3000
                    logger.info(f"Using default Square Footage: {square_footage}")
                
                try:
                    square_footage_input = self.page.locator('#squareFootage').first
                    if await square_footage_input.count() > 0:
                        await square_footage_input.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await square_footage_input.click()
                        await square_footage_input.fill(str(square_footage))
                        await asyncio.sleep(0.3)
                        logger.info(f"✅ Square Footage filled: {square_footage}")
                    else:
                        raise Exception("Square Footage input not found")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill Square Footage: {e}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error filling Square Footage: {e}")
            
            # ----------------------------------------------------------------
            # Select "Sprinkler" - "No" (id="sprinkler_N")
            # ----------------------------------------------------------------
            logger.info("Selecting 'Sprinkler' - No...")
            try:
                await asyncio.sleep(0.3)
                
                result = await self.page.evaluate('''(radioId) => {
                    const label = document.querySelector('label[for="' + radioId + '"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        label.click();
                        return 'label';
                    }
                    const input = document.getElementById(radioId);
                    if (input) {
                        input.scrollIntoView({behavior: 'instant', block: 'center'});
                        input.click();
                        return 'input';
                    }
                    return false;
                }''', 'sprinkler_N')
                
                if result:
                    await asyncio.sleep(0.3)
                    logger.info(f"✅ Sprinkler 'No' selected (method: {result})")
                else:
                    logger.warning("⚠️ Could not find Sprinkler 'No' radio button")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select Sprinkler 'No': {e}")
            
            # ----------------------------------------------------------------
            # Fill "Building Limit" - only if applicant is "owner"
            # ----------------------------------------------------------------
            applicant_type = self.quote_data.get('applicant_is', self.quote_data.get('applicant_type', 'tenant')).lower()
            if 'owner' in applicant_type:
                logger.info("Filling Building Limit (applicant is owner)...")
                try:
                    await asyncio.sleep(0.3)
                    
                    # Get building limit from quote_data (default to 500000 if not provided)
                    building_limit = self.quote_data.get('building_limit', self.quote_data.get('building_value', '500000'))
                    
                    try:
                        building_limit_input = self.page.locator('#buildingLimit').first
                        if await building_limit_input.count() > 0:
                            await building_limit_input.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await building_limit_input.click()
                            await building_limit_input.fill(str(building_limit))
                            await asyncio.sleep(0.3)
                            logger.info(f"✅ Building Limit filled: {building_limit}")
                        else:
                            raise Exception("Building Limit input not found")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not fill Building Limit: {e}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error filling Building Limit: {e}")
                
                # ----------------------------------------------------------------
                # Select "Building Valuation" - "Replacement Cost" (1st option, id="buildingValuation_1")
                # Only appears when applicant is owner
                # ----------------------------------------------------------------
                logger.info("Selecting 'Building Valuation' - Replacement Cost (1st option)...")
                try:
                    await asyncio.sleep(0.3)
                    
                    result = await self.page.evaluate('''(radioId) => {
                        const label = document.querySelector('label[for="' + radioId + '"]');
                        if (label) {
                            label.scrollIntoView({behavior: 'instant', block: 'center'});
                            label.click();
                            return 'label';
                        }
                        const input = document.getElementById(radioId);
                        if (input) {
                            input.scrollIntoView({behavior: 'instant', block: 'center'});
                            input.click();
                            return 'input';
                        }
                        return false;
                    }''', 'buildingValuation_1')
                    
                    if result:
                        await asyncio.sleep(0.3)
                        logger.info(f"✅ Building Valuation 'Replacement Cost' selected (method: {result})")
                    else:
                        logger.warning("⚠️ Could not find Building Valuation 'Replacement Cost' radio button")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Could not select Building Valuation 'Replacement Cost': {e}")
            else:
                logger.info("Skipping Building Limit and Building Valuation (applicant is tenant)")
            
            # ----------------------------------------------------------------
            # Fill "Business Personal Property Limit" (default: 70000)
            # ----------------------------------------------------------------
            logger.info("Filling Business Personal Property Limit...")
            try:
                await asyncio.sleep(0.3)
                
                # Get BPP limit from quote_data (default to 70000 if not provided)
                bpp_limit = self.quote_data.get('bpp_limit', self.quote_data.get('business_personal_property_limit', '70000'))
                
                try:
                    bpp_limit_input = self.page.locator('#bppLimit').first
                    if await bpp_limit_input.count() > 0:
                        await bpp_limit_input.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await bpp_limit_input.click()
                        await bpp_limit_input.fill(str(bpp_limit))
                        await asyncio.sleep(0.3)
                        logger.info(f"✅ Business Personal Property Limit filled: {bpp_limit}")
                    else:
                        raise Exception("BPP Limit input not found")
                except Exception as e:
                    logger.warning(f"⚠️ Could not fill Business Personal Property Limit: {e}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Error filling Business Personal Property Limit: {e}")
            
            # ----------------------------------------------------------------
            # Select "Earthquake Coverage" - "No" (id="earthquakeCoverage_N")
            # ----------------------------------------------------------------
            logger.info("Selecting 'Earthquake Coverage' - No...")
            try:
                await asyncio.sleep(0.3)
                
                result = await self.page.evaluate('''(radioId) => {
                    const label = document.querySelector('label[for="' + radioId + '"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        label.click();
                        return 'label';
                    }
                    const input = document.getElementById(radioId);
                    if (input) {
                        input.scrollIntoView({behavior: 'instant', block: 'center'});
                        input.click();
                        return 'input';
                    }
                    return false;
                }''', 'earthquakeCoverage_N')
                
                if result:
                    await asyncio.sleep(0.3)
                    logger.info(f"✅ Earthquake Coverage 'No' selected (method: {result})")
                else:
                    logger.warning("⚠️ Could not find Earthquake Coverage 'No' radio button")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select Earthquake Coverage 'No': {e}")
            
            # ----------------------------------------------------------------
            # Click Next button on the modal
            # ----------------------------------------------------------------
            logger.info("Clicking Next button on Building Information modal...")
            try:
                await asyncio.sleep(1)
                
                # Use the same approach as Location Information modal - target the Next button inside the modal form
                # There are 2 Next buttons on the page - one in main content, one in modal
                # We need to click the one inside the modal form (has "Select information" text)
                button_clicked = False
                
                # Method 1: Target the Next button inside the modal form specifically
                try:
                    logger.info("Trying to click Next button inside modal form...")
                    # The modal form contains "Select information on this page"
                    modal_next = self.page.locator('form:has-text("Select information") button#Next')
                    if await modal_next.count() > 0:
                        await modal_next.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await modal_next.click(timeout=5000)
                        button_clicked = 'modal_form_next'
                        logger.info("✅ Clicked Next button inside modal form")
                except Exception as e:
                    logger.info(f"Modal form Next click failed: {e}")
                
                # Method 2: Use nth(1) to get the second Next button (modal's button)
                if not button_clicked:
                    try:
                        logger.info("Trying to click second Next button (modal)...")
                        next_btns = self.page.locator('button#Next')
                        count = await next_btns.count()
                        logger.info(f"Found {count} Next buttons")
                        if count >= 2:
                            # The second button is inside the modal
                            await next_btns.nth(1).scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await next_btns.nth(1).click(timeout=5000)
                            button_clicked = 'nth_1_next'
                            logger.info("✅ Clicked second Next button (nth=1)")
                    except Exception as e:
                        logger.info(f"nth(1) Next click failed: {e}")
                
                # Method 3: Click navigateRight inside modal
                if not button_clicked:
                    try:
                        logger.info("Trying to click navigateRight inside modal...")
                        modal_nav_right = self.page.locator('form:has-text("Select information") #navigateRight')
                        if await modal_nav_right.count() > 0:
                            await modal_nav_right.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await modal_nav_right.click(timeout=5000)
                            button_clicked = 'modal_navigateRight'
                            logger.info("✅ Clicked navigateRight inside modal")
                    except Exception as e:
                        logger.info(f"Modal navigateRight click failed: {e}")
                
                # Method 4: JavaScript to find and click the visible Next button in modal
                if not button_clicked:
                    try:
                        logger.info("Trying JavaScript to click modal Next button...")
                        result = await self.page.evaluate('''() => {
                            // Find all Next buttons and click the one that's inside the modal
                            const buttons = document.querySelectorAll('button#Next');
                            for (const btn of buttons) {
                                // Check if this button is inside a form with "Select information"
                                const form = btn.closest('form');
                                if (form && form.textContent.includes('Select information')) {
                                    btn.scrollIntoView({behavior: 'instant', block: 'center'});
                                    btn.click();
                                    return 'js_modal_next';
                                }
                            }
                            // Fallback: click the last Next button (usually the modal one)
                            if (buttons.length > 0) {
                                const lastBtn = buttons[buttons.length - 1];
                                lastBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                                lastBtn.click();
                                return 'js_last_next';
                            }
                            return false;
                        }''')
                        if result:
                            button_clicked = result
                            logger.info(f"✅ Clicked via JavaScript: {result}")
                    except Exception as e:
                        logger.info(f"JavaScript modal Next click failed: {e}")
                
                if not button_clicked:
                    raise Exception("Could not click Next button with any method")
                
                # Wait for navigation/modal change
                await asyncio.sleep(3)
                
                # Verify the modal actually changed - look for next page content
                logger.info("Verifying modal/page changed...")
                page_content = await self.page.content()
                # Check if we've moved past the Building Information modal
                if "Building Information" not in page_content or len(page_content) < 50000:
                    logger.info(f"✅ Next button clicked and page changed (method: {button_clicked})")
                else:
                    logger.warning("⚠️ Page may not have changed - still on Building Information?")
                    # Take a debug screenshot
                    screenshot_path = self.screenshot_dir / "debug_building_next_not_changed.png"
                    await self.page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"Debug screenshot saved: {screenshot_path}")
                
            except Exception as e:
                logger.error(f"❌ Could not click Next button on Building Information modal: {e}")
                screenshot_path = self.screenshot_dir / "error_building_next.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # ================================================================
            # BUILDING QUESTIONS MODAL
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("BUILDING QUESTIONS MODAL")
            logger.info("=" * 80)
            
            # Wait for Building Questions modal to appear
            logger.info("Waiting for Building Questions modal to appear...")
            await asyncio.sleep(2)
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # Take screenshot of the modal
            screenshot_path = self.screenshot_dir / "22_building_questions_modal.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # ----------------------------------------------------------------
            # Select "I Agree" radio button (id="questions.reviewedCorrect_Y")
            # ----------------------------------------------------------------
            logger.info("Selecting 'I Agree' for Building Questions...")
            try:
                await asyncio.sleep(0.3)
                
                # Use JavaScript to click the label (faster and more reliable)
                result = await self.page.evaluate('''(radioId) => {
                    // Try clicking label directly
                    const label = document.querySelector('label[for="' + radioId + '"]');
                    if (label) {
                        label.scrollIntoView({behavior: 'instant', block: 'center'});
                        label.click();
                        return 'label';
                    }
                    // Fallback: click input
                    const input = document.getElementById(radioId);
                    if (input) {
                        input.scrollIntoView({behavior: 'instant', block: 'center'});
                        input.click();
                        return 'input';
                    }
                    return false;
                }''', 'questions.reviewedCorrect_Y')
                
                if result:
                    await asyncio.sleep(0.3)
                    logger.info(f"✅ 'I Agree' selected (method: {result})")
                else:
                    logger.warning("⚠️ Could not find 'I Agree' radio button")
                    
            except Exception as e:
                logger.warning(f"⚠️ Could not select 'I Agree': {e}")
            
            # ----------------------------------------------------------------
            # Click Next button on the Building Questions modal
            # ----------------------------------------------------------------
            logger.info("Clicking Next button on Building Questions modal...")
            try:
                await asyncio.sleep(1)
                
                # Use the same approach as other modals - target the Next button inside the modal form
                button_clicked = False
                
                # Method 1: Target the Next button inside the modal form specifically
                try:
                    logger.info("Trying to click Next button inside modal form...")
                    # The modal form contains "Select information on this page"
                    modal_next = self.page.locator('form:has-text("Select information") button#Next')
                    if await modal_next.count() > 0:
                        await modal_next.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await modal_next.click(timeout=5000)
                        button_clicked = 'modal_form_next'
                        logger.info("✅ Clicked Next button inside modal form")
                except Exception as e:
                    logger.info(f"Modal form Next click failed: {e}")
                
                # Method 2: Use nth(1) to get the second Next button (modal's button)
                if not button_clicked:
                    try:
                        logger.info("Trying to click second Next button (modal)...")
                        next_btns = self.page.locator('button#Next')
                        count = await next_btns.count()
                        logger.info(f"Found {count} Next buttons")
                        if count >= 2:
                            # The second button is inside the modal
                            await next_btns.nth(1).scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await next_btns.nth(1).click(timeout=5000)
                            button_clicked = 'nth_1_next'
                            logger.info("✅ Clicked second Next button (nth=1)")
                    except Exception as e:
                        logger.info(f"nth(1) Next click failed: {e}")
                
                # Method 3: Click navigateRight inside modal
                if not button_clicked:
                    try:
                        logger.info("Trying to click navigateRight inside modal...")
                        modal_nav_right = self.page.locator('form:has-text("Select information") #navigateRight')
                        if await modal_nav_right.count() > 0:
                            await modal_nav_right.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await modal_nav_right.click(timeout=5000)
                            button_clicked = 'modal_navigateRight'
                            logger.info("✅ Clicked navigateRight inside modal")
                    except Exception as e:
                        logger.info(f"Modal navigateRight click failed: {e}")
                
                # Method 4: JavaScript to find and click the visible Next button in modal
                if not button_clicked:
                    try:
                        logger.info("Trying JavaScript to click modal Next button...")
                        result = await self.page.evaluate('''() => {
                            // Find all Next buttons and click the one that's inside the modal
                            const buttons = document.querySelectorAll('button#Next');
                            for (const btn of buttons) {
                                // Check if this button is inside a form with "Select information"
                                const form = btn.closest('form');
                                if (form && form.textContent.includes('Select information')) {
                                    btn.scrollIntoView({behavior: 'instant', block: 'center'});
                                    btn.click();
                                    return 'js_modal_next';
                                }
                            }
                            // Fallback: click the last Next button (usually the modal one)
                            if (buttons.length > 0) {
                                const lastBtn = buttons[buttons.length - 1];
                                lastBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                                lastBtn.click();
                                return 'js_last_next';
                            }
                            return false;
                        }''')
                        if result:
                            button_clicked = result
                            logger.info(f"✅ Clicked via JavaScript: {result}")
                    except Exception as e:
                        logger.info(f"JavaScript modal Next click failed: {e}")
                
                if not button_clicked:
                    raise Exception("Could not click Next button with any method")
                
                # Wait for navigation/modal change
                await asyncio.sleep(3)
                logger.info(f"✅ Next button clicked on Building Questions modal (method: {button_clicked})")
                
            except Exception as e:
                logger.error(f"❌ Could not click Next button on Building Questions modal: {e}")
                screenshot_path = self.screenshot_dir / "error_building_questions_next.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # ================================================================
            # NEW BUILDING COVERAGE MODAL
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("NEW BUILDING COVERAGE MODAL")
            logger.info("=" * 80)
            
            # Wait for New Building Coverage modal to appear
            logger.info("Waiting for New Building Coverage modal to appear...")
            await asyncio.sleep(2)
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # Take screenshot of the modal
            screenshot_path = self.screenshot_dir / "23_building_coverage_modal.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # ----------------------------------------------------------------
            # Click Next button on the New Building Coverage modal
            # ----------------------------------------------------------------
            logger.info("Clicking Next button on New Building Coverage modal...")
            try:
                await asyncio.sleep(1)
                
                # Use the same approach as other modals
                button_clicked = False
                
                # Method 1: Target the Next button inside the modal form
                try:
                    logger.info("Trying to click Next button inside modal form...")
                    modal_next = self.page.locator('form:has-text("Select information") button#Next')
                    if await modal_next.count() > 0:
                        await modal_next.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await modal_next.click(timeout=5000)
                        button_clicked = 'modal_form_next'
                        logger.info("✅ Clicked Next button inside modal form")
                except Exception as e:
                    logger.info(f"Modal form Next click failed: {e}")
                
                # Method 2: Use nth(1) to get the second Next button (modal's button)
                if not button_clicked:
                    try:
                        logger.info("Trying to click second Next button (modal)...")
                        next_btns = self.page.locator('button#Next')
                        count = await next_btns.count()
                        logger.info(f"Found {count} Next buttons")
                        if count >= 2:
                            await next_btns.nth(1).scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await next_btns.nth(1).click(timeout=5000)
                            button_clicked = 'nth_1_next'
                            logger.info("✅ Clicked second Next button (nth=1)")
                    except Exception as e:
                        logger.info(f"nth(1) Next click failed: {e}")
                
                # Method 3: Click navigateRight inside modal
                if not button_clicked:
                    try:
                        logger.info("Trying to click navigateRight inside modal...")
                        modal_nav_right = self.page.locator('form:has-text("Select information") #navigateRight')
                        if await modal_nav_right.count() > 0:
                            await modal_nav_right.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await modal_nav_right.click(timeout=5000)
                            button_clicked = 'modal_navigateRight'
                            logger.info("✅ Clicked navigateRight inside modal")
                    except Exception as e:
                        logger.info(f"Modal navigateRight click failed: {e}")
                
                # Method 4: JavaScript fallback
                if not button_clicked:
                    try:
                        logger.info("Trying JavaScript to click modal Next button...")
                        result = await self.page.evaluate('''() => {
                            const buttons = document.querySelectorAll('button#Next');
                            for (const btn of buttons) {
                                const form = btn.closest('form');
                                if (form && form.textContent.includes('Select information')) {
                                    btn.scrollIntoView({behavior: 'instant', block: 'center'});
                                    btn.click();
                                    return 'js_modal_next';
                                }
                            }
                            if (buttons.length > 0) {
                                const lastBtn = buttons[buttons.length - 1];
                                lastBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                                lastBtn.click();
                                return 'js_last_next';
                            }
                            return false;
                        }''')
                        if result:
                            button_clicked = result
                            logger.info(f"✅ Clicked via JavaScript: {result}")
                    except Exception as e:
                        logger.info(f"JavaScript modal Next click failed: {e}")
                
                if not button_clicked:
                    raise Exception("Could not click Next button with any method")
                
                # Wait for navigation/modal change
                await asyncio.sleep(3)
                logger.info(f"✅ Next button clicked on New Building Coverage modal (method: {button_clicked})")
                
            except Exception as e:
                logger.error(f"❌ Could not click Next button on New Building Coverage modal: {e}")
                screenshot_path = self.screenshot_dir / "error_building_coverage_next.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            # ================================================================
            # LOCATION COVERAGES MODAL
            # ================================================================
            logger.info("\n" + "=" * 80)
            logger.info("LOCATION COVERAGES MODAL")
            logger.info("=" * 80)
            
            # Wait for Location Coverages modal to appear
            logger.info("Waiting for Location Coverages modal to appear...")
            await asyncio.sleep(2)
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # Take screenshot of the modal
            screenshot_path = self.screenshot_dir / "24_location_coverages_modal.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
            # ----------------------------------------------------------------
            # Click Done button on the Location Coverages modal
            # Done button is like Next but with id="Done"
            # ----------------------------------------------------------------
            logger.info("Clicking Done button on Location Coverages modal...")
            try:
                await asyncio.sleep(1)
                
                # Use the same approach as Next button but target "Done" button
                button_clicked = False
                
                # Method 1: Target the Done button inside the modal form
                try:
                    logger.info("Trying to click Done button inside modal form...")
                    modal_done = self.page.locator('form:has-text("Select information") button#Done')
                    if await modal_done.count() > 0:
                        await modal_done.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)
                        await modal_done.click(timeout=5000)
                        button_clicked = 'modal_form_done'
                        logger.info("✅ Clicked Done button inside modal form")
                except Exception as e:
                    logger.info(f"Modal form Done click failed: {e}")
                
                # Method 2: Use nth() to get the Done button in modal
                if not button_clicked:
                    try:
                        logger.info("Trying to click Done button (modal)...")
                        done_btns = self.page.locator('button#Done')
                        count = await done_btns.count()
                        logger.info(f"Found {count} Done buttons")
                        if count >= 1:
                            # If multiple, try the last one (usually the modal one)
                            target_btn = done_btns.nth(count - 1) if count > 1 else done_btns.first
                            await target_btn.scroll_into_view_if_needed()
                            await asyncio.sleep(0.3)
                            await target_btn.click(timeout=5000)
                            button_clicked = 'done_button'
                            logger.info("✅ Clicked Done button")
                    except Exception as e:
                        logger.info(f"Done button click failed: {e}")
                
                # Method 3: JavaScript fallback
                if not button_clicked:
                    try:
                        logger.info("Trying JavaScript to click modal Done button...")
                        result = await self.page.evaluate('''() => {
                            const buttons = document.querySelectorAll('button#Done');
                            for (const btn of buttons) {
                                const form = btn.closest('form');
                                if (form && form.textContent.includes('Select information')) {
                                    btn.scrollIntoView({behavior: 'instant', block: 'center'});
                                    btn.click();
                                    return 'js_modal_done';
                                }
                            }
                            if (buttons.length > 0) {
                                const lastBtn = buttons[buttons.length - 1];
                                lastBtn.scrollIntoView({behavior: 'instant', block: 'center'});
                                lastBtn.click();
                                return 'js_done';
                            }
                            return false;
                        }''')
                        if result:
                            button_clicked = result
                            logger.info(f"✅ Clicked via JavaScript: {result}")
                    except Exception as e:
                        logger.info(f"JavaScript modal Done click failed: {e}")
                
                if not button_clicked:
                    raise Exception("Could not click Done button with any method")
                
                # Wait for navigation/modal change
                await asyncio.sleep(3)
                logger.info(f"✅ Done button clicked on Location Coverages modal (method: {button_clicked})")
                
            except Exception as e:
                logger.error(f"❌ Could not click Done button on Location Coverages modal: {e}")
                screenshot_path = self.screenshot_dir / "error_location_coverages_done.png"
                await self.page.screenshot(path=str(screenshot_path), full_page=True)
                raise
            
            await asyncio.sleep(1)
            
            # Take screenshot after filling fields
            screenshot_path = self.screenshot_dir / "21_building_info_filled.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Screenshot saved: {screenshot_path}")
            
        except Exception as e:
            logger.error(f"❌ Error filling quote details: {e}", exc_info=True)
            screenshot_path = self.screenshot_dir / "error_quote_details.png"
            await self.page.screenshot(path=str(screenshot_path), full_page=True)
            raise
    
    async def run(self):
        """Run complete automation flow"""
        try:
            # Initialize browser
            await self.init_browser()
            
            # Login
            if not await self.login():
                raise Exception("Login failed")
            
            # Navigate to quote
            if not await self.navigate_to_quote():
                raise Exception("Navigation to quote page failed")
            
            # Fill quote details
            await self.fill_quote_details()
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ COLUMBIA AUTOMATION COMPLETE")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"❌ Automation error: {e}", exc_info=True)
            raise
        finally:
            await self.close()
    
    async def close(self):
        """Close browser, save trace, and cleanup (cookies are automatically saved by persistent context)"""
        logger.info("Closing browser...")
        try:
            # Stop and save trace if enabled (like Guard)
            if self.enable_tracing and self.context:
                logger.info(f"Stopping trace recording and saving to: {self.trace_path}")
                await self.context.tracing.stop(path=str(self.trace_path))
                
                # Verify trace file was created
                if self.trace_path.exists():
                    file_size = self.trace_path.stat().st_size
                    logger.info(f"✅ Trace saved successfully: {self.trace_path} ({file_size} bytes)")
                    logger.info(f"View trace with: playwright show-trace {self.trace_path}")
                else:
                    logger.warning(f"⚠️ Trace file not found at: {self.trace_path}")
            
            # With persistent context, we just close the context
            # Cookies and session data are automatically saved
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("✅ Browser closed - cookies and session saved to persistent storage")
        except Exception as e:
            logger.error(f"Error closing browser: {e}", exc_info=True)


async def main():
    """Main execution"""
    import sys
    
    task_id = "default"
    clear_session = "--clear" in sys.argv or "-c" in sys.argv
    
    automation = ColumbiaAutomation(
        task_id=task_id,
        clear_session=clear_session,  # Clear cookies/session if --clear flag is used
        person_entering_risk="John Doe",
        person_entering_risk_email="john.doe@example.com",
        company_name="Arish LLC",
        dba="SEERRA",  # Optional
        mailing_address="4964 lavista road tucker GA",
        applicant_is="owner",  # Test with owner - should select 1st option (Owner and occupying over 90%)
        # effective_date will be auto-calculated (today + 1 day) if not provided
    )
    
    await automation.run()


if __name__ == "__main__":
    asyncio.run(main())

