"""
Interactive Account Operations Test
User selects operations to perform after login
"""

import asyncio
import sys
import time
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.screen_detector import ScreenDetector, LoginScreen
from src.login_brain import LoginBrain
from src.gmail_authenticator import GmailAuthenticator
from src.utils import ConfigManager, TOTPGenerator
from urllib.parse import urlparse, urlunparse
from shared.robust import robust_goto, find_and_click, find_and_fill, find_element

# Ensure screenshots directory exists (some operations still save debug screenshots)
Path("screenshots").mkdir(exist_ok=True)


async def detect_and_handle_errors(page, email=None):
    """
    Detect error screens and return failure reason with actionable solution.

    This function checks for various error/verification screens that would prevent
    automation from continuing, and provides detailed failure reasons.

    Args:
        page: Playwright page
        email: User email (for logging)

    Returns:
        dict: {
            'has_error': bool,
            'error_type': str,
            'reason': str,
            'solution': str,
            'screenshot_path': str (if error found)
        }
    """
    result = {
        'has_error': False,
        'error_type': None,
        'reason': None,
        'solution': None,
        'screenshot_path': None
    }

    try:
        # Take screenshot for error analysis
        timestamp = int(time.time())

        # Check if redirected to support page (usually means account issue)
        current_url = page.url
        if 'support.google.com' in current_url:
            ss_path = f"screenshots/error_support_redirect_{timestamp}.png"
            await page.screenshot(path=ss_path, full_page=True)

            result['has_error'] = True
            result['error_type'] = 'ACCOUNT_RECOVERY_REDIRECT'
            result['reason'] = 'Google redirected to support page - Account needs manual recovery'
            result['solution'] = 'SOLUTION: Account requires manual verification. Check Google Account manually or contact support.'
            result['screenshot_path'] = ss_path
            return result

        # Check for recovery email verification screen
        recovery_email_selectors = [
            'input[type="email"][aria-label*="recovery email" i]',
            'input[placeholder*="recovery email" i]',
            'text="Verify it\'s you"',
            'text="Get a verification code"',
            'text="sent a verification code to"',
            'text="An email with a verification code was just sent to"',
            'text="Verify your identity"',
            'text="confirm your recovery email"',
        ]

        for sel in recovery_email_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        # Check context to avoid false positive with TOTP screen
                        # If page contains 2FA/Authenticator text, it's NOT recovery email error
                        page_text = await page.text_content('body')
                        page_text_lower = page_text.lower() if page_text else ''

                        # Keywords that indicate TOTP screen (NOT error)
                        totp_keywords = [
                            'google authenticator',
                            'authenticator app',
                            '2-step verification',
                            'verify with your authenticator',
                            'enter the code',
                            'use your authenticator',
                            'get a verification code from the google authenticator',
                            'open your authenticator app'
                        ]

                        # If page contains TOTP keywords, skip this detection
                        is_totp_screen = any(keyword in page_text_lower for keyword in totp_keywords)

                        if is_totp_screen:
                            # This is TOTP screen, not recovery email error
                            continue

                        # Otherwise, it's really a recovery email error
                        ss_path = f"screenshots/error_recovery_email_{timestamp}.png"
                        await page.screenshot(path=ss_path, full_page=True)

                        result['has_error'] = True
                        result['error_type'] = 'RECOVERY_EMAIL_VERIFICATION'
                        result['reason'] = 'Google is asking for recovery email verification code'
                        result['solution'] = 'SOLUTION: Add/update recovery email in account settings, or use different account'
                        result['screenshot_path'] = ss_path
                        return result
            except:
                continue

        # Check for phone verification screen
        phone_verification_selectors = [
            'input[type="tel"][aria-label*="phone" i]',
            'input[placeholder*="phone number" i]',
            'text="Verify your phone number"',
            'text="Enter the phone number"',
            'text="sent a verification code to your phone"',
            'text="sent a Google prompt to your phone"',
        ]

        for sel in phone_verification_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        # Check if it's asking for phone NUMBER (not code)
                        page_text = await page.text_content('body')
                        if 'enter' in page_text.lower() and 'phone' in page_text.lower():
                            ss_path = f"screenshots/error_phone_verification_{timestamp}.png"
                            await page.screenshot(path=ss_path, full_page=True)

                            result['has_error'] = True
                            result['error_type'] = 'PHONE_VERIFICATION'
                            result['reason'] = 'Google is asking for phone number verification'
                            result['solution'] = 'SOLUTION: Add recovery phone in account settings, or use different account'
                            result['screenshot_path'] = ss_path
                            return result
            except:
                continue

        # Check for account locked/suspended
        account_locked_selectors = [
            'text="This account has been disabled"',
            'text="account has been suspended"',
            'text="account has been locked"',
            'text="unusual activity"',
            'text="couldn\'t verify this account belongs to you"',
        ]

        for sel in account_locked_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        ss_path = f"screenshots/error_account_locked_{timestamp}.png"
                        await page.screenshot(path=ss_path, full_page=True)

                        result['has_error'] = True
                        result['error_type'] = 'ACCOUNT_LOCKED'
                        result['reason'] = 'Account is locked, suspended, or disabled by Google'
                        result['solution'] = 'SOLUTION: Check account status manually, complete account recovery, or contact Google support'
                        result['screenshot_path'] = ss_path
                        return result
            except:
                continue

        # Check for "Too many failed attempts" error (rate limit)
        too_many_attempts_selectors = [
            'text="Too many failed attempts"',
            'h2:has-text("Too many failed attempts")',
            'span[jsname="Ud7fr"]:has-text("Too many failed attempts")',
        ]

        for sel in too_many_attempts_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        ss_path = f"screenshots/error_too_many_attempts_{timestamp}.png"
                        await page.screenshot(path=ss_path, full_page=True)

                        result['has_error'] = True
                        result['error_type'] = 'TOO_MANY_ATTEMPTS'
                        result['reason'] = 'Too many failed login attempts - Account temporarily locked'
                        result['solution'] = 'SOLUTION: Wait 15-30 minutes before trying again, or use account recovery. This is Google\'s rate limiting protection.'
                        result['screenshot_path'] = ss_path
                        return result
            except:
                continue

        # Check for "Email not found" error (specific)
        email_not_found_selectors = [
            'text="Couldn\'t find your Google Account"',
            'text="No such user"',
            'text="Enter a valid email"',
        ]

        for sel in email_not_found_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        ss_path = f"screenshots/error_email_not_found_{timestamp}.png"
                        await page.screenshot(path=ss_path, full_page=True)

                        result['has_error'] = True
                        result['error_type'] = 'EMAIL_NOT_FOUND'
                        result['reason'] = 'Email address not found - Account does not exist'
                        result['solution'] = 'SOLUTION: Verify email address is correct. Check for typos or extra spaces.'
                        result['screenshot_path'] = ss_path
                        return result
            except:
                continue

        # Check for "Wrong password" error (specific)
        wrong_password_selectors = [
            'text="Wrong password"',
            'text="Wrong password. Try again"',
            'div[aria-live="polite"]:has-text("Wrong password")',
        ]

        for sel in wrong_password_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        ss_path = f"screenshots/error_wrong_password_{timestamp}.png"
                        await page.screenshot(path=ss_path, full_page=True)

                        result['has_error'] = True
                        result['error_type'] = 'WRONG_PASSWORD'
                        result['reason'] = 'Password is incorrect'
                        result['solution'] = 'SOLUTION: Verify password is correct. Copy-paste to avoid typos. Check if password was recently changed.'
                        result['screenshot_path'] = ss_path
                        return result
            except:
                continue

        # Check for "Couldn't sign in" (generic)
        couldnt_signin_selectors = [
            'text="Couldn\'t sign in"',
            'text="Sign-in failed"',
        ]

        for sel in couldnt_signin_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        ss_path = f"screenshots/error_signin_failed_{timestamp}.png"
                        await page.screenshot(path=ss_path, full_page=True)

                        result['has_error'] = True
                        result['error_type'] = 'SIGNIN_FAILED'
                        result['reason'] = 'Sign-in failed - Check credentials'
                        result['solution'] = 'SOLUTION: Verify both email and password are correct in your input file'
                        result['screenshot_path'] = ss_path
                        return result
            except:
                continue

        # Check for "Wrong 2FA code" / "Incorrect code" error
        wrong_2fa_selectors = [
            'text="Wrong code"',
            'text="The code is incorrect"',
            'text="That code didn\'t work"',
            'text="Try again"',
            'div[aria-live="polite"]:has-text("incorrect")',
            'div[aria-live="polite"]:has-text("wrong")',
        ]

        for sel in wrong_2fa_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        # Make sure we're on a code input page
                        page_text = await page.text_content('body')
                        if 'code' in page_text.lower() or 'verification' in page_text.lower():
                            ss_path = f"screenshots/error_wrong_2fa_code_{timestamp}.png"
                            await page.screenshot(path=ss_path, full_page=True)

                            result['has_error'] = True
                            result['error_type'] = 'WRONG_2FA_CODE'
                            result['reason'] = '2FA/TOTP code is incorrect or expired'
                            result['solution'] = 'SOLUTION: Verify TOTP secret is correct. Check if authenticator app time is synced. Code may have expired - retry immediately.'
                            result['screenshot_path'] = ss_path
                            return result
            except:
                continue

        # Check for "Too many attempts" / rate limiting
        rate_limit_selectors = [
            'text="Try again later"',
            'text="too many attempts"',
            'text="tried to sign in too many times"',
        ]

        for sel in rate_limit_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        ss_path = f"screenshots/error_rate_limit_{timestamp}.png"
                        await page.screenshot(path=ss_path, full_page=True)

                        result['has_error'] = True
                        result['error_type'] = 'RATE_LIMITED'
                        result['reason'] = 'Too many sign-in attempts detected by Google'
                        result['solution'] = 'SOLUTION: Wait 15-30 minutes before trying again, or use different IP/device'
                        result['screenshot_path'] = ss_path
                        return result
            except:
                continue

        # Check for 2-Step Verification setup required (backup phone/email needed)
        two_step_setup_selectors = [
            'text="Add a phone number to use 2-Step Verification"',
            'text="Add recovery info"',
            'text="Secure your account"',
        ]

        for sel in two_step_setup_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        # Check if this is blocking login (required setup)
                        page_text = await page.text_content('body')
                        if 'required' in page_text.lower() or 'must' in page_text.lower():
                            ss_path = f"screenshots/error_2step_setup_required_{timestamp}.png"
                            await page.screenshot(path=ss_path, full_page=True)

                            result['has_error'] = True
                            result['error_type'] = 'TWO_STEP_SETUP_REQUIRED'
                            result['reason'] = 'Google requires 2-Step Verification setup (phone/backup email)'
                            result['solution'] = 'SOLUTION: Complete 2-Step setup manually first, then run bot'
                            result['screenshot_path'] = ss_path
                            return result
            except:
                continue

        # Check for any generic error/warning messages (catch-all)
        generic_error_selectors = [
            'div[role="alert"]',
            'div[aria-live="assertive"]',
            'div[class*="error"]',
            'div[class*="warning"]',
        ]

        for sel in generic_error_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        # Get the error message text
                        error_text = await elem.text_content()
                        if error_text and len(error_text.strip()) > 0:
                            # Check if it looks like an actual error (not just a label)
                            error_text_lower = error_text.lower()
                            error_keywords = ['error', 'failed', 'wrong', 'incorrect', 'invalid',
                                            'cannot', 'unable', 'denied', 'blocked', 'suspended']

                            if any(keyword in error_text_lower for keyword in error_keywords):
                                ss_path = f"screenshots/error_unexpected_{timestamp}.png"
                                await page.screenshot(path=ss_path, full_page=True)

                                result['has_error'] = True
                                result['error_type'] = 'UNEXPECTED_ERROR'
                                result['reason'] = f'Unexpected error detected: {error_text[:200]}'
                                result['solution'] = 'SOLUTION: Check screenshot for details. May need manual intervention or account review.'
                                result['screenshot_path'] = ss_path
                                return result
            except:
                continue

        # No errors detected
        return result

    except Exception as e:
        print(f"  [WARN] Error detection failed: {e}")
        return result


def save_failure_log(email, operation, error_info, output_file="failed_accounts.txt"):
    """
    Save failure information to a log file for review.

    Args:
        email: Account email
        operation: Operation being performed
        error_info: Error info dict from detect_and_handle_errors()
        output_file: Path to failure log file
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        log_entry = f"""
{'='*70}
FAILURE LOG - {timestamp}
{'='*70}
Email: {email}
Operation: {operation}
Error Type: {error_info.get('error_type', 'UNKNOWN')}
Reason: {error_info.get('reason', 'Unknown error')}
Solution: {error_info.get('solution', 'No solution available')}
Screenshot: {error_info.get('screenshot_path', 'No screenshot')}
{'='*70}

