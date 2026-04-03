"""
Setup script for Gmail Bot
Helps initialize the project and create template files
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils import ConfigManager, FileManager
from src.excel_processor import ExcelProcessor


def setup():
    """Run initial setup"""
    print("=" * 70)
    print("GMAIL BOT - SETUP")
    print("=" * 70)
    print()

    # Step 1: Create directories
    print("Step 1: Creating directory structure...")
    FileManager.ensure_directories()
    print("[OK] Directories created")
    print()

    # Step 2: Create Excel template
    print("Step 2: Creating Excel template...")
    config = ConfigManager()
    excel = ExcelProcessor(config)
    excel.create_template("input/template.xlsx")
    print("[OK] Template created at: input/template.xlsx")
    print()

    # Step 3: Instructions
    print("=" * 70)
    print("SETUP COMPLETE!")
    print("=" * 70)
    print()
    print("Next steps:")
    print()
    print("1. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("   playwright install chromium")
    print()
    print("2. Copy template to accounts file:")
    print("   Copy input/template.xlsx to input/accounts.xlsx")
    print()
    print("3. Fill in your account details in accounts.xlsx")
    print()
    print("4. Update config/urls.json with your bypass URLs")
    print()
    print("5. Run the bot:")
    print("   python run.py")
    print()
    print("=" * 70)
    print("Read QUICKSTART.md for detailed instructions!")
    print("=" * 70)


if __name__ == "__main__":
    try:
        setup()
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
