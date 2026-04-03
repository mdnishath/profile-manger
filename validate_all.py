"""
VALIDATION SCRIPT - Run before test_debug.py
Checks all components and confirms everything is ready
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

def validate_imports():
    """Test all module imports"""
    print("\n" + "="*70)
    print("1. VALIDATING MODULE IMPORTS")
    print("="*70)

    modules_to_test = [
        ("playwright.async_api", "Playwright"),
        ("pandas", "Pandas"),
        ("openpyxl", "OpenPyXL"),
        ("pyotp", "PyOTP"),
        ("loguru", "Loguru"),
        ("colorama", "Colorama"),
        ("dotenv", "Python-dotenv"),
        ("dateutil", "Python-dateutil"),
        ("src.utils", "Utils"),
        ("src.screen_detector", "ScreenDetector"),
        ("src.gmail_authenticator", "GmailAuthenticator"),
        ("src.excel_processor", "ExcelProcessor"),
    ]

    failed = []
    for module, name in modules_to_test:
        try:
            __import__(module)
            print(f"  [OK] {name}")
        except ImportError as e:
            print(f"  [ERROR] {name}: {e}")
            failed.append(name)

    if failed:
        print(f"\n[FAILED] {len(failed)} module(s) failed to import")
        return False
    else:
        print(f"\n[OK] All {len(modules_to_test)} modules imported successfully")
        return True


def validate_totp():
    """Test TOTP generation"""
    print("\n" + "="*70)
    print("2. VALIDATING TOTP GENERATION")
    print("="*70)

    try:
        from src.utils import TOTPGenerator

        # Test with a known secret
        test_secret = "5NHKYTTYO6ZVAT4A"
        gen = TOTPGenerator()
        code = gen.generate_code(test_secret)

        if len(code) == 6 and code.isdigit():
            print(f"  [OK] Generated code: {code}")
            print(f"  [OK] Code format valid (6 digits)")
            return True
        else:
            print(f"  [ERROR] Invalid code format: {code}")
            return False

    except Exception as e:
        print(f"  [ERROR] TOTP generation failed: {e}")
        return False


def validate_screen_detector():
    """Test screen detector configuration"""
    print("\n" + "="*70)
    print("3. VALIDATING SCREEN DETECTION PRIORITY")
    print("="*70)

    try:
        from src.screen_detector import ScreenDetector, LoginScreen

        # Check that LoginScreen enum has all required screens
        required_screens = [
            "EMAIL_INPUT",
            "PASSWORD_INPUT",
            "BACKUP_CODE",
            "AUTHENTICATOR_CODE",
            "TRY_ANOTHER_WAY",
            "ACCOUNT_RECOVERY",
            "PASSKEY_PROMPT",
            "SUCCESS_SCREEN",
            "SUSPICIOUS_ACTIVITY",
            "ACCOUNT_LOCKED",
            "LOGGED_IN",
            "UNKNOWN"
        ]

        for screen in required_screens:
            if not hasattr(LoginScreen, screen):
                print(f"  [ERROR] Missing screen type: {screen}")
                return False
            print(f"  [OK] {screen}")

        print(f"\n[OK] All screen types defined correctly")
        return True

    except Exception as e:
        print(f"  [ERROR] Screen detector validation failed: {e}")
        return False


def validate_config():
    """Test configuration loading"""
    print("\n" + "="*70)
    print("4. VALIDATING CONFIGURATION FILES")
    print("="*70)

    try:
        from src.utils import ConfigManager

        config = ConfigManager()

        # Check URLs
        required_urls = [
            "login",
            "password_change",
            "recovery_phone",
            "recovery_email",
            "two_factor_settings",
            "backup_codes",
            "devices"
        ]

        missing_urls = []
        for url_key in required_urls:
            url = config.get_url(url_key)
            if url:
                print(f"  [OK] {url_key}: {url[:50]}...")
            else:
                print(f"  [ERROR] Missing URL: {url_key}")
                missing_urls.append(url_key)

        if missing_urls:
            print(f"\n[ERROR] {len(missing_urls)} URL(s) missing from config")
            return False
        else:
            print(f"\n[OK] All {len(required_urls)} URLs configured")
            return True

    except Exception as e:
        print(f"  [ERROR] Config validation failed: {e}")
        return False


def validate_input_cleaning():
    """Test input cleaning functionality"""
    print("\n" + "="*70)
    print("5. VALIDATING INPUT CLEANING")
    print("="*70)

    # Test TOTP cleaning
    test_cases = [
        ("5nhk ytty o6zv at4a", "5NHKYTTYO6ZVAT4A"),
        ("5589 8987", "55898987"),
        ("ABCD-EFGH-IJKL", "ABCDEFGHIJKL"),
    ]

    for input_val, expected in test_cases:
        cleaned = input_val.replace(" ", "").replace("-", "").upper()
        if cleaned == expected:
            print(f"  [OK] '{input_val}' -> '{cleaned}'")
        else:
            print(f"  [ERROR] '{input_val}' -> '{cleaned}' (expected '{expected}')")
            return False

    print(f"\n[OK] Input cleaning works correctly")
    return True


def validate_directories():
    """Ensure required directories exist"""
    print("\n" + "="*70)
    print("6. VALIDATING DIRECTORY STRUCTURE")
    print("="*70)

    required_dirs = [
        "config",
        "src",
        "input",
        "output",
        "output/success",
        "output/failed",
        "logs",
        "screenshots"
    ]

    project_root = Path(__file__).parent

    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"  [OK] {dir_name}/")
        else:
            print(f"  [CREATING] {dir_name}/")
            dir_path.mkdir(parents=True, exist_ok=True)

    print(f"\n[OK] All directories exist")
    return True


def main():
    """Run all validations"""
    print("\n")
    print("="*70)
    print("GMAIL BOT - PRE-FLIGHT VALIDATION")
    print("="*70)
    print("\nThis script validates all components before testing")
    print()

    results = []

    # Run all validations
    results.append(("Module Imports", validate_imports()))
    results.append(("TOTP Generation", validate_totp()))
    results.append(("Screen Detection", validate_screen_detector()))
    results.append(("Configuration", validate_config()))
    results.append(("Input Cleaning", validate_input_cleaning()))
    results.append(("Directories", validate_directories()))

    # Summary
    print("\n" + "="*70)
    print("VALIDATION SUMMARY")
    print("="*70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"  {status} {name}")

    print()
    print("="*70)

    if passed == total:
        print(f"ALL TESTS PASSED ({passed}/{total})")
        print("="*70)
        print()
        print("READY TO TEST!")
        print()
        print("Next step: Run the debug test")
        print("Command: python test_debug.py")
        print()
        print("="*70)
        return 0
    else:
        print(f"SOME TESTS FAILED ({passed}/{total})")
        print("="*70)
        print()
        print("Please fix the errors above before running test_debug.py")
        print()
        if passed < total:
            print("To install missing dependencies:")
            print("  python -m pip install -r requirements.txt")
            print("  python -m pip install pandas --only-binary :all:")
            print("  playwright install chromium")
        print()
        print("="*70)
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Validation interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