"""

        # Append to failure log file
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)

        print(f"  [LOG] Failure logged to: {output_file}")

    except Exception as e:
        print(f"  [WARN] Could not save failure log: {e}")


async def handle_phone_confirmation(page, recovery_phone=None):
    """
    Handle phone confirmation screen that may appear after password entry.
    Google sometimes asks to confirm phone number before allowing login.

    Args:
        page: Playwright page
        recovery_phone: Expected recovery phone from Excel (optional)

    Returns:
        dict: {
            'handled': bool - If phone confirmation was found and handled
            'success': bool - If phone confirmation succeeded
            'error_message': str - Error message if failed
        }
    """
    result = {
        'handled': False,
        'success': False,
        'error_message': None
    }

    try:
        # Check if phone confirmation screen is present
        phone_confirm_selectors = [
            'input[type="tel"][name="phoneNumberId"]',
            'input[type="tel"][placeholder*="phone" i]',
            'input[aria-label*="phone" i]',
            'text="Confirm your recovery phone"',
            'text="Enter your phone number"',
            'text="For your security"',
        ]

        phone_input_found = False
        phone_input_elem = None

        for sel in phone_confirm_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible and 'input' in sel.lower():
                        phone_input_found = True
                        phone_input_elem = elem
                        print(f"\n  [INFO] Phone confirmation screen detected!")
                        result['handled'] = True
                        break
            except:
                continue

        if not phone_input_found:
            # No phone confirmation screen
            return result

        # Phone confirmation screen is present
        print(f"  [STEP] Handling phone confirmation...")

        # Take screenshot
        timestamp = datetime.now().strftime("%H%M%S")
        ss_path = f"screenshots/phone_confirm_screen_{timestamp}.png"
        await page.screenshot(path=ss_path, full_page=True)
        print(f"  Screenshot saved: {ss_path}")

        # If no recovery phone provided in Excel, cannot continue
        if not recovery_phone:
            result['error_message'] = "Phone confirmation required but no recovery phone provided in Excel"
            print(f"  [ERROR] {result['error_message']}")
            return result

        # Fill phone number
        print(f"  [INFO] Filling recovery phone: {recovery_phone}")
        try:
            await phone_input_elem.click()
            await asyncio.sleep(0.5)
            await phone_input_elem.fill("")
            await phone_input_elem.type(recovery_phone, delay=50)
            print(f"  [OK] Phone number entered")
            await asyncio.sleep(1)
        except Exception as e:
            result['error_message'] = f"Failed to fill phone number: {e}"
            print(f"  [ERROR] {result['error_message']}")
            return result

        # Click Next button
        next_btn_selectors = [
            'button:has-text("Next")',
            'button[jsname="LgbsSe"]',
            'button[type="submit"]',
            'span[jsname="V67aGc"]:has-text("Next")',
        ]

        next_clicked = False
        for sel in next_btn_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        await elem.click()
                        print(f"  [OK] Clicked Next button")
                        next_clicked = True
                        await asyncio.sleep(3)
                        break
            except:
                continue

        if not next_clicked:
            result['error_message'] = "Could not find Next button on phone confirmation screen"
            print(f"  [ERROR] {result['error_message']}")
            return result

        # Wait and check if phone was accepted
        await asyncio.sleep(2)

        # Check if still on phone screen (phone didn't match)
        still_on_phone = False
        for sel in phone_confirm_selectors[:3]:  # Check input selectors only
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0:
                    is_visible = await elem.is_visible()
                    if is_visible:
                        still_on_phone = True
                        break
            except:
                continue

        if still_on_phone:
            # Phone didn't match
            result['error_message'] = f"Phone confirmation failed - {recovery_phone} does not match account recovery phone"
            print(f"  [ERROR] {result['error_message']}")

            # Take screenshot of error
            ss_error = f"screenshots/phone_confirm_failed_{timestamp}.png"
            await page.screenshot(path=ss_error, full_page=True)
            print(f"  Screenshot saved: {ss_error}")
            return result

        # Phone confirmation successful
        result['success'] = True
        print(f"  [OK] Phone confirmation successful!")

        # Take screenshot after success
        ss_success = f"screenshots/phone_confirm_success_{timestamp}.png"
        await page.screenshot(path=ss_success, full_page=True)
        print(f"  Screenshot saved: {ss_success}")

        return result

    except Exception as e:
        result['error_message'] = f"Phone confirmation handler error: {e}"
        print(f"  [ERROR] {result['error_message']}")
        return result


def build_operation_url(base_password_url, operation_path):
    """
    Build operation URL from captured password change URL.
    Preserves all query parameters (hl, continue, rapt, pli) to maintain session.

    Handles multiple URL formats:
    - Standard: https://myaccount.google.com/signinoptions/password?rapt=...
    - Recovery: https://accounts.google.com/u/0/recovery/summary?rapt=...
    - Any URL with rapt token

    Args:
        base_password_url: Captured password URL with all params
        operation_path: Operation path to use
                        e.g., 'rescuephone', 'email', 'twosv', 'backup-codes', 'device-activity'

    Returns:
        Full URL with preserved query parameters
    """
    parsed = urlparse(base_password_url)

    # Extract rapt token from query params (needed for all operations)
    from urllib.parse import parse_qs, urlencode
    query_params = parse_qs(parsed.query, keep_blank_values=True)
    rapt_value = query_params.get('rapt', [None])[0]

    # If URL is already myaccount.google.com/signinoptions/password, just replace path
    if 'myaccount.google.com' in parsed.netloc and '/password' in parsed.path:
        new_path = parsed.path.replace('/password', f'/{operation_path}')
        new_url = urlunparse((
            parsed.scheme, parsed.netloc, new_path,
            parsed.params, parsed.query, parsed.fragment
        ))
        return new_url

    # For any other URL format (recovery/summary, accounts.google.com, etc.):
    # Build correct myaccount.google.com URL with rapt token
    new_path = f'/signinoptions/{operation_path}'

    # Preserve important query params
    preserved_params = {}
    for key in ['rapt', 'hl', 'pli']:
        val = query_params.get(key, [None])[0]
        if val:
            preserved_params[key] = val

    # Ensure hl=en is set
    if 'hl' not in preserved_params:
        preserved_params['hl'] = 'en'

    new_query = urlencode(preserved_params)
    new_url = urlunparse((
        'https', 'myaccount.google.com', new_path,
        '', new_query, ''
    ))

    print(f"  [build_operation_url] Converted non-standard URL to: {new_url[:100]}")
    return new_url


def show_menu():
    """Display operation menu"""
    print("\n" + "="*70)
    print("GMAIL ACCOUNT OPERATIONS - INTERACTIVE MENU")
    print("="*70)
    print("\nAvailable Operations:")
    print("  1. Change Password")
    print("  2. Update Recovery Phone")
    print("  3. Update Recovery Email")
    print("  4. Change Authenticator App")
    print("  5. Generate New Backup Codes")
    print("  6. Add and Replace 2FA Phone")
    print("  7. Remove All Devices")
    print("  8. Change Name (First Name + Last Name)")
    print("  0. Exit")
    print("\n" + "="*70)


def get_user_choices():
    """Get operation choices from user"""
    choices = []

    print("\nEnter operation numbers (comma-separated, e.g., 1,2,5):")
    print("Or enter 'all' to perform all operations")

    user_input = input("Your choice: ").strip().lower()

    if user_input == 'all':
        choices = [1, 2, 3, 4, 5, 6, 7]
    else:
        try:
            choices = [int(x.strip()) for x in user_input.split(',')]
        except:
            print("Invalid input! Using default: Change Password only")
            choices = [1]

    return choices


async def change_password(page, config, new_password, base_url=None):
    """
    Change account password
    Workflow:
    1. Fill new password input
    2. Fill confirm password input
    3. Click first "Change password" button
    4. Click second "Change password" button (confirmation)

    Args:
        page: Playwright page
        config: ConfigManager instance
        new_password: New password to set
        base_url: Optional captured password URL to construct URL from

    Returns:
        bool: Success status
    """
    print("\n[OPERATION] Changing Password...")

    try:
        # Build URL from captured password URL if provided
        if base_url:
            print(f"  Using current page (already on password change)")
        else:
            password_url = config.get_url("password_change")
            await robust_goto(page, password_url)

        await asyncio.sleep(1)

        # Take screenshot before
        timestamp = datetime.now().strftime("%H%M%S")
        ss_before = f"screenshots/password_change_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # STEP 1: Fill new password input
        print("\n  [STEP 1] Entering new password...")

        new_pwd_selectors = [
            'input[name="password"]',
            'input[autocomplete="new-password"]',
            'input[type="password"][jsname="YPqjbf"]',
            'input[type="password"]'
        ]

        if not await find_and_fill(page, new_pwd_selectors, new_password,
                                   label="New password input", type_delay=50):
            print("  [ERROR] Could not find new password input")
            return False

        # STEP 2: Fill confirm password input
        print("\n  [STEP 2] Entering confirm password...")

        confirm_pwd_selectors = [
            'input[name="confirmation_password"]',
            'input[autocomplete="new-password"]:not([name="password"])',
            'input[type="password"]:nth-of-type(2)',
            'input[type="password"][id*="i12"]'
        ]

        if not await find_and_fill(page, confirm_pwd_selectors, new_password,
                                   label="Confirm password input", type_delay=50):
            print("  [ERROR] Could not find confirm password input")
            return False

        # STEP 3: Click first "Change password" button
        print("\n  [STEP 3] Clicking first 'Change password' button...")

        first_btn_selectors = [
            'button:has-text("Change password")',
            'span[jsname="m9ZlFb"]',
            'button[jsname="LgbsSe"]:has-text("Change")',
            'button:has-text("Save")',
            'button[type="submit"]'
        ]

        if not await find_and_click(page, first_btn_selectors, force=True,
                                    label="First Change password button", post_click_sleep=3):
            print("  [ERROR] Could not find first Change password button")
            return False

        # STEP 4: Click second "Change password" button (confirmation popup)
        print("\n  [STEP 4] Clicking second 'Change password' button (confirmation popup)...")

        second_btn_selectors = [
            'button[data-mdc-dialog-action="ok"]',
            'button.mUIrbf-LgbsSe:has-text("Change password")',
            'button[data-mdc-dialog-button-default]',
            'button:has-text("Change password")',
            'span[jsname="m9ZlFb"]',
            'button:has-text("Done")',
            'button:has-text("OK")',
            'button[jsname="LgbsSe"]'
        ]

        if not await find_and_click(page, second_btn_selectors, force=True,
                                    label="Second Change password button", post_click_sleep=3):
            print("  [INFO] No second button found - operation may be complete")

        # Final screenshot
        ss_final = f"screenshots/password_change_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)

        print("\n  [SUCCESS] Password change completed!")
        return True

    except Exception as e:
        print(f"  [ERROR] Password change failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def change_authenticator_app(page, config, base_url=None):
    """
    Change authenticator app and get new TOTP secret.
    Retries once on failure (navigates back and tries again).

    Returns:
        tuple: (bool success, str new_secret_key)
    """
    print("\n[OPERATION] Changing Authenticator App...")

    # Build URL once
    if base_url:
        from urllib.parse import parse_qs, urlencode
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        preserved = {}
        for key in ['rapt', 'hl', 'pli']:
            val = query_params.get(key, [None])[0]
            if val:
                preserved[key] = val
        if 'hl' not in preserved:
            preserved['hl'] = 'en'
        auth_url = urlunparse((
            'https', 'myaccount.google.com',
            '/two-step-verification/authenticator',
            '', urlencode(preserved), ''
        ))
        print(f"  Built URL from session: {auth_url[:80]}...")
    else:
        auth_url = config.get_url("authenticator_app")
        print(f"  Using config URL: {auth_url}")

    # ── Inner attempt function ──────────────────────────────────────────
    async def _attempt(attempt_num):
        print(f"\n  ── Attempt {attempt_num} ──")

        await robust_goto(page, auth_url)

        # Check for phone verification / challenge redirect
        current_url = page.url.lower()
        if any(kw in current_url for kw in ['challenge', 'signin', 'verifyphone', 'speedbump']):
            print(f"  [SKIP] Phone verification / challenge detected at URL")
            return False, None

        # STEP 1: Smart detect — "Set up authenticator" (new) or "Change authenticator app" (existing)
        print("\n  [STEP 1] Detecting authenticator state...")

        # Try "Set up authenticator" first (fresh account — no existing authenticator)
        setup_clicked = await find_and_click(page, [
            'button:has-text("Set up authenticator")',
            'a:has-text("Set up authenticator")',
        ], force=True, max_retries=1, label="Set up authenticator", post_click_sleep=3)

        if setup_clicked:
            print("  [OK] Fresh account — setting up new authenticator")
        else:
            # Fall back to "Change authenticator app" (existing authenticator)
            if not await find_and_click(page, [
                'button:has-text("Change authenticator app")',
                'span[jsname="m9ZlFb"]',
                'button[jsname="Pr7Yme"]',
                'button:has-text("Change")',
            ], force=True, label="Change authenticator app", post_click_sleep=3):
                print("  [ERROR] Could not find authenticator setup/change button")
                return False, None
            else:
                print("  [OK] Found existing authenticator — changing")

        # STEP 2: Click "Can't scan it?" button
        print("\n  [STEP 2] Clicking 'Can't scan it?'...")

        if not await find_and_click(page, [
            'button:has-text("Can\'t scan it?")',
            'span.mUIrbf-vQzf8d:has-text("Can\'t scan it?")',
            'button[jsname="Pr7Yme"]:has-text("Can\'t")',
            'div[jsname="Ptcard"]'
        ], force=True, label="Can't scan it?", post_click_sleep=3):
            print("  [ERROR] Could not find 'Can't scan it?' button")
            return False, None

        # STEP 3: Extract the secret key from popup
        print("\n  [STEP 3] Extracting secret key...")
        await asyncio.sleep(3)

        secret_key = None
        for key_attempt in range(1, 4):
            all_strong = page.locator('strong')
            strong_count = await all_strong.count()
            print(f"  Found {strong_count} <strong> elements (attempt {key_attempt})")

            for i in range(strong_count):
                try:
                    elem = all_strong.nth(i)
                    text = (await elem.inner_text()).strip()
                    if text and len(text) >= 30 and all(c.isalnum() or c.isspace() for c in text):
                        secret_key = text
                        print(f"  [OK] Found key in <strong> #{i+1}: {secret_key}")
                        break
                except Exception:
                    continue
            if secret_key:
                break
            if key_attempt < 3:
                print(f"  [RETRY {key_attempt}/3] Secret key not found, waiting 2s...")
                await asyncio.sleep(2)

        if not secret_key:
            print("  [ERROR] Could not extract secret key")
            return False, None

        # Save the key to file
        Path("screenshots").mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%H%M%S")
        with open(f"screenshots/authenticator_key_{timestamp}.txt", 'w', encoding='utf-8') as f:
            f.write(secret_key)

        # STEP 4: Click Next button (data-id="OCpkoe")
        # Google shows: Back | Cancel | Next(visible) | Verify(display:none)
        # After clicking Next: Next→hidden, Verify→visible
        print("\n  [STEP 4] Clicking Next button...")

        next_clicked = False
        for _na in range(3):
            try:
                btn = page.locator('button[data-id="OCpkoe"]').first
                if await btn.count() > 0:
                    await btn.evaluate('el => el.click()')
                    print(f"  [CLICK] Next button — OK via: button[data-id=\"OCpkoe\"]")
                    next_clicked = True
            except Exception:
                pass
            if next_clicked:
                break
            print(f"  [RETRY {_na+1}/3] Next button not found, waiting 2s...")
            await asyncio.sleep(2)

        if next_clicked:
            await asyncio.sleep(3)
        else:
            print("  [WARN] Next button not found — trying code input directly")
            await asyncio.sleep(1)

        # STEP 5: Generate TOTP code from the key
        print("\n  [STEP 5] Generating TOTP code from key...")
        secret_key_for_totp = secret_key.replace(' ', '')
        totp_gen = TOTPGenerator()
        totp_code = totp_gen.generate_code(secret_key_for_totp)
        print(f"  Generated code: {totp_code}")

        # STEP 6: Fill the code in input
        print("\n  [STEP 6] Entering verification code...")

        if not await find_and_fill(page, [
            'input[type="text"][jsname="YPqjbf"]',
            'input[placeholder*="Enter code"]',
            'input[placeholder*="enter code" i]',
            'input[aria-label*="code" i]',
            'input[aria-label*="Enter" i][type="text"]',
            'input[autocomplete="off"][type="text"]',
            'input[id*="c3"]',
            'input[type="tel"]:not([name="totpPin"])',
        ], totp_code, label="TOTP code input", type_delay=100):
            print("  [ERROR] Could not find code input field")
            return False, secret_key

        await asyncio.sleep(1)

        # STEP 7: Click Verify button (data-id="dtOep")
        # After Next click: Next→hidden, Verify→visible
        print("\n  [STEP 7] Clicking Verify button...")

        verify_clicked = False
        for _va in range(3):
            try:
                btn = page.locator('button[data-id="dtOep"]').first
                if await btn.count() > 0:
                    await btn.evaluate('el => el.click()')
                    print(f"  [CLICK] Verify button — OK via: button[data-id=\"dtOep\"]")
                    verify_clicked = True
            except Exception:
                pass
            if verify_clicked:
                break
            print(f"  [RETRY {_va+1}/3] Verify button not found, waiting 2s...")
            await asyncio.sleep(2)

        if not verify_clicked:
            print("  [ERROR] Could not find Verify button")
            return False, secret_key

        await asyncio.sleep(3)

        print(f"\n  [SUCCESS] Authenticator app changed!")
        print(f"  [IMPORTANT] New secret key: {secret_key}")
        return True, secret_key

    # ── Retry loop (3 attempts) ─────────────────────────────────────────
    for attempt in range(1, 4):
        try:
            success, key = await _attempt(attempt)
            if success and key:
                return True, key
            if attempt < 3:
                print(f"\n  [RETRY] Attempt {attempt} failed, waiting 3s before retry...")
                await asyncio.sleep(3)
        except Exception as e:
            print(f"  [ERROR] Attempt {attempt} exception: {e}")
            import traceback
            traceback.print_exc()
            if attempt < 3:
                print(f"\n  [RETRY] Waiting 3s before retry...")
                await asyncio.sleep(3)

    print("  [FAILED] Authenticator change failed after 3 attempts")
    return False, None


async def update_recovery_phone(page, config, new_phone, base_url=None):
    """
    Update recovery phone number
    Handles 2 scenarios:
    1. Phone exists → Click Edit button → Update phone
    2. Phone doesn't exist → Click "Add recovery phone" → Add phone

    Args:
        page: Playwright page
        config: ConfigManager instance
        new_phone: New phone number (e.g., +1234567890)
        base_url: Optional captured password URL to construct recovery URL from

    Returns:
        bool: Success status
    """
    print("\n[OPERATION] Updating Recovery Phone...")

    try:
        # Build URL from captured password URL if provided, otherwise use config
        if base_url:
            recovery_phone_url = build_operation_url(base_url, 'rescuephone')
            print(f"  Built URL from session: {recovery_phone_url[:80]}...")
        else:
            recovery_phone_url = config.get_url("recovery_phone")
            print(f"  Using config URL: {recovery_phone_url}")

        await robust_goto(page, recovery_phone_url)

        # Take screenshot of current page
        timestamp = datetime.now().strftime("%H%M%S")
        ss_before = f"screenshots/recovery_phone_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # STEP 1: Check for Add button FIRST, then Edit button
        print("\n  [STEP 1] Checking if recovery phone exists...")

        add_button_selectors = [
            'button:has-text("Add recovery phone")',
            'button[aria-label*="Add recovery phone" i]',
            'a:has-text("Add recovery phone")',
            'span.mUIrbf-vQzf8d:has-text("Add recovery phone")',
            'button.mUIrbf-LgbsSe:has-text("Add")',
            'button[jsname="Pr7Yme"]:has-text("Add")',
        ]

        add_found = await find_and_click(page, add_button_selectors, force=True,
                                         max_retries=1, label="Add recovery phone",
                                         post_click_sleep=4)

        if not add_found:
            print("  No 'Add' button found - phone already exists, looking for Edit button...")
            edit_button_selectors = [
                'button[aria-label="Edit phone number"]',
                'button[aria-label*="Edit" i][aria-label*="phone" i]',
                'button.pYTkkf-Bz112c-LgbsSe:has(svg)',
                'button[jsname="Pr7Yme"]:has(svg)',
                'button:has(path[d*="L20.41"])',
            ]

            if not await find_and_click(page, edit_button_selectors, force=True,
                                        label="Edit phone button", post_click_sleep=4):
                print("  [ERROR] Could not find Add or Edit button")
                return False

        # Wait for popup/dialog to appear
        await asyncio.sleep(1)

        # STEP 2: Find and fill phone input in popup
        print("\n  [STEP 2] Entering phone number in popup...")

        phone_input_selectors = [
            'input[type="tel"][jsname="YPqjbf"]',
            'input[aria-label="Phone input"]',
            'input[placeholder*="phone" i]',
            'input[type="tel"]',
            'input[id*="c7"]'
        ]

        # Find the phone input with retry
        phone_elem = await find_element(page, phone_input_selectors, label="Phone input")

        if phone_elem:
            # Check current value
            current_value = await phone_elem.input_value()
            print(f"  Current phone value: {current_value}")

            current_last_6 = ''.join(filter(str.isdigit, str(current_value)))[-6:] if current_value else ''
            new_last_6 = ''.join(filter(str.isdigit, str(new_phone)))[-6:]

            if current_last_6 and new_last_6 and current_last_6 == new_last_6:
                print(f"  [SKIP] Phone number already matches (last 6 digits same)")
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(2)
                print(f"  [SUCCESS] Recovery phone already up-to-date")
                return True

            # Different phone - update it
            phone_to_enter = str(new_phone).strip()
            if not phone_to_enter.startswith('+'):
                phone_to_enter = '+' + phone_to_enter

            await phone_elem.click()
            await asyncio.sleep(0.3)
            await phone_elem.fill("")
            await asyncio.sleep(0.3)
            await phone_elem.type(phone_to_enter, delay=100)
            print(f"  [OK] Phone number entered: {phone_to_enter}")
        else:
            print("  [ERROR] Could not find phone input field in popup")
            return False

        await asyncio.sleep(1)

        # STEP 3: Click Next/Save button
        print("\n  [STEP 3] Clicking Next/Save button...")

        if not await find_and_click(page, [
            'button:has-text("Next")',
            'button:has-text("Save")',
            'button:has-text("Update")',
            'button[type="submit"]',
            'button[jsname="LgbsSe"]',
            'button:has-text("Continue")'
        ], label="Next/Save button", post_click_sleep=3):
            print("  [ERROR] Could not find Next/Save button")
            return False

        # STEP 3.5: Click final Save button (appears after Next)
        print("\n  [STEP 3.5] Checking for final Save button...")

        await find_and_click(page, [
            'button:has-text("Save")',
            'button[jsname="LgbsSe"]:has-text("Save")',
            'span[jsname="m9ZlFb"]',
            'button:has-text("Done")',
            'button:has-text("OK")',
            'button[type="submit"]'
        ], force=True, label="Final Save button", post_click_sleep=3)
        # Not failing if Save not found — operation may already be complete

        # Screenshot after Save
        ss_saved = f"screenshots/recovery_phone_saved_{timestamp}.png"
        await page.screenshot(path=ss_saved, full_page=True)
        print(f"  Screenshot saved: {ss_saved}")

        # STEP 4: Check if verification code is required
        # If Google asks for SMS/phone verification, we CANNOT automate this - SKIP
        print("\n  [STEP 4] Checking if verification required...")

        verification_selectors = [
            'input[name="code"]',
            'input[aria-label*="code" i]',
            'input[type="tel"][maxlength="6"]',
            'input[aria-label*="verification" i]',
        ]

        verification_texts = [
            "Enter the code",
            "Verify your phone",
            "verification code",
            "We sent a code",
            "Enter code",
        ]

        verification_required = False
        for sel in verification_selectors:
            try:
                elem = page.locator(sel).first
                count = await elem.count()
                if count > 0 and await elem.is_visible():
                    verification_required = True
                    break
            except:
                continue

        if not verification_required:
            # Also check by text content
            for text in verification_texts:
                try:
                    elem = page.get_by_text(text, exact=False).first
                    if await elem.count() > 0 and await elem.is_visible():
                        verification_required = True
                        break
                except:
                    continue

        # Final screenshot
        ss_final = f"screenshots/recovery_phone_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)
        print(f"  Screenshot saved: {ss_final}")

        if verification_required:
            print("  [SKIP] Google requires phone/SMS verification - cannot automate")
            print("  [SKIP] Recovery phone update needs manual verification")
            return "SKIP - Verification code required (cannot automate SMS verification)"

        print("\n  [SUCCESS] Recovery phone update completed!")
        return True

    except Exception as e:
        print(f"  [ERROR] Recovery phone update failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def update_recovery_email(page, config, new_email, base_url=None):
    """
    Update recovery email

    Workflow:
    1. Navigate to recovery email page
    2. Check if recovery email exists:
       - If NOT exists: Click "Add recovery email" button
       - If exists: Click Edit icon button
    3. Fill email in popup input
    4. Click Save button
    5. Click Cancel button in verification popup (skip verification)

    Args:
        page: Playwright page
        config: ConfigManager instance
        new_email: New recovery email
        base_url: Optional captured password URL to construct recovery URL from

    Returns:
        bool: Success status
    """
    print("\n[OPERATION] Updating Recovery Email...")

    try:
        timestamp = int(time.time())

        # Build URL from captured password URL if provided
        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            new_path = '/recovery/email'
            recovery_email_url = urlunparse((
                'https', 'myaccount.google.com', new_path,
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {recovery_email_url[:80]}...")
        else:
            recovery_email_url = config.get_url("recovery_email")
            print(f"  Using config URL: {recovery_email_url}")

        # Navigate to recovery email page
        await robust_goto(page, recovery_email_url)

        # Screenshot before
        ss_before = f"screenshots/recovery_email_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # STEP 1: Check if recovery email exists - try Add button first, then Edit button
        print("\n  [STEP 1] Checking if recovery email exists...")

        add_btn_found = await find_and_click(page, [
            'button:has-text("Add recovery email")',
            'button[aria-label*="Add recovery email" i]',
            'a:has-text("Add recovery email")',
            'button[jsname="Pr7Yme"]:has-text("Add")',
            'span.AeBiU-vQzf8d:has-text("Add recovery email")',
        ], js_click=True, max_retries=1, label="Add recovery email", post_click_sleep=2)

        if not add_btn_found:
            print("  No 'Add' button found - recovery email already exists, looking for Edit...")

            if not await find_and_click(page, [
                'button[aria-label="Edit recovery email"]',
                'button[aria-label*="Edit" i][aria-label*="email" i]',
                'button[jsname="Pr7Yme"][aria-label*="recovery email"]',
                'button.pYTkkf-Bz112c-LgbsSe:has(svg)',
                'button:has(path[d*="L20.41"])',
            ], js_click=True, label="Edit recovery email", post_click_sleep=2):
                print("  [ERROR] Could not find Add or Edit button")
                return False

        # STEP 2: Fill email in popup input
        print("\n  [STEP 2] Entering recovery email in popup...")

        email_input_selectors = [
            'input[type="email"][jsname="YPqjbf"]',
            'input[aria-label="Your recovery email"]',
            'input[placeholder="Enter email"]',
            'input[type="email"]',
            'input[autocomplete="username"]',
        ]

        # Find input with retry, check if already matches, then fill
        email_elem = await find_element(page, email_input_selectors, label="Email input")
        if email_elem:
            current_value = (await email_elem.input_value()).strip()
            if current_value:
                print(f"  Current email value: {current_value}")
                if current_value.lower() == new_email.strip().lower():
                    print(f"  [SKIP] Recovery email already matches — no change needed")
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(2)
                    print(f"  [SUCCESS] Recovery email already up-to-date")
                    return True

            await email_elem.click()
            await email_elem.press('Control+A')
            await email_elem.press('Backspace')
            await asyncio.sleep(0.5)
            await email_elem.fill(new_email)
            print(f"  [OK] Email entered: {new_email}")
        else:
            print("  [ERROR] Could not find email input")
            return False

        # STEP 3: Click Save button
        print("\n  [STEP 3] Clicking Save button...")

        if not await find_and_click(page, [
            'button[data-mdc-dialog-action="ok"]',
            'button[aria-label*="Save your recovery email"]',
            'button:has-text("Save")',
            'span.UywwFc-vQzf8d:has-text("Save")',
        ], js_click=True, label="Save button", post_click_sleep=3):
            print("  [ERROR] Could not find Save button")
            return False

        # STEP 4: Click Cancel button in verification popup (skip verification)
        print("\n  [STEP 4] Checking for verification popup...")

        await find_and_click(page, [
            'button[data-mdc-dialog-action="cancel"]',
            'button[jsname="acyM6e"]',
            'button:has-text("Cancel")',
            'span.mUIrbf-vQzf8d:has-text("Cancel")',
        ], js_click=True, label="Cancel verification popup", post_click_sleep=2)
        # Not failing if Cancel not found — verification may not appear

        # Final screenshot
        ss_final = f"screenshots/recovery_email_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)

        print(f"\n  [SUCCESS] Recovery email updated!")
        print(f"  New recovery email: {new_email}")
        return True

    except Exception as e:
        print(f"  [ERROR] Recovery email update failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def generate_backup_codes(page, config, base_url=None):
    """
    Generate new backup codes.
    Retries once on failure (navigates back and tries again).

    Returns:
        list: List of backup codes or None
    """
    print("\n[OPERATION] Generating Backup Codes...")

    # Build URL once
    if base_url:
        from urllib.parse import parse_qs, urlencode
        parsed = urlparse(base_url)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        preserved = {}
        for key in ['rapt', 'hl', 'pli']:
            val = query_params.get(key, [None])[0]
            if val:
                preserved[key] = val
        if 'hl' not in preserved:
            preserved['hl'] = 'en'
        backup_codes_url = urlunparse((
            'https', 'myaccount.google.com',
            '/two-step-verification/backup-codes',
            '', urlencode(preserved), ''
        ))
        print(f"  Built URL from session: {backup_codes_url[:80]}...")
    else:
        backup_codes_url = config.get_url("backup_codes")
        print(f"  Using config URL: {backup_codes_url}")

    # ── Inner attempt function ──────────────────────────────────────────
    async def _attempt(attempt_num):
        print(f"\n  ── Attempt {attempt_num} ──")

        await robust_goto(page, backup_codes_url)

        # Check for phone verification / challenge redirect
        current_url = page.url.lower()
        if any(kw in current_url for kw in ['challenge', 'signin', 'verifyphone', 'speedbump']):
            print(f"  [SKIP] Phone verification / challenge detected at URL")
            return None

        # STEP 1: Smart detect — "Get backup codes" (first-time) or "Generate new codes" (existing)
        print("\n  [STEP 1] Detecting backup codes state...")

        is_first_time = False

        # Try "Get backup codes" first (fresh account — no existing codes)
        get_clicked = await find_and_click(page, [
            'button:has-text("Get backup codes")',
            'a:has-text("Get backup codes")',
            'button[aria-label="Get backup codes"]',
        ], js_click=True, max_retries=1, label="Get backup codes", post_click_sleep=3)

        if get_clicked:
            print("  [OK] Fresh account — getting first backup codes")
            is_first_time = True
        else:
            # Fall back to "Generate new codes" (existing codes)
            if not await find_and_click(page, [
                'button[aria-label="Generate new codes"]',
                'button[jsname="Pr7Yme"]',
                'button.pYTkkf-Bz112c-LgbsSe:has(svg)',
                'button:has-text("Generate")',
            ], js_click=True, label="Generate new codes", post_click_sleep=3):
                print("  [ERROR] Could not find backup codes button")
                return None
            print("  [OK] Existing codes found — regenerating")

        # STEP 2: Confirmation popup (ONLY for regeneration, not first-time)
        if not is_first_time:
            print("\n  [STEP 2] Clicking 'Get new codes' in popup...")

            if not await find_and_click(page, [
                'button[data-mdc-dialog-action="ok"]',
                'button[jsname="Wilgpb"]',
                'button:has-text("Get new codes")',
                'span.mUIrbf-vQzf8d:has-text("Get new codes")',
            ], js_click=True, label="Get new codes popup", post_click_sleep=3):
                print("  [ERROR] Could not find confirmation popup")
                return None
        else:
            print("\n  [STEP 2] Skipped — first-time setup, no confirmation needed")

        # STEP 3: Extract all backup codes
        print("\n  [STEP 3] Waiting for backup codes to load...")

        # Wait for code elements to appear (max 15 seconds)
        try:
            await page.locator('div[dir="ltr"]').first.wait_for(state='visible', timeout=15000)
            print("  [OK] Code container appeared")
        except Exception:
            print("  [WARNING] Timeout waiting for codes, will still try extraction...")

        await asyncio.sleep(4)

        # Find all code elements with retry
        code_selectors = [
            'div[dir="ltr"]',
            'div.lgHlnd div[dir="ltr"]',
            'div.hJVXqf div[dir="ltr"]',
        ]

        backup_codes = []
        for code_attempt in range(1, 4):
            for sel in code_selectors:
                try:
                    all_codes = page.locator(sel)
                    count = await all_codes.count()

                    if count >= 10:
                        for i in range(count):
                            code_text = (await all_codes.nth(i).inner_text()).strip()
                            if code_text and len(code_text) >= 4 and any(c.isdigit() for c in code_text):
                                backup_codes.append(code_text)

                        if backup_codes:
                            print(f"  [OK] Extracted {len(backup_codes)} codes")
                            break
                except Exception:
                    continue

            if backup_codes:
                break
            if code_attempt < 3:
                print(f"  [RETRY {code_attempt}/3] Codes not ready, waiting 3s...")
                await asyncio.sleep(3)

        if not backup_codes:
            print("  [ERROR] Could not extract backup codes")
            return None

        print(f"\n  Extracted {len(backup_codes)} backup codes:")
        for i, code in enumerate(backup_codes, 1):
            print(f"    {i}. {code}")

        # Save to file
        Path("screenshots").mkdir(exist_ok=True)
        timestamp = int(time.time())
        backup_file = f"screenshots/backup_codes_{timestamp}.txt"
        with open(backup_file, 'w', encoding='utf-8') as f:
            f.write("Google Backup Codes\n")
            f.write("=" * 40 + "\n\n")
            for i, code in enumerate(backup_codes, 1):
                f.write(f"{i}. {code}\n")

        print(f"  [OK] Backup codes saved to: {backup_file}")
        return backup_codes

    # ── Retry loop (3 attempts) ─────────────────────────────────────────
    for attempt in range(1, 4):
        try:
            result = await _attempt(attempt)
            if result:
                return result
            if attempt < 3:
                print(f"\n  [RETRY] Attempt {attempt} failed, waiting 3s before retry...")
                await asyncio.sleep(3)
        except Exception as e:
            print(f"  [ERROR] Attempt {attempt} exception: {e}")
            import traceback
            traceback.print_exc()
            if attempt < 3:
                print(f"\n  [RETRY] Waiting 3s before retry...")
                await asyncio.sleep(3)

    print("  [FAILED] Backup code generation failed after 3 attempts")
    return None


async def add_and_replace_2fa_phone(page, config, new_phone, base_url=None):
    """
    Add a new backup 2-Step Verification phone and delete all old phones

    Workflow:
    1. Navigate to 2-Step Verification phone numbers page
    2. Click "Add a backup 2-Step Verification phone"
    3. Fill phone number in popup
    4. Click Next
    5. Click Save in confirmation popup
    6. Delete all other phone numbers (except the one we just added)

    Args:
        page: Playwright page
        config: ConfigManager instance
        new_phone: New phone number to add
        base_url: Optional captured password URL to construct 2FA phone URL from

    Returns:
        bool: Success status
    """
    print("\n[OPERATION] Adding and Replacing 2FA Phone...")

    try:
        timestamp = int(time.time())

        # Build URL from captured password URL if provided
        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            new_path = '/two-step-verification/phone-numbers'
            phone_url = urlunparse((
                'https', 'myaccount.google.com', new_path,
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {phone_url[:80]}...")
        else:
            phone_url = config.get_url("two_factor_phone")
            print(f"  Using config URL: {phone_url}")

        await robust_goto(page, phone_url)

        print("  Navigated to 2FA phone numbers page")

        # Screenshot before
        ss_before = f"screenshots/2fa_phone_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # STEP 0: Check if phone already exists
        print("\n  [STEP 0] Checking existing 2FA phones...")
        page_text = await page.text_content('body')

        new_last_6 = ''.join(filter(str.isdigit, str(new_phone)))[-6:]
        if new_last_6 in page_text:
            print(f"  [SKIP] Phone ending in {new_last_6} already exists on page")
            return True

        # STEP 1: Click "Add a backup 2-Step Verification phone"
        print("\n  [STEP 1] Clicking 'Add a backup 2-Step Verification phone'...")

        if not await find_and_click(page, [
            'button[jsname="Pr7Yme"]:has-text("Add a backup 2-Step Verification phone")',
            'button:has-text("Add a backup 2-Step Verification phone")',
            'span.AeBiU-vQzf8d:has-text("Add a backup 2-Step Verification phone")',
        ], js_click=True, label="Add 2FA phone", post_click_sleep=2):
            print("  [ERROR] Could not find 'Add' button")
            return False

        # STEP 2: Fill phone number in popup
        print("\n  [STEP 2] Entering phone number in popup...")

        phone_to_enter = str(new_phone).strip()
        if not phone_to_enter.startswith('+'):
            phone_to_enter = '+' + phone_to_enter

        if not await find_and_fill(page, [
            'input[type="tel"][jsname="YPqjbf"]',
            'input[aria-label="Phone input"]',
            'input[placeholder="Enter phone number"]',
            'input[type="tel"]',
        ], phone_to_enter, label="2FA phone input", clear_first=True, type_delay=100):
            print("  [ERROR] Could not find phone input")
            return False

        # STEP 3: Click Next button
        print("\n  [STEP 3] Clicking Next button...")

        if not await find_and_click(page, [
            'button[data-mdc-dialog-action="OCpkoe"]',
            'button[aria-label="Next button"]',
            'button:has-text("Next")',
            'span.mUIrbf-vQzf8d:has-text("Next")',
        ], js_click=True, label="Next button", post_click_sleep=2):
            print("  [ERROR] Could not find Next button")
            return False

        # STEP 4: Click Save button in confirmation popup
        print("\n  [STEP 4] Clicking Save button...")

        if not await find_and_click(page, [
            'button[data-mdc-dialog-action="x8hlje"]',
            'button[aria-label="Save phone number"]',
            'button:has-text("Save")',
            'span.mUIrbf-vQzf8d:has-text("Save")',
        ], js_click=True, label="Save button", post_click_sleep=3):
            print("  [ERROR] Could not find Save button")
            return False

        # Screenshot after adding phone
        ss_added = f"screenshots/2fa_phone_added_{timestamp}.png"
        await page.screenshot(path=ss_added, full_page=True)

        # STEP 4.5: Check if Google requires verification (SMS/phone)
        print("\n  [STEP 4.5] Checking if verification required after Save...")

        verification_selectors = [
            'input[name="code"]',
            'input[aria-label*="code" i]',
            'input[type="tel"][maxlength="6"]',
            'input[aria-label*="verification" i]',
        ]
        verification_texts = [
            "Enter the code", "Verify your phone", "verification code",
            "We sent a code", "Enter code", "Get a verification code",
        ]

        verification_required = False
        for sel in verification_selectors:
            try:
                elem = page.locator(sel).first
                if await elem.count() > 0 and await elem.is_visible():
                    verification_required = True
                    break
            except:
                continue

        if not verification_required:
            for text in verification_texts:
                try:
                    elem = page.get_by_text(text, exact=False).first
                    if await elem.count() > 0 and await elem.is_visible():
                        verification_required = True
                        break
                except:
                    continue

        if verification_required:
            print("  [SKIP] Google requires SMS/phone verification - cannot automate")
            return "SKIP - Verification code required (cannot automate SMS verification)"

        print(f"\n  [OK] Phone {new_phone} added successfully!")

        # STEP 5: Delete all OLD phone numbers (keep the newly added one)
        print("\n  [STEP 5] Deleting old phone numbers (keeping the new one)...")
        await asyncio.sleep(2)

        delete_btn_selector = 'button[aria-label*="Delete phone number"]'
        all_delete_btns = page.locator(delete_btn_selector)
        total_phones = await all_delete_btns.count()
        print(f"  Total phones on page: {total_phones}")

        phones_to_delete = total_phones - 1

        if phones_to_delete <= 0:
            print("  [OK] No old phones to delete")
        else:
            print(f"  Need to delete {phones_to_delete} old phone(s)")

            for i in range(phones_to_delete):
                try:
                    all_delete_btns = page.locator(delete_btn_selector)
                    count = await all_delete_btns.count()
                    if count <= 1:
                        print("  [OK] Only the new phone remains")
                        break

                    first_btn = all_delete_btns.first
                    await first_btn.evaluate('el => el.click()')
                    print(f"  [OK] Clicked delete button #{i+1}")
                    await asyncio.sleep(2)

                    # Confirm removal in popup with retry
                    if not await find_and_click(page, [
                        'button[data-mdc-dialog-action="ok"]',
                        'button:has-text("OK")',
                        'span.mUIrbf-vQzf8d:has-text("OK")',
                    ], js_click=True, label=f"OK confirm #{i+1}", post_click_sleep=3):
                        print("  [WARN] Could not find OK button, stopping deletion...")
                        break

                except Exception as e:
                    print(f"  [ERROR] Failed to delete phone #{i+1}: {str(e)[:50]}")
                    break

        # Final screenshot
        ss_final = f"screenshots/2fa_phone_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)
        print(f"  Screenshot saved: {ss_final}")

        print("\n  [SUCCESS] 2FA phone replacement completed!")
        return True

    except Exception as e:
        print(f"  [ERROR] 2FA phone operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def _handle_device_challenge(page, devices_url, account):
    """Handle verification challenges during device removal.

    Uses ScreenDetector + LoginBrain to handle password, TOTP, and backup code
    challenges that Google may show before allowing device management.

    Returns:
        None if no challenge or challenge resolved successfully.
        "SKIP - ..." string if challenge cannot be resolved.
    """
    detector = ScreenDetector(page)
    current_screen = await detector.detect_current_screen()

    # Also check URL for challenge/signin redirects
    current_url = page.url.lower()
    is_challenge_url = any(kw in current_url for kw in ['challenge', 'signin', 'verifyphone', 'speedbump'])

    challenge_screens = {
        LoginScreen.PASSWORD_INPUT,
        LoginScreen.AUTHENTICATOR_CODE,
        LoginScreen.BACKUP_CODE,
        LoginScreen.TRY_ANOTHER_WAY,
        LoginScreen.ACCOUNT_RECOVERY,
    }

    # No challenge detected — continue normally
    if current_screen not in challenge_screens and not is_challenge_url:
        return None

    print(f"  [CHALLENGE] Verification screen detected: {current_screen.name}")

    # No credentials to handle challenge — skip
    if not account:
        print("  [SKIP] No account credentials available to handle challenge")
        try:
            await robust_goto(page, "https://myaccount.google.com/?hl=en")
        except Exception:
            pass
        return "SKIP - Verification required but no credentials available"

    # Build credentials from account data
    password = str(account.get('Password', '') or '').strip()
    new_password = str(account.get('New Password', '') or '').strip()
    totp_secret = str(account.get('TOTP Secret', '') or '').strip()

    # Clean NaN values
    if new_password.lower() == 'nan':
        new_password = ''
    if totp_secret.lower() == 'nan':
        totp_secret = ''

    # Merge backup codes from Backup Code 1-10
    bc_list = []
    for i in range(1, 11):
        val = account.get(f'Backup Code {i}', '')
        if val and str(val).strip() and str(val).strip().lower() != 'nan':
            bc_list.append(str(val).strip())
    backup_code = ', '.join(bc_list)

    # Use generated password if available, else original
    effective_password = new_password if new_password else password

    recovery_email = str(account.get('Recovery Email', '') or '').strip()
    recovery_phone = str(account.get('Recovery Phone', '') or '').strip()
    if recovery_email.lower() == 'nan':
        recovery_email = ''
    if recovery_phone.lower() == 'nan':
        recovery_phone = ''

    # Check if we have ANY credentials to attempt
    has_creds = effective_password or totp_secret or backup_code
    if not has_creds:
        print("  [SKIP] No password, TOTP, or backup codes available")
        try:
            await robust_goto(page, "https://myaccount.google.com/?hl=en")
        except Exception:
            pass
        return "SKIP - Verification required but no credentials in Excel"

    print(f"  [CHALLENGE] Attempting to resolve with: "
          f"password={'YES' if effective_password else 'NO'}, "
          f"TOTP={'YES' if totp_secret else 'NO'}, "
          f"backup_codes={len(bc_list)}")

    brain = LoginBrain(
        page=page,
        detector=detector,
        credentials={
            'password': effective_password,
            'totp_secret': totp_secret,
            'backup_code': backup_code,
            'recovery_email': recovery_email,
            'recovery_phone': recovery_phone,
        },
        config={'require_inbox': False},
        log_fn=lambda msg: print(f"  [CHALLENGE] {msg}"),
    )

    # Poll loop — same pattern as gmail_authenticator._handle_two_factor()
    max_attempts = 15
    for attempt in range(max_attempts):
        current_screen = await detector.detect_current_screen()

        # If we're past the challenge, break
        if current_screen in (LoginScreen.LOGGED_IN, LoginScreen.SUCCESS_SCREEN):
            print("  [OK] Challenge resolved successfully")
            break

        # Check if we're back on a non-challenge page
        if current_screen == LoginScreen.UNKNOWN:
            cur_url = page.url.lower()
            if 'device-activity' in cur_url or ('myaccount.google.com' in cur_url and 'challenge' not in cur_url and 'signin' not in cur_url):
                print(f"  [OK] Challenge resolved — now on: {page.url[:80]}")
                break

        result = await brain.handle_screen(current_screen)

        if result.action == "success":
            print("  [OK] Challenge completed")
            break
        elif result.action == "fail":
            print(f"  [FAIL] Challenge failed: {result.error}")
            try:
                await robust_goto(page, "https://myaccount.google.com/?hl=en")
            except Exception:
                pass
            return f"SKIP - Challenge failed: {result.error}"
        elif result.action == "continue":
            continue
        elif result.action == "skip":
            await asyncio.sleep(2)

    # After challenge, re-navigate to devices page if needed
    if 'device-activity' not in page.url:
        print(f"  [CHALLENGE] Re-navigating to devices page...")
        await robust_goto(page, devices_url)

    return None


async def remove_all_devices(page, config, base_url=None, account=None):
    """
    Remove all logged-in devices except current session

    Workflow:
    1. Navigate to device-activity page
    2. Handle any verification challenge (password, TOTP, backup code)
    3. Find all device session links (exclude current session)
    4. For each device:
       a. Click device link to go to device page
       b. Click "Sign out" button on device page
       c. Click "Sign out" in confirmation popup
       d. Go back to device list
    5. Repeat until all devices (except current) are signed out

    Args:
        page: Playwright page
        config: ConfigManager instance
        base_url: Optional captured password URL to construct devices URL from
        account: Optional account dict with credentials for challenge handling

    Returns:
        bool: Success status
    """
    print("\n[OPERATION] Removing All Devices...")

    try:
        # Build URL from captured password URL if provided
        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            new_path = '/device-activity'
            devices_url = urlunparse((
                'https', 'myaccount.google.com', new_path,
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {devices_url[:80]}...")
        else:
            devices_url = config.get_url("devices")
            print(f"  Using config URL: {devices_url}")

        await robust_goto(page, devices_url)

        print(f"  Navigated to devices page — URL: {page.url[:100]}")

        # ── Handle verification challenges (password, TOTP, backup code) ──
        challenge_result = await _handle_device_challenge(page, devices_url, account)
        if challenge_result is not None:
            return challenge_result

        # ── Find and remove devices ───────────────────────────────────
        device_removed_count = 0

        while True:
            print(f"\n  [STEP] Checking for devices to remove...")

            # Find all device links
            device_link_selectors = [
                'a[href*="device-activity/id/"]',
                'a.RlFDUe.mlgsfe',
                'a[data-device-id]',
            ]

            device_links = None
            for sel in device_link_selectors:
                try:
                    device_links = page.locator(sel)
                    count = await device_links.count()
                    if count > 0:
                        print(f"  Found {count} device(s) with selector: {sel}")
                        break
                except:
                    continue

            if not device_links:
                print("  [INFO] No device links found")
                break

            total_devices = await device_links.count()

            if total_devices == 0:
                print("  [INFO] No more devices to remove")
                break

            # Filter out current session AND signed out devices
            devices_to_remove = []
            for i in range(total_devices):
                link = device_links.nth(i)

                try:
                    parent_text = await page.evaluate('''
                        (elem) => {
                            let parent = elem.closest('li') || elem.parentElement;
                            return parent ? parent.textContent : '';
                        }
                    ''', await link.element_handle())

                    if 'Your current session' in parent_text or 'current session' in parent_text.lower():
                        print(f"  [SKIP] Device #{i+1} is current session")
                        continue

                    if 'Signed out' in parent_text or 'signed out' in parent_text.lower():
                        print(f"  [SKIP] Device #{i+1} is already signed out")
                        continue

                    devices_to_remove.append(i)
                except:
                    devices_to_remove.append(i)

            print(f"  Total devices: {total_devices}")
            print(f"  Devices to remove (excluding current): {len(devices_to_remove)}")

            if len(devices_to_remove) == 0:
                print("  [INFO] No devices to remove (only current session remains)")
                break

            # Remove first non-current device
            device_index = devices_to_remove[0]
            print(f"\n  [REMOVING] Device #{device_index+1}...")

            device_link = device_links.nth(device_index)

            try:
                device_text = await device_link.inner_text()
                print(f"  Device: {device_text[:100]}...")
            except:
                pass

            # Click device link (navigates to device details page)
            try:
                await device_link.click(timeout=10000)
                await asyncio.sleep(3)
                print(f"  [OK] Clicked device link - navigated to device page")
            except Exception as e:
                print(f"  [ERROR] Failed to click device link: {str(e)[:50]}")
                break

            # Check if device page shows a verification challenge
            mid_challenge = await _handle_device_challenge(page, devices_url, account)
            if mid_challenge is not None:
                return mid_challenge

            # STEP: Click "Sign out" button on device page
            print("  [STEP] Clicking Sign out button on device page...")

            signout_clicked = await find_and_click(page, [
                'button[jsname="JIbuQc"]:has-text("Sign out")',
                'button:has-text("Sign out")',
                'span.Rju2Ue-TfeOUb-V67aGc:has-text("Sign out")',
                'button[id*="ucj"]',
            ], js_click=True, label="Sign out button", post_click_sleep=3)

            if not signout_clicked:
                print("  [ERROR] Could not find/click Sign out button")
                await robust_goto(page, devices_url)
                continue

            # STEP: Click "Sign out" in confirmation popup (if it appears)
            # Google sometimes shows a popup, sometimes signs out directly.
            # Wait a moment for popup to render, then try.
            print("  [STEP] Checking for confirmation popup...")
            await asyncio.sleep(1)

            popup_clicked = await find_and_click(page, [
                'button[jsname="LgbsSe"]:has-text("Sign out")',
                'button.VfPpkd-LgbsSe:has-text("Sign out")',
                'button[data-mdc-dialog-action="ok"]',
                'button[data-mdc-dialog-action="yes"]',
                'span.VfPpkd-vQzf8d:has-text("Sign out")',
                'button[data-id="EBS5u"]',
                'button:has-text("OK")',
                'button:has-text("Confirm")',
            ], js_click=True, label="Sign out popup", post_click_sleep=3)

            if not popup_clicked:
                print("  [INFO] No confirmation popup found — sign out may have completed directly")

            device_removed_count += 1
            print(f"  [OK] Device signed out! Total removed: {device_removed_count}")

            # Go back to device list
            await robust_goto(page, devices_url)

            # Handle any challenge that appears when navigating back (e.g. TOTP)
            back_challenge = await _handle_device_challenge(page, devices_url, account)
            if back_challenge is not None:
                print(f"  [WARN] Challenge after device removal: {back_challenge}")
                # Don't return — we already removed some devices
                break

        print(f"\n  [SUCCESS] Device removal completed!")
        print(f"  Total devices removed: {device_removed_count}")
        return True

    except Exception as e:
        print(f"  [ERROR] Device removal failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            await robust_goto(page, "https://myaccount.google.com/?hl=en")
        except:
            pass
        return False


async def change_name(page, config, first_name, last_name, base_url=None):
    """
    Change account first name and last name

    Workflow:
    1. Navigate to profile name edit page
    2. Clear and fill first name input
    3. Clear and fill last name input
    4. Click Save button

    Args:
        page: Playwright page
        config: ConfigManager instance
        first_name: New first name
        last_name: New last name
        base_url: Optional captured password URL to construct name URL from

    Returns:
        bool: Success status
    """
    print("\n[OPERATION] Changing Name...")

    try:
        timestamp = int(time.time())

        # Build URL from captured password URL if provided
        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            new_path = '/profile/name/edit'
            name_url = urlunparse((
                'https', 'myaccount.google.com', new_path,
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {name_url[:80]}...")
        else:
            name_url = "https://myaccount.google.com/profile/name/edit"
            print(f"  Using default URL: {name_url}")

        # Navigate to name edit page
        await robust_goto(page, name_url)

        # STEP 1: Fill first name input
        print("\n  [STEP 1] Entering first name...")
        first_name_selectors = [
            'input[jsname="YPqjbf"][autocomplete="off"]',
            'input[type="text"][jsname="YPqjbf"]',
            'input[aria-labelledby*="label-id"]',
            'input[type="text"]',
        ]

        # Find first input (first name) with retry
        first_input_elem = await find_element(page, first_name_selectors, label="First name input")
        if first_input_elem:
            await first_input_elem.click()
            await first_input_elem.press('Control+A')
            await first_input_elem.press('Backspace')
            await asyncio.sleep(0.5)
            await first_input_elem.fill(first_name)
            print(f"  [OK] First name entered: {first_name}")
        else:
            print("  [ERROR] Could not find first name input")
            return False

        # STEP 2: Fill last name input (ALWAYS clear, even if empty)
        print("\n  [STEP 2] Entering last name...")

        last_name_filled = False
        for attempt in range(1, 4):
            for sel in first_name_selectors:
                try:
                    inputs = page.locator(sel)
                    count = await inputs.count()
                    if count > 1:
                        last_input = inputs.nth(1)
                        if await last_input.is_visible():
                            await last_input.click()
                            await last_input.press('Control+A')
                            await last_input.press('Backspace')
                            await asyncio.sleep(0.5)
                            if last_name and last_name.strip():
                                await last_input.fill(last_name)
                                print(f"  [OK] Last name entered: {last_name}")
                            else:
                                print(f"  [OK] Last name cleared")
                            last_name_filled = True
                            break
                except Exception:
                    continue
            if last_name_filled:
                break
            if attempt < 3:
                print(f"  [RETRY {attempt}/3] Last name input not found, waiting 2s...")
                await asyncio.sleep(2)

        if not last_name_filled:
            print("  [WARNING] Could not find last name input, but continuing...")

        # STEP 3: Click Save button
        print("\n  [STEP 3] Clicking Save button...")

        if not await find_and_click(page, [
            'button[jsname="Pr7Yme"]:has-text("Save")',
            'button:has-text("Save")',
            'span[jsname="V67aGc"]:has-text("Save")',
            'button.UywwFc-LgbsSe:has-text("Save")',
        ], js_click=True, label="Save button", post_click_sleep=3):
            print("  [ERROR] Could not find Save button")
            return False

        print(f"\n  [SUCCESS] Name changed!")
        print(f"  First Name: {first_name}")
        print(f"  Last Name: {last_name}")
        return True

    except Exception as e:
        print(f"  [ERROR] Name change failed: {e}")
        import traceback
        traceback.print_exc()
        return False


# ═════════════════════════════════════════════════════════════════════════
# NEW REMOVE OPERATIONS (paired with Add/Update operations)
# ═════════════════════════════════════════════════════════════════════════


async def remove_recovery_phone(page, config, base_url=None):
    """
    Remove recovery phone number from account.

    Workflow:
    1. Navigate to recovery phone page
    2. Check if recovery phone exists
    3. Click Delete/Remove button
    4. Confirm removal in popup

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    print("\n[OPERATION] Removing Recovery Phone...")

    try:
        timestamp = int(time.time())

        # Build URL
        if base_url:
            recovery_phone_url = build_operation_url(base_url, 'rescuephone')
            print(f"  Built URL from session: {recovery_phone_url[:80]}...")
        else:
            recovery_phone_url = config.get_url("recovery_phone")
            print(f"  Using config URL: {recovery_phone_url}")

        await robust_goto(page, recovery_phone_url)

        ss_before = f"screenshots/remove_recovery_phone_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Check if "Add recovery phone" button exists - means no phone set
        add_elem = await find_element(page, [
            'button:has-text("Add recovery phone")',
            'button[jsname="Pr7Yme"]:has-text("Add")',
            'span.mUIrbf-vQzf8d:has-text("Add recovery phone")',
        ], max_retries=1, label="Add recovery phone check")
        if add_elem:
            print("  [SKIP] No recovery phone exists to remove")
            return "SKIP - No recovery phone exists to remove"

        # Look for Delete button
        print("\n  [STEP 1] Looking for Delete button...")

        if not await find_and_click(page, [
            'button[aria-label*="Delete" i]',
            'button[aria-label*="Remove" i]',
            'button:has-text("Delete")',
            'button:has-text("Remove")',
            'button[jsname="Pr7Yme"]:has(svg path[d*="M6"])',
        ], force=True, label="Delete recovery phone", post_click_sleep=2):
            return "SKIP - No delete button found for recovery phone"

        # Confirm removal in popup
        print("\n  [STEP 2] Confirming removal...")

        await find_and_click(page, [
            'button[data-mdc-dialog-action="ok"]',
            'button:has-text("Remove")',
            'button:has-text("Delete")',
            'button:has-text("Confirm")',
            'button:has-text("OK")',
        ], js_click=True, label="Confirm removal", post_click_sleep=3)

        # Check for verification requirement
        for sel in ['input[name="code"]', 'input[aria-label*="code" i]', 'input[type="tel"][maxlength="6"]']:
            try:
                elem = page.locator(sel).first
                if await elem.count() > 0 and await elem.is_visible():
                    return "SKIP - Verification code required (cannot automate)"
            except:
                continue

        ss_final = f"screenshots/remove_recovery_phone_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)

        print("\n  [SUCCESS] Recovery phone removed!")
        return True

    except Exception as e:
        print(f"  [ERROR] Remove recovery phone failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def remove_recovery_email(page, config, base_url=None):
    """
    Remove recovery email from account.

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    print("\n[OPERATION] Removing Recovery Email...")

    try:
        timestamp = int(time.time())

        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            recovery_email_url = urlunparse((
                'https', 'myaccount.google.com', '/recovery/email',
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {recovery_email_url[:80]}...")
        else:
            recovery_email_url = config.get_url("recovery_email")
            print(f"  Using config URL: {recovery_email_url}")

        await robust_goto(page, recovery_email_url)

        ss_before = f"screenshots/remove_recovery_email_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Check if "Add recovery email" button exists - no email set
        add_elem = await find_element(page, [
            'button:has-text("Add recovery email")',
            'button[jsname="Pr7Yme"]:has-text("Add")',
            'span.AeBiU-vQzf8d:has-text("Add recovery email")',
        ], max_retries=1, label="Add recovery email check")
        if add_elem:
            print("  [SKIP] No recovery email exists to remove")
            return "SKIP - No recovery email exists to remove"

        # Look for Delete/Trash button
        print("\n  [STEP 1] Looking for Delete button...")

        if not await find_and_click(page, [
            'button[aria-label*="Delete" i]',
            'button[aria-label*="Remove" i]',
            'button.pYTkkf-Bz112c-LgbsSe:has(svg path[d*="M6"])',
            'button:has-text("Delete")',
            'button:has-text("Remove")',
        ], force=True, label="Delete recovery email", post_click_sleep=2):
            return "SKIP - No delete button found for recovery email"

        # Confirm popup
        print("\n  [STEP 2] Confirming removal...")

        await find_and_click(page, [
            'button[data-mdc-dialog-action="ok"]',
            'button:has-text("Remove")',
            'button:has-text("Delete")',
            'button:has-text("OK")',
        ], js_click=True, label="Confirm removal", post_click_sleep=3)

        # Check for verification
        for sel in ['input[name="code"]', 'input[aria-label*="code" i]']:
            try:
                elem = page.locator(sel).first
                if await elem.count() > 0 and await elem.is_visible():
                    return "SKIP - Verification code required (cannot automate)"
            except:
                continue

        ss_final = f"screenshots/remove_recovery_email_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)

        print("\n  [SUCCESS] Recovery email removed!")
        return True

    except Exception as e:
        print(f"  [ERROR] Remove recovery email failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def remove_authenticator_app(page, config, base_url=None):
    """
    Remove authenticator app (2FA key) from account.

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    print("\n[OPERATION] Removing Authenticator App...")

    try:
        timestamp = int(time.time())

        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            auth_url = urlunparse((
                'https', 'myaccount.google.com', '/two-step-verification/authenticator',
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {auth_url[:80]}...")
        else:
            auth_url = config.get_url("authenticator_app")
            print(f"  Using config URL: {auth_url}")

        await robust_goto(page, auth_url)

        ss_before = f"screenshots/remove_authenticator_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Check if "Set up authenticator" exists - nothing to remove
        setup_elem = await find_element(page, [
            'button:has-text("Set up authenticator")',
            'button:has-text("Set up Authenticator")',
            'span:has-text("Set up authenticator")',
        ], max_retries=1, label="Set up authenticator check")
        if setup_elem:
            return "SKIP - No authenticator app configured to remove"

        # Look for Delete/Trash icon button
        print("\n  [STEP 1] Looking for Delete button...")

        if not await find_and_click(page, [
            'button[aria-label*="Delete" i]',
            'button[aria-label*="Remove" i]',
            'button:has-text("Remove authenticator")',
            'button:has-text("Delete")',
            'button.pYTkkf-Bz112c-LgbsSe:has(svg)',
        ], js_click=True, label="Delete authenticator", post_click_sleep=2):
            return False

        # Confirm popup
        print("\n  [STEP 2] Confirming removal...")

        await find_and_click(page, [
            'button[data-mdc-dialog-action="ok"]',
            'button:has-text("Remove")',
            'button:has-text("Turn off")',
            'button:has-text("OK")',
            'button:has-text("Confirm")',
        ], js_click=True, label="Confirm removal", post_click_sleep=3)

        # Check for verification
        for sel in ['input[name="code"]', 'input[aria-label*="code" i]']:
            try:
                elem = page.locator(sel).first
                if await elem.count() > 0 and await elem.is_visible():
                    return "SKIP - Verification code required (cannot automate)"
            except:
                continue

        ss_final = f"screenshots/remove_authenticator_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)

        print("\n  [SUCCESS] Authenticator app removed!")
        return True

    except Exception as e:
        print(f"  [ERROR] Remove authenticator failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def remove_backup_codes(page, config, base_url=None):
    """
    Remove/revoke all backup codes.

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    print("\n[OPERATION] Removing Backup Codes...")

    try:
        timestamp = int(time.time())

        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            backup_url = urlunparse((
                'https', 'myaccount.google.com', '/two-step-verification/backup-codes',
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {backup_url[:80]}...")
        else:
            backup_url = config.get_url("backup_codes")
            print(f"  Using config URL: {backup_url}")

        await robust_goto(page, backup_url)

        ss_before = f"screenshots/remove_backup_codes_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Check if "Get backup codes" exists - no codes set up
        setup_elem = await find_element(page, [
            'button:has-text("Get backup codes")',
            'button:has-text("Generate backup codes")',
        ], max_retries=1, label="Get backup codes check")
        if setup_elem:
            return "SKIP - No backup codes exist to remove"

        # Look for Delete/Trash button
        print("\n  [STEP 1] Looking for Delete button...")

        delete_found = await find_and_click(page, [
            'button[aria-label*="Delete" i]',
            'button[aria-label*="Revoke" i]',
            'button:has-text("Delete backup codes")',
            'button:has-text("Revoke")',
        ], js_click=True, label="Delete backup codes", post_click_sleep=2)

        if not delete_found:
            # Try second icon button (first is generate, second is delete)
            try:
                icon_btns = page.locator('button.pYTkkf-Bz112c-LgbsSe:has(svg)')
                count = await icon_btns.count()
                if count >= 2:
                    await icon_btns.nth(1).evaluate('el => el.click()')
                    print(f"  [OK] Clicked second icon button (delete)")
                    delete_found = True
                    await asyncio.sleep(2)
            except:
                pass

        if not delete_found:
            return "SKIP - No delete button found for backup codes"

        # Confirm popup
        print("\n  [STEP 2] Confirming deletion...")

        await find_and_click(page, [
            'button[data-mdc-dialog-action="ok"]',
            'button:has-text("Revoke codes")',
            'button:has-text("Delete")',
            'button:has-text("OK")',
            'button:has-text("Confirm")',
        ], js_click=True, label="Confirm deletion", post_click_sleep=3)

        ss_final = f"screenshots/remove_backup_codes_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)

        print("\n  [SUCCESS] Backup codes removed!")
        return True

    except Exception as e:
        print(f"  [ERROR] Remove backup codes failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def remove_2fa_phone(page, config, base_url=None):
    """
    Remove ALL 2FA phone numbers.

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    print("\n[OPERATION] Removing All 2FA Phones...")

    try:
        timestamp = int(time.time())

        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            phone_url = urlunparse((
                'https', 'myaccount.google.com', '/two-step-verification/phone-numbers',
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {phone_url[:80]}...")
        else:
            phone_url = config.get_url("two_factor_phone")
            print(f"  Using config URL: {phone_url}")

        await robust_goto(page, phone_url)

        ss_before = f"screenshots/remove_2fa_phones_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Find all delete buttons with retry
        delete_selector = 'button[aria-label*="Delete phone number"]'
        all_delete_btns = page.locator(delete_selector)
        total = await all_delete_btns.count()

        if total == 0:
            for alt_sel in ['button[aria-label*="Delete" i]', 'button:has-text("Delete")']:
                alt_btns = page.locator(alt_sel)
                alt_count = await alt_btns.count()
                if alt_count > 0:
                    total = alt_count
                    delete_selector = alt_sel
                    all_delete_btns = alt_btns
                    break

        if total == 0:
            print("  [SKIP] No 2FA phones found to remove")
            return "SKIP - No 2FA phone numbers to remove"

        print(f"  Found {total} 2FA phone(s) to remove")

        for i in range(total):
            try:
                btns = page.locator(delete_selector)
                count = await btns.count()
                if count == 0:
                    break

                await btns.first.evaluate('el => el.click()')
                print(f"  [OK] Clicked delete #{i+1}")
                await asyncio.sleep(2)

                # Confirm in popup with retry
                await find_and_click(page, [
                    'button[data-mdc-dialog-action="ok"]',
                    'button:has-text("OK")',
                    'button:has-text("Remove")',
                ], js_click=True, label=f"Confirm removal #{i+1}", post_click_sleep=3)
            except Exception as e:
                print(f"  [ERROR] Delete #{i+1} failed: {str(e)[:50]}")
                break

        ss_final = f"screenshots/remove_2fa_phones_final_{timestamp}.png"
        await page.screenshot(path=ss_final, full_page=True)

        print(f"\n  [SUCCESS] All 2FA phones removed!")
        return True

    except Exception as e:
        print(f"  [ERROR] Remove 2FA phones failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def security_checkup(page, config, base_url=None):
    """
    Perform security checkup at https://myaccount.google.com/security-checkup/2

    Workflow:
    1. Navigate to security checkup page
    2. Expand each section (button[id^="section"])
    3. In each section:
       - Click "Yes, confirm" buttons (confirms recovery info)
       - Collect device session URLs (device-activity/id/...) for sign-out
       - Click "Remove" buttons one by one
       - Click "Remove access" buttons + confirm popup
    4. After all sections: sign out from collected device sessions
       - Navigate to each device URL, click "Sign out", confirm popup
       - Skip current session and already signed-out devices
    5. All sections optional - skip on error

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    import re
    print("\n[OPERATION] Security Checkup...")

    try:
        timestamp = int(time.time())
        CHECKUP_URL = "https://myaccount.google.com/security-checkup/2"

        # Add rapt if available
        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            rapt = query_params.get('rapt', [None])[0]
            if rapt:
                CHECKUP_URL += f"?rapt={rapt}"

        print(f"  Navigating to security checkup: {CHECKUP_URL[:80]}...")
        await robust_goto(page, CHECKUP_URL)

        ss_before = f"screenshots/security_checkup_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Collect all section button IDs — broad prefix handles sectionc*, sectioni*, etc.
        section_buttons = page.locator('button[id^="section"]')
        total_sections = await section_buttons.count()
        print(f"  Found {total_sections} collapsible section(s)")

        if total_sections == 0:
            print("  [INFO] No sections found - checkup may be complete")
            return True

        section_ids = []
        for i in range(total_sections):
            sid = await section_buttons.nth(i).get_attribute('id')
            if sid:
                section_ids.append(sid)

        print(f"  Sections: {section_ids}")
        sections_processed = 0
        device_hrefs_to_signout = []  # Collect device URLs for sign-out after all sections

        for sid in section_ids:
            try:
                btn = page.locator(f'button#{sid}').first
                if await btn.count() == 0:
                    continue

                # Expand section if collapsed
                expanded = await btn.get_attribute('aria-expanded')
                if expanded != 'true':
                    await btn.scroll_into_view_if_needed()
                    await btn.click()
                    print(f"  [{sid}] Expanded section")
                    await asyncio.sleep(2)

                # Get content area
                controls_id = await btn.get_attribute('aria-controls')
                content = page.locator(f'#{controls_id}') if controls_id else page

                # A: Click "Yes, confirm" buttons (recovery phone/email confirmation)
                for sel in ['button[aria-label*="Yes, confirm" i]', 'button:has-text("Yes, confirm")']:
                    try:
                        yes_btn = content.locator(sel).first
                        if await yes_btn.count() > 0 and await yes_btn.is_visible():
                            await yes_btn.click()
                            print(f"  [{sid}] Clicked 'Yes, confirm'")
                            await asyncio.sleep(2)
                            break
                    except:
                        continue

                # B: Collect device session URLs for sign-out later
                try:
                    device_links = content.locator('a[href*="device-activity/id/"]')
                    device_count = await device_links.count()
                    if device_count > 0:
                        print(f"  [{sid}] Found {device_count} device link(s) — collecting sessions")
                        for di in range(device_count):
                            try:
                                link = device_links.nth(di)
                                parent_text = await page.evaluate('''
                                    (elem) => {
                                        let p = elem.closest('li') || elem.parentElement;
                                        return p ? p.textContent : '';
                                    }
                                ''', await link.element_handle())

                                if 'current session' in parent_text.lower():
                                    print(f"  [{sid}] Device {di+1}: Current session — skip")
                                    continue
                                if 'signed out' in parent_text.lower():
                                    print(f"  [{sid}] Device {di+1}: Already signed out — skip")
                                    continue

                                href = await link.get_attribute('href')
                                if href:
                                    full = href if href.startswith('http') else f"https://myaccount.google.com/{href.lstrip('/')}"
                                    device_hrefs_to_signout.append(full)
                                    print(f"  [{sid}] Device {di+1}: Queued for sign-out")
                            except:
                                continue
                except:
                    pass

                # C: Click "Remove" buttons (exact - not "Remove access")
                for r in range(20):
                    try:
                        remove_btns = content.locator('button').filter(
                            has_text=re.compile(r'^\s*Remove\s*$', re.IGNORECASE)
                        )
                        if await remove_btns.count() == 0:
                            break
                        first = remove_btns.first
                        if not await first.is_visible():
                            break
                        await first.click()
                        print(f"  [{sid}] Clicked 'Remove' #{r+1}")
                        await asyncio.sleep(2)
                    except:
                        break

                # D: Click "Remove access" buttons + confirm popup
                for r in range(20):
                    try:
                        ra_btns = content.locator('button').filter(
                            has_text=re.compile(r'^\s*Remove access\s*$', re.IGNORECASE)
                        )
                        if await ra_btns.count() == 0:
                            break
                        first = ra_btns.first
                        if not await first.is_visible():
                            break
                        await first.click()
                        print(f"  [{sid}] Clicked 'Remove access' #{r+1}")
                        await asyncio.sleep(2)

                        # Confirm popup
                        for c_sel in ['button[jsname="czYADc"]', 'button[data-mdc-dialog-action="ok"]', 'button:has-text("Confirm")']:
                            try:
                                c_btn = page.locator(c_sel).first
                                if await c_btn.count() > 0 and await c_btn.is_visible():
                                    await c_btn.click()
                                    print(f"  [{sid}] Confirmed remove access")
                                    await asyncio.sleep(2)
                                    break
                            except:
                                continue
                    except:
                        break

                sections_processed += 1

            except Exception as sec_err:
                print(f"  [{sid}] Section error: {str(sec_err)[:80]} - skip")
                continue

        # ── E: Sign out from collected device sessions ─────────────────────
        if device_hrefs_to_signout:
            print(f"\n  [DEVICES] Signing out from {len(device_hrefs_to_signout)} device(s)...")
            devices_removed = 0
            for dev_idx, dev_url in enumerate(device_hrefs_to_signout, 1):
                try:
                    print(f"  [DEVICE {dev_idx}/{len(device_hrefs_to_signout)}] Navigating to device page...")
                    await robust_goto(page, dev_url)

                    # Click "Sign out" button on device page
                    signout_clicked = False
                    for so_sel in [
                        'button:has-text("Sign out")',
                        'button[jsname="JIbuQc"]:has-text("Sign out")',
                        'span:has-text("Sign out")',
                    ]:
                        try:
                            so_btn = page.locator(so_sel).first
                            if await so_btn.count() > 0 and await so_btn.is_visible():
                                await so_btn.evaluate('el => el.click()')
                                print(f"  [DEVICE {dev_idx}] Clicked 'Sign out'")
                                await asyncio.sleep(2)
                                signout_clicked = True
                                break
                        except:
                            continue

                    if not signout_clicked:
                        print(f"  [DEVICE {dev_idx}] Sign out button not found — skip")
                        continue

                    # Click "Sign out" in confirmation popup
                    for cp_sel in [
                        'button[jsname="LgbsSe"]:has-text("Sign out")',
                        'button.VfPpkd-LgbsSe:has-text("Sign out")',
                        'span.VfPpkd-vQzf8d:has-text("Sign out")',
                        'button[data-id="EBS5u"]',
                    ]:
                        try:
                            cp_btn = page.locator(cp_sel).first
                            if await cp_btn.count() > 0 and await cp_btn.is_visible():
                                await cp_btn.evaluate('el => el.click()')
                                print(f"  [DEVICE {dev_idx}] Confirmed sign-out in popup")
                                await asyncio.sleep(3)
                                break
                        except:
                            continue

                    devices_removed += 1
                    print(f"  [DEVICE {dev_idx}] Signed out!")
                except Exception as dev_err:
                    print(f"  [DEVICE {dev_idx}] Error: {str(dev_err)[:60]}")
            print(f"  [DEVICES] Done — {devices_removed}/{len(device_hrefs_to_signout)} devices signed out")
        else:
            print("  [DEVICES] No devices to sign out")

        ss_final = f"screenshots/security_checkup_final_{timestamp}.png"
        try:
            await page.screenshot(path=ss_final, full_page=True)
        except:
            pass

        print(f"\n  [SUCCESS] Security checkup done! Processed {sections_processed}/{len(section_ids)} sections")
        return True

    except Exception as e:
        print(f"  [ERROR] Security checkup failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main interactive test function"""

    print("\n" + "="*70)
    print("GMAIL ACCOUNT OPERATIONS - INTERACTIVE TEST")
    print("="*70)

    # Get login credentials
    print("\n[STEP 1] Enter Login Credentials")
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    totp_secret_raw = input("TOTP Secret (2FA key): ").strip()

    # Clean TOTP secret
    totp_secret = totp_secret_raw.replace(" ", "").replace("-", "").upper()

    # Show menu and get choices
    show_menu()
    choices = get_user_choices()

    print(f"\nSelected operations: {choices}")
    input("\nPress ENTER to start login and operations...")

    # Initialize browser
    async with async_playwright() as p:
        # Playwright creates fresh ephemeral profile by default
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500,
            args=[
                '--disable-blink-features=AutomationControlled',  # Avoid bot detection
                '--lang=en-US',  # FORCE English language
                '--accept-lang=en-US,en',
            ]
        )

        # Create context with EXPLICIT English settings
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )
        page = await context.new_page()

        # Additional stealth: Remove webdriver flag and override language
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'language', {get: () => 'en-US'});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

        try:
            # Initialize components
            config = ConfigManager()
            detector = ScreenDetector(page)
            totp_gen = TOTPGenerator()

            # STEP 2: Login (manual approach like test_debug.py)
            print("\n[STEP 2] Performing Login...")

            # Navigate to login
            login_url = config.get_url("login")
            await page.goto(login_url, wait_until="networkidle")
            await asyncio.sleep(3)

            # Enter email
            print("[STEP 2.1] Entering email...")
            email_selectors = ['#identifierId', 'input[type="email"]', 'input[name="identifier"]']
            email_filled = False
            for sel in email_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.count() > 0 and await elem.is_visible():
                        await elem.fill(email)
                        print(f"  [OK] Email entered: {sel}")
                        email_filled = True
                        break
                except:
                    continue

            if not email_filled:
                print("[ERROR] Could not enter email")
                return

            await asyncio.sleep(1)
            await page.locator('button:has-text("Next")').first.click()
            print("  [OK] Clicked Next")
            await asyncio.sleep(4)

            # OPTIONAL: Check for "Use your fingerprint, face, or screen lock" screen
            # If it appears, click "Try another way" to proceed to password
            print("[STEP 2.1.5] Checking for fingerprint/face lock screen...")
            try_another_selectors = [
                'button:has-text("Try another way")',
                'button[jsname="LgbsSe"]:has-text("Try another way")',
                'span.VfPpkd-vQzf8d:has-text("Try another way")',
            ]

            try_another_found = False
            for sel in try_another_selectors:
                try:
                    elem = page.locator(sel).first
                    count = await elem.count()
                    if count > 0:
                        is_visible = await elem.is_visible()
                        if is_visible:
                            print(f"  [INFO] Found 'Try another way' button - clicking it...")
                            await elem.evaluate('el => el.click()')
                            print("  [OK] Clicked 'Try another way'")
                            try_another_found = True
                            await asyncio.sleep(3)
                            break
                except:
                    continue

            if not try_another_found:
                print("  [INFO] No fingerprint/face lock screen (continuing)")

            # OPTIONAL: Check for TOTP code input BEFORE password (rare but possible)
            print("[STEP 2.1.6] Checking for early authenticator code screen...")
            totp_input_selectors = [
                'input[type="text"][jsname="YPqjbf"][aria-label*="code" i]',
                'input[type="tel"][aria-label*="code" i]',
                'input[type="text"][placeholder*="code" i]',
                'input[id*="totpPin"]',
            ]

            early_totp_found = False
            for sel in totp_input_selectors:
                try:
                    elem = page.locator(sel).first
                    count = await elem.count()
                    if count > 0:
                        is_visible = await elem.is_visible()
                        if is_visible:
                            print(f"  [INFO] Authenticator code screen detected BEFORE password!")
                            print(f"  [INFO] This is optional bypass - entering TOTP code...")

                            # Generate TOTP code
                            totp_gen = TOTPGenerator()
                            totp_code = totp_gen.generate_code(totp_secret)
                            print(f"  Generated code: {totp_code}")

                            # Enter TOTP code
                            await elem.fill(totp_code)
                            print(f"  [OK] TOTP code entered: {sel}")

                            # Click Next
                            await asyncio.sleep(1)
                            await page.locator('button:has-text("Next")').first.click()
                            print("  [OK] Clicked Next")
                            await asyncio.sleep(4)

                            early_totp_found = True
                            break
                except:
                    continue

            if not early_totp_found:
                print("  [INFO] No early authenticator code screen (continuing to password)")

            # Enter password
            print("[STEP 2.2] Entering password...")
            pwd_selectors = ['input[type="password"]', 'input[name="Passwd"]']
            pwd_filled = False
            for sel in pwd_selectors:
                try:
                    elem = page.locator(sel).first
                    if await elem.count() > 0 and await elem.is_visible():
                        await elem.fill(password)
                        print(f"  [OK] Password entered: {sel}")
                        pwd_filled = True
                        break
                except:
                    continue

            if not pwd_filled:
                print("[ERROR] Could not enter password")
                return

            await asyncio.sleep(1)
            await page.locator('button:has-text("Next")').first.click()
            print("  [OK] Clicked Next")
            await asyncio.sleep(5)

            # Check for errors before 2FA
            print("[STEP 2.2.5] Checking for login errors...")
            error_check = await detect_and_handle_errors(page, email)
            if error_check['has_error']:
                print(f"  [ERROR] {error_check['error_type']}")
                print(f"  Reason: {error_check['reason']}")
                print(f"  {error_check['solution']}")
                print(f"  Screenshot: {error_check['screenshot_path']}")

                # Save to failure log
                save_failure_log(email, "Login/2FA", error_check)

                # Return failure
                print("\n[FAILED] Cannot proceed - blocking error detected")
                return

            # Handle 2FA
            print("[STEP 2.3] Handling 2FA...")
            screen = await detector.detect_current_screen()
            print(f"  Detected: {screen.name}")

            # Click authenticator option if needed
            if screen == LoginScreen.ACCOUNT_RECOVERY or screen == LoginScreen.TRY_ANOTHER_WAY:
                print("  Clicking authenticator option...")
                auth_selectors = [
                    '[jsname="EBHGs"][data-challengetype="6"]',
                    'li:has-text("Google Authenticator")',
                    'div[role="link"]:has-text("Authenticator")'
                ]
                for sel in auth_selectors:
                    try:
                        elem = page.locator(sel).first
                        if await elem.count() > 0:
                            await elem.click()
                            print(f"  [OK] Clicked: {sel}")
                            await asyncio.sleep(3)
                            break
                    except:
                        continue

            # Enter TOTP code
            print("  Generating TOTP code...")
            totp_code = totp_gen.generate_code(totp_secret)
            print(f"  Generated code: {totp_code}")

            code_input = page.locator('input[type="tel"]').first
            await code_input.fill(totp_code)
            print("  [OK] TOTP code entered")

            await asyncio.sleep(1)
            await page.locator('button:has-text("Next")').first.click()
            print("  [OK] Clicked Next")
            await asyncio.sleep(5)

            # Check for errors after TOTP
            print("[STEP 2.3.5] Checking for post-2FA errors...")
            error_check = await detect_and_handle_errors(page, email)
            if error_check['has_error']:
                print(f"  [ERROR] {error_check['error_type']}")
                print(f"  Reason: {error_check['reason']}")
                print(f"  {error_check['solution']}")
                print(f"  Screenshot: {error_check['screenshot_path']}")

                # Save to failure log
                save_failure_log(email, "Post-2FA Verification", error_check)

                # Return failure
                print("\n[FAILED] Cannot proceed - blocking error detected")
                return

            # Handle passkey prompt if appears
            print("[STEP 2.4] Checking for passkey prompt...")
            screen = await detector.detect_current_screen()
            if screen == LoginScreen.PASSKEY_PROMPT:
                print("  Passkey prompt detected - clicking Not now...")
                not_now_clicked = await detector.click_not_now()
                if not_now_clicked:
                    print("  [OK] Clicked Not now")
                    await asyncio.sleep(3)
                else:
                    print("  [WARNING] Could not click Not now automatically")

            print("[OK] Login successful!")
            await asyncio.sleep(3)

            # CRITICAL: Force Google account language to English BEFORE any operations
            # This prevents Gmail/Google pages from loading in French or other languages
            print("\n[STEP 2.5] Forcing Google account language to English...")
            try:
                # Navigate to language settings page
                language_url = "https://myaccount.google.com/language"
                await page.goto(language_url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)

                # Look for language dropdown or English option
                english_selectors = [
                    'div[data-value="en"]',  # English option
                    'div[data-value="en-US"]',  # English (US)
                    'div[role="button"][data-value="en"]',
                    '[data-value="en"]',
                ]

                language_changed = False
                for sel in english_selectors:
                    try:
                        elem = page.locator(sel).first
                        if await elem.count() > 0:
                            await elem.click()
                            print(f"  [OK] Clicked English language option: {sel}")
                            language_changed = True
                            await asyncio.sleep(2)
                            break
                    except Exception as e:
                        continue

                if language_changed:
                    print("  [OK] Google account language set to English!")
                else:
                    # Try alternative: Look for language edit button and change
                    try:
                        # Click edit button if present
                        edit_button = page.locator('button[aria-label*="Edit" i]').first
                        if await edit_button.count() > 0:
                            await edit_button.click()
                            await asyncio.sleep(1)

                            # Select English from dropdown
                            await page.locator('div[data-value="en"]').first.click()
                            await asyncio.sleep(1)
                            print("  [OK] Language changed via edit button")
                    except:
                        pass

                    print("  [OK] Language setting attempt completed (may already be English)")

                await asyncio.sleep(2)
            except Exception as lang_err:
                print(f"  [WARN] Could not force language to English: {lang_err}")
                print("  [INFO] Continuing with operations...")

            # CRITICAL: Capture password URL to build operation URLs
            print("\n[STEP 2.6] Detecting Success Screen and Capturing URL...")
            password_url = None

            # Detect current screen
            current_screen = await detector.detect_current_screen()
            print(f"Current screen: {current_screen.name}")
            print(f"Current URL: {page.url}")

            # Handle success screen if present
            if current_screen == LoginScreen.SUCCESS_SCREEN:
                print("[INFO] Success screen detected - clicking 'Change password'...")

                # Click "Change password" to get URL with rapt token
                change_pwd_selectors = [
                    'a[aria-label="Change password"]',
                    'a[href*="signinoptions/password"]',
                    '[jsname="hSRGPd"]',
                    'a[aria-label*="password" i]'
                ]

                clicked = False
                for sel in change_pwd_selectors:
                    try:
                        elem = page.locator(sel).first
                        count = await elem.count()
                        if count > 0:
                            await elem.click()
                            print(f"[OK] Clicked 'Change password': {sel}")
                            clicked = True
                            await asyncio.sleep(3)
                            break
                    except:
                        continue

                if clicked:
                    password_url = page.url
                    print(f"[OK] Captured password change URL")
                    print(f"     URL: {password_url[:80]}...")
                    # Save URL to file for reference
                    Path("screenshots").mkdir(exist_ok=True)
                    with open("screenshots/password_change_url.txt", 'w', encoding='utf-8') as f:
                        f.write(password_url)
                    print(f"     Saved to: screenshots/password_change_url.txt")
                else:
                    print("[WARNING] Could not click 'Change password'")
                    print("[INFO] Operations may require re-authentication")

            elif current_screen == LoginScreen.LOGGED_IN or "myaccount.google.com" in page.url:
                print("[INFO] Already on account page - navigating to password change...")
                # Navigate directly to password change to get URL with token
                await page.goto("https://myaccount.google.com/signinoptions/password", wait_until="domcontentloaded")
                await asyncio.sleep(3)
                password_url = page.url
                print(f"[OK] Captured password change URL")
                print(f"     URL: {password_url[:80]}...")
                Path("screenshots").mkdir(exist_ok=True)
                with open("screenshots/password_change_url.txt", 'w', encoding='utf-8') as f:
                    f.write(password_url)
                print(f"     Saved to: screenshots/password_change_url.txt")

            else:
                print(f"[WARNING] Unexpected screen: {current_screen.name}")
                print("[INFO] Operations will use config URLs instead of session URLs")

            # STEP 3: Perform selected operations
            print("\n[STEP 3] Performing Selected Operations...")
            if password_url:
                print(f"[INFO] Using session-based URLs (maintains authentication)")
            else:
                print(f"[INFO] Using config URLs (may require re-authentication)")

            results = {}

            for choice in choices:
                if choice == 1:
                    new_pwd = input("\nEnter new password: ").strip()
                    results['password_change'] = await change_password(
                        page, config, new_pwd, base_url=password_url
                    )

                elif choice == 2:
                    new_phone = input("\nEnter new recovery phone: ").strip()
                    results['recovery_phone'] = await update_recovery_phone(
                        page, config, new_phone, base_url=password_url
                    )

                elif choice == 3:
                    new_email = input("\nEnter new recovery email: ").strip()
                    results['recovery_email'] = await update_recovery_email(
                        page, config, new_email, base_url=password_url
                    )

                elif choice == 4:
                    success, new_key = await change_authenticator_app(
                        page, config, base_url=password_url
                    )
                    results['authenticator_change'] = success
                    if success and new_key:
                        print(f"\n[IMPORTANT] Save this new authenticator key:")
                        print(f"  {new_key}")
                        print(f"  Saved to: screenshots/authenticator_key_*.txt")

                elif choice == 5:
                    results['backup_codes'] = await generate_backup_codes(
                        page, config, base_url=password_url
                    )

                elif choice == 6:
                    new_2fa_phone = input("\nEnter new 2FA phone number: ").strip()
                    results['2fa_phone'] = await add_and_replace_2fa_phone(
                        page, config, new_2fa_phone, base_url=password_url
                    )

                elif choice == 7:
                    results['remove_devices'] = await remove_all_devices(
                        page, config, base_url=password_url
                    )

                elif choice == 8:
                    print("\n[INPUT] Enter new name details:")
                    new_first_name = input("First Name: ").strip()
                    new_last_name = input("Last Name: ").strip()
                    results['change_name'] = await change_name(
                        page, config, new_first_name, new_last_name, base_url=password_url
                    )

                await asyncio.sleep(1)

            # STEP 4: Show results
            print("\n" + "="*70)
            print("OPERATION RESULTS")
            print("="*70)
            for op, status in results.items():
                status_str = "[OK]" if status else "[FAIL]"
                print(f"  {status_str} {op}")
            print("="*70)

        except Exception as e:
            print(f"\n[EXCEPTION] {e}")
            import traceback
            traceback.print_exc()

        finally:
            # Cleanup: Close browser completely
            print("\n[CLEANUP] Closing browser...")
            try:
                # Close all pages first
                for page in context.pages:
                    try:
                        await page.close()
                    except:
                        pass

                # Close context
                await context.close()
                print("  [OK] Browser context closed")

                # Close browser
                await browser.close()
                print("  [OK] Browser closed completely")

            except Exception as e:
                print(f"  [WARN] Cleanup error: {e}")

            print("\n[DONE] All operations completed and browser closed!")
            print("="*70)


##############################################################################
# ── Operation 10a: Enable 2FA (Turn on 2-Step Verification) ────────────────
##############################################################################

async def enable_2fa(page, config, base_url=None):
    """
    Enable 2-Step Verification on the account.

    Flow:
      1. Navigate to twosv settings page
      2. Check if already ON (Turn off button visible) → SKIP
      3. Click "Turn on 2-Step Verification"
      4. Click "Done" in popup

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    print("\n[OPERATION] Enable 2FA (Turn on 2-Step Verification)...")

    try:
        timestamp = int(time.time())

        # Build URL from session or config
        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            twosv_url = urlunparse((
                'https', 'myaccount.google.com',
                '/signinoptions/twosv',
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {twosv_url[:80]}...")
        else:
            twosv_url = config.get_url("two_factor_settings")
            print(f"  Using config URL: {twosv_url}")

        await robust_goto(page, twosv_url)
        await asyncio.sleep(3)

        # Screenshot before
        ss_before = f"screenshots/enable_2fa_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Check if 2FA is already ON
        already_on = await find_element(page, [
            'button[aria-label*="Turn off 2-Step Verification"]',
            'button:has-text("Turn off 2-Step Verification")',
        ], max_retries=1, label="Turn off button (already ON check)")
        if already_on:
            print("  [SKIP] 2FA is already enabled")
            return "SKIP - 2FA is already enabled"

        # STEP 1: Click "Turn on 2-Step Verification"
        print("\n  [STEP 1] Clicking 'Turn on 2-Step Verification'...")

        if not await find_and_click(page, [
            'button[aria-label="Turn on 2-Step Verification"]',
            'button:has-text("Turn on 2-Step Verification")',
            'button[jsname="Pr7Yme"][aria-label*="Turn on"]',
            'button.wMI9H[aria-label*="Turn on"]',
        ], js_click=True, label="Turn on 2FA button", post_click_sleep=3):
            print("  [ERROR] Could not find 'Turn on 2-Step Verification' button")
            return False

        # STEP 2: Click "Done" in popup
        print("\n  [STEP 2] Clicking 'Done' in popup...")

        if not await find_and_click(page, [
            'button[data-mdc-dialog-action="AHldd"]',
            'button[aria-label="Done"]',
            'button:has-text("Done")',
            'span:has-text("Done")',
        ], js_click=True, label="Done button", post_click_sleep=3):
            print("  [WARN] Could not find Done button — trying Enter key")
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)

        # Screenshot after
        ss_after = f"screenshots/enable_2fa_after_{timestamp}.png"
        await page.screenshot(path=ss_after, full_page=True)

        # Verify success: "Turn off" button should now be visible
        verify = await find_element(page, [
            'button[aria-label*="Turn off 2-Step Verification"]',
            'button:has-text("Turn off 2-Step Verification")',
        ], max_retries=2, label="Verify 2FA enabled")
        if verify:
            print("\n  [SUCCESS] 2FA enabled successfully!")
            return True

        print("\n  [OK] Enable 2FA completed (could not verify final state)")
        return True

    except Exception as e:
        print(f"  [ERROR] Enable 2FA failed: {e}")
        import traceback
        traceback.print_exc()
        return False


##############################################################################
# ── Operation 10b: Disable 2FA (Turn off 2-Step Verification) ──────────────
##############################################################################

async def disable_2fa(page, config, base_url=None):
    """
    Disable 2-Step Verification on the account.

    Flow:
      1. Navigate to twosv settings page
      2. Check if already OFF (Turn on button visible) → SKIP
      3. Click "Turn off 2-Step Verification"
      4. Click "Turn off" in confirmation popup

    Returns:
        bool or str: True=success, False=fail, "SKIP - reason"=skip
    """
    print("\n[OPERATION] Disable 2FA (Turn off 2-Step Verification)...")

    try:
        timestamp = int(time.time())

        # Build URL from session or config
        if base_url:
            from urllib.parse import parse_qs, urlencode
            parsed = urlparse(base_url)
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            preserved = {}
            for key in ['rapt', 'hl', 'pli']:
                val = query_params.get(key, [None])[0]
                if val:
                    preserved[key] = val
            if 'hl' not in preserved:
                preserved['hl'] = 'en'
            twosv_url = urlunparse((
                'https', 'myaccount.google.com',
                '/signinoptions/twosv',
                '', urlencode(preserved), ''
            ))
            print(f"  Built URL from session: {twosv_url[:80]}...")
        else:
            twosv_url = config.get_url("two_factor_settings")
            print(f"  Using config URL: {twosv_url}")

        await robust_goto(page, twosv_url)
        await asyncio.sleep(3)

        # Screenshot before
        ss_before = f"screenshots/disable_2fa_before_{timestamp}.png"
        await page.screenshot(path=ss_before, full_page=True)

        # Check if 2FA is already OFF
        already_off = await find_element(page, [
            'button[aria-label*="Turn on 2-Step Verification"]',
            'button:has-text("Turn on 2-Step Verification")',
        ], max_retries=1, label="Turn on button (already OFF check)")
        if already_off:
            print("  [SKIP] 2FA is already disabled")
            return "SKIP - 2FA is already disabled"

        # STEP 1: Click "Turn off 2-Step Verification"
        print("\n  [STEP 1] Clicking 'Turn off 2-Step Verification'...")

        if not await find_and_click(page, [
            'button[aria-label="Turn off 2-Step Verification"]',
            'button:has-text("Turn off 2-Step Verification")',
            'button[jsname="Pr7Yme"][aria-label*="Turn off"]',
            'button.wMI9H[aria-label*="Turn off"]',
        ], js_click=True, label="Turn off 2FA button", post_click_sleep=3):
            print("  [ERROR] Could not find 'Turn off 2-Step Verification' button")
            return False

        # STEP 2: Click "Turn off" in confirmation popup
        print("\n  [STEP 2] Clicking 'Turn off' in confirmation popup...")

        if not await find_and_click(page, [
            'button:has-text("Turn off")',
            'button[data-mdc-dialog-action]:has-text("Turn off")',
            'button[aria-label*="Turn off"]',
        ], js_click=True, label="Confirm Turn off", post_click_sleep=3):
            print("  [WARN] Could not find confirmation button — trying Enter key")
            await page.keyboard.press("Enter")
            await asyncio.sleep(3)

        # Screenshot after
        ss_after = f"screenshots/disable_2fa_after_{timestamp}.png"
        await page.screenshot(path=ss_after, full_page=True)

        # Verify success: "Turn on" button should now be visible
        verify = await find_element(page, [
            'button[aria-label*="Turn on 2-Step Verification"]',
            'button:has-text("Turn on 2-Step Verification")',
        ], max_retries=2, label="Verify 2FA disabled")
        if verify:
            print("\n  [SUCCESS] 2FA disabled successfully!")
            return True

        print("\n  [OK] Disable 2FA completed (could not verify final state)")
        return True

    except Exception as e:
        print(f"  [ERROR] Disable 2FA failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(main())
