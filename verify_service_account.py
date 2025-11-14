"""Comprehensive Service Account Verification and Google Sheets API Test."""
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

print("="*80)
print("SERVICE ACCOUNT & GOOGLE SHEETS API VERIFICATION")
print("="*80)

# Load environment variables
load_dotenv()

# Step 1: Verify JSON file exists and is readable
print("\n[STEP 1] Checking service account JSON file...")
service_account_path = Path("config/service_account.json")

if not service_account_path.exists():
    print(f"[ERROR] Service account file not found: {service_account_path}")
    print("\nPlease ensure:")
    print("  1. You downloaded the JSON file from Google Cloud Console")
    print("  2. You saved it as 'config/service_account.json'")
    sys.exit(1)

print(f"[OK] File exists: {service_account_path}")
print(f"     File size: {service_account_path.stat().st_size} bytes")

# Step 2: Parse and validate JSON structure
print("\n[STEP 2] Parsing service account JSON...")
try:
    with open(service_account_path, 'r') as f:
        sa_data = json.load(f)
    print("[OK] Valid JSON format")
except json.JSONDecodeError as e:
    print(f"[ERROR] Invalid JSON: {e}")
    sys.exit(1)

# Step 3: Check required fields
print("\n[STEP 3] Validating service account fields...")
required_fields = {
    'type': 'service_account',
    'project_id': None,
    'private_key_id': None,
    'private_key': None,
    'client_email': None,
    'client_id': None,
    'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
    'token_uri': 'https://oauth2.googleapis.com/token',
}

all_valid = True
for field, expected_value in required_fields.items():
    if field not in sa_data:
        print(f"[ERROR] Missing required field: {field}")
        all_valid = False
    elif expected_value and sa_data[field] != expected_value:
        print(f"[WARNING] Unexpected value for {field}: {sa_data[field]}")
    else:
        print(f"[OK] {field}: {'<present>' if expected_value is None else expected_value}")

if not all_valid:
    print("\n[ERROR] Invalid service account JSON structure")
    sys.exit(1)

# Step 4: Display service account details
print("\n[STEP 4] Service Account Details...")
print(f"  Email: {sa_data['client_email']}")
print(f"  Project ID: {sa_data['project_id']}")
print(f"  Client ID: {sa_data['client_id']}")
print(f"  Private Key ID: {sa_data['private_key_id'][:20]}...")

# Step 5: Check Google Sheets URL
print("\n[STEP 5] Checking Google Sheets configuration...")
sheet_url = os.getenv("GOOGLE_SHEET_URL")
if not sheet_url:
    print("[ERROR] GOOGLE_SHEET_URL not set in .env file")
    sys.exit(1)

print(f"[OK] Sheet URL: {sheet_url}")

# Extract sheet ID
if "/d/" in sheet_url:
    sheet_id = sheet_url.split("/d/")[1].split("/")[0]
    print(f"[OK] Sheet ID: {sheet_id}")
else:
    print("[ERROR] Invalid Google Sheets URL format")
    sys.exit(1)

# Step 6: Test Google API authentication
print("\n[STEP 6] Testing Google API authentication...")
try:
    import gspread
    from google.auth.exceptions import RefreshError
    print("[OK] Required packages installed")
except ImportError as e:
    print(f"[ERROR] Missing package: {e}")
    print("\nRun: pip install gspread google-auth")
    sys.exit(1)

try:
    client = gspread.service_account(filename=str(service_account_path))
    print("[OK] Service account credentials loaded")
except Exception as e:
    print(f"[ERROR] Failed to load credentials: {e}")
    sys.exit(1)

# Step 7: Test API access
print("\n[STEP 7] Testing Google Sheets API access...")
print(f"  Attempting to access spreadsheet...")

try:
    spreadsheet = client.open_by_url(sheet_url)
    print(f"[SUCCESS] Spreadsheet opened: {spreadsheet.title}")

    # Get worksheets
    worksheets = spreadsheet.worksheets()
    print(f"[SUCCESS] Found {len(worksheets)} worksheet(s):")
    for i, ws in enumerate(worksheets, 1):
        print(f"  {i}. {ws.title} ({ws.row_count} rows x {ws.col_count} cols)")

    # Read some data
    if worksheets:
        ws = worksheets[0]
        data = ws.get_all_values()
        print(f"\n[SUCCESS] Read {len(data)} rows from '{ws.title}'")
        if data:
            print(f"\nFirst 3 rows:")
            for i, row in enumerate(data[:3], 1):
                print(f"  Row {i}: {row}")

    print("\n" + "="*80)
    print("[SUCCESS] GOOGLE SHEETS API IS WORKING CORRECTLY!")
    print("="*80)
    print("\nNo errors detected. Your setup is complete.")

except gspread.exceptions.APIError as e:
    print(f"[ERROR] Google API Error")
    error_code = e.response.status_code if hasattr(e, 'response') else 'Unknown'
    print(f"  Status Code: {error_code}")

    if error_code == 403:
        print("\n[SOLUTION] 403 Forbidden Error - Permission Issue:")
        print(f"  1. Open your Google Sheet: {sheet_url}")
        print(f"  2. Click 'Share' button (top right)")
        print(f"  3. Add this email with 'Editor' access:")
        print(f"     {sa_data['client_email']}")
        print(f"  4. Click 'Send' (uncheck 'Notify people')")

    elif error_code == 404:
        print("\n[SOLUTION] 404 Not Found - Spreadsheet doesn't exist or not shared:")
        print(f"  1. Verify the URL is correct: {sheet_url}")
        print(f"  2. Make sure the spreadsheet exists")
        print(f"  3. Share it with: {sa_data['client_email']}")

    print(f"\nFull error: {e}")
    sys.exit(1)

except RefreshError as e:
    print(f"[ERROR] Authentication Failed - Invalid Service Account")
    print(f"  Error: {e}")
    print("\n[SOLUTION] Service Account Not Found or Disabled:")
    print(f"  This error means Google cannot find the service account.")
    print(f"  Your service account email: {sa_data['client_email']}")
    print(f"  Your project ID: {sa_data['project_id']}")
    print("\n  PLEASE DO THE FOLLOWING:")
    print(f"  1. Go to Google Cloud Console:")
    print(f"     https://console.cloud.google.com/iam-admin/serviceaccounts?project={sa_data['project_id']}")
    print(f"  2. Check if the service account exists:")
    print(f"     {sa_data['client_email']}")
    print(f"  3. If it doesn't exist, you need to:")
    print(f"     a. Create a NEW service account")
    print(f"     b. Enable Google Sheets API")
    print(f"     c. Download NEW JSON key")
    print(f"     d. Replace config/service_account.json with the new file")
    print(f"  4. If it exists but is disabled, enable it")
    print(f"  5. Make sure Google Sheets API is enabled:")
    print(f"     https://console.cloud.google.com/apis/library/sheets.googleapis.com?project={sa_data['project_id']}")
    sys.exit(1)

except gspread.exceptions.SpreadsheetNotFound:
    print(f"[ERROR] Spreadsheet Not Found")
    print(f"\n[SOLUTION] The spreadsheet hasn't been shared with the service account:")
    print(f"  1. Open your Google Sheet: {sheet_url}")
    print(f"  2. Click 'Share' button")
    print(f"  3. Add this email: {sa_data['client_email']}")
    print(f"  4. Give it 'Editor' or 'Viewer' access")
    print(f"  5. Click 'Send'")
    sys.exit(1)

except Exception as e:
    print(f"[ERROR] Unexpected Error: {type(e).__name__}")
    print(f"  Message: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
