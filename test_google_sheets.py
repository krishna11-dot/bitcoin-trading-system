"""Test Google Sheets connection with detailed error reporting."""
import gspread
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get configuration
service_account_path = Path("config/service_account.json")
sheet_url = os.getenv("GOOGLE_SHEET_URL")

print(f"Service account file: {service_account_path}")
print(f"Service account exists: {service_account_path.exists()}")
print(f"Google Sheet URL: {sheet_url}")
print("\n" + "="*80)

try:
    print("\nAttempting to authenticate...")
    client = gspread.service_account(filename=str(service_account_path))
    print("[OK] Authentication successful!")

    print("\nAttempting to open spreadsheet...")
    spreadsheet = client.open_by_url(sheet_url)
    print(f"[OK] Spreadsheet opened: {spreadsheet.title}")

    print("\nAttempting to read worksheet...")
    worksheet = spreadsheet.get_worksheet(0)
    print(f"[OK] Worksheet found: {worksheet.title}")

    print("\nAttempting to read data...")
    all_values = worksheet.get_all_values()
    print(f"[OK] Read {len(all_values)} rows")

    print("\nFirst 5 rows:")
    for i, row in enumerate(all_values[:5], 1):
        print(f"  Row {i}: {row}")

    print("\n" + "="*80)
    print("[SUCCESS] Google Sheets connection is working perfectly!")
    print("="*80)

except FileNotFoundError as e:
    print(f"[ERROR] Service account file not found: {e}")

except gspread.exceptions.APIError as e:
    print(f"[ERROR] Google Sheets API error: {e}")
    print(f"  Status code: {e.response.status_code if hasattr(e, 'response') else 'N/A'}")
    print(f"  Error details: {e.response.json() if hasattr(e, 'response') else 'N/A'}")

except gspread.exceptions.SpreadsheetNotFound:
    print(f"[ERROR] Spreadsheet not found!")
    print(f"  Make sure you've shared the spreadsheet with:")
    print(f"  bitcoin-trading-bot@analog-foundry-434413-i7.iam.gserviceaccount.com")

except Exception as e:
    print(f"[ERROR] Unexpected error: {type(e).__name__}")
    print(f"  Message: {e}")
    import traceback
    print(f"\nFull traceback:")
    traceback.print_exc()
