"""
Create a template Excel file for the simplified Gmail Bot
Only 3-4 columns needed! Operations are selected in UI.
"""

import pandas as pd
from pathlib import Path

# Create template data - ONLY 3-4 columns needed!
template_data = {
    'Email': [
        'example1@gmail.com',
        'example2@gmail.com',
        'example3@gmail.com'
    ],
    'Password': [
        'CurrentPassword123',
        'MyOldPass456',
        'AnotherPass789'
    ],
    'TOTP Secret': [
        'jbswy 3dpeh pk3pxp',
        'abcd efgh ijkl mnop',
        'xyz1 234p qrst 567u'
    ],
    'Name': [
        'John Smith',
        'Emma Wilson',
        ''  # Name is optional
    ]
}

df = pd.DataFrame(template_data)

# Create input folder
Path('input').mkdir(exist_ok=True)

# Save template
output_file = 'input/template_simple.xlsx'
df.to_excel(output_file, index=False, sheet_name='Accounts')

print("=" * 70)
print("SIMPLIFIED TEMPLATE CREATED!")
print("=" * 70)
print(f"\nFile: {output_file}")
print("\nRequired Columns (Only 3!):")
print("  * Email          - Gmail address")
print("  * Password       - Current password")
print("  * TOTP Secret    - Google Authenticator key (spaces optional)")
print("\nOptional Column:")
print("  * Name           - Full name (only if you want to change name)")
print("\nWhat's Different?")
print("  [X] NO 'Operations' column - Select operations in UI with checkboxes!")
print("  [X] NO 'New Password' column - Enter once in UI, used for all accounts")
print("  [X] NO 'Recovery Email/Phone' columns - Enter once in UI")
print("  [+] Just 3-4 simple columns!")
print("\nNext Steps:")
print("  1. Edit the template file with your accounts")
print("  2. Run: python gmail_bot_simple.py")
print("  3. Select operations with checkboxes in UI")
print("  4. Enter common settings (new password, etc.)")
print("  5. Click 'Start Processing'")
print("\nStatus Column:")
print("  * Empty status is automatically marked as PENDING")
print("  * Bot processes all PENDING accounts")
print("  * After processing: SUCCESS (green) or FAILED (red)")
print("\n" + "=" * 70)
