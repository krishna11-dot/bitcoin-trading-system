"""Verify Google Sheets setup step-by-step."""
import os
import gspread
from pathlib import Path
from dotenv import load_dotenv

print("="*80)
print("GOOGLE SHEETS SETUP VERIFICATION")
print("="*80)

# Step 1: Check files
print("\n[STEP 1] Checking required files...")
load_dotenv()

service_account_path = Path("config/service_account.json")
if service_account_path.exists():
    print("[OK] Service account file found")
else:
    print("[FAIL] Service account file MISSING")
    exit(1)

sheet_url = os.getenv("GOOGLE_SHEET_URL")
if sheet_url:
    print(f"[OK] Google Sheet URL configured: {sheet_url}")
else:
    print("[FAIL] GOOGLE_SHEET_URL not set in .env")
    exit(1)

# Step 2: Check credentials
print("\n[STEP 2] Checking service account credentials...")
try:
    import json
    with open(service_account_path) as f:
        creds = json.load(f)

    email = creds.get("client_email")
    project_id = creds.get("project_id")

    if email:
        print(f"[OK] Service account email: {email}")
    else:
        print("[FAIL] No client_email in service account file")
        exit(1)

    if project_id:
        print(f"[OK] Project ID: {project_id}")
    else:
        print("[FAIL] No project_id in service account file")
        exit(1)

except Exception as e:
    print(f"[FAIL] Error reading service account file: {e}")
    exit(1)

# Step 3: Test authentication
print("\n[STEP 3] Testing Google Cloud authentication...")
try:
    client = gspread.service_account(filename=str(service_account_path))
    print("[OK] Authentication successful!")
except Exception as e:
    print(f"[FAIL] Authentication failed: {e}")
    exit(1)

# Step 4: Test API access
print("\n[STEP 4] Testing Google Sheets API access...")
try:
    spreadsheet = client.open_by_url(sheet_url)
    print(f"[OK] Successfully opened spreadsheet: {spreadsheet.title}")
except PermissionError:
    # This wraps the underlying APIError
    print("[FAIL] Permission denied - 403 Error")
    print("\nPOSSIBLE CAUSES:")
    print("  1. Google Sheets API is not enabled in your project")
    print("  2. The spreadsheet is not shared with the service account")
    print("\nFIX STEPS:")
    print(f"\n  Step A: Enable Google Sheets API")
    print(f"  ----------------------------------------")
    print(f"  Visit: https://console.cloud.google.com/apis/library/sheets.googleapis.com?project={project_id}")
    print(f"  Click 'ENABLE' button")
    print(f"  Wait 2-3 minutes for activation")
    print(f"\n  Step B: Share the spreadsheet")
    print(f"  ----------------------------------------")
    print(f"  1. Open: {sheet_url}")
    print(f"  2. Click 'Share' button (top right)")
    print(f"  3. Add this email with 'Editor' access:")
    print(f"     {email}")
    print(f"  4. Uncheck 'Notify people' (it's a service account)")
    print(f"  5. Click 'Share'")
    print(f"\n  After completing BOTH steps, run this script again.")
    exit(1)
except gspread.exceptions.APIError as e:
    print(f"[FAIL] API Error: {e}")
    exit(1)
except Exception as e:
    print(f"[FAIL] Unexpected error: {type(e).__name__}: {str(e)}")
    import traceback
    traceback.print_exc()
    exit(1)

# Step 5: Test reading data
print("\n[STEP 5] Testing data access...")
try:
    worksheet = spreadsheet.get_worksheet(0)
    print(f"[OK] Accessed worksheet: {worksheet.title}")

    all_values = worksheet.get_all_values()
    print(f"[OK] Read {len(all_values)} rows from spreadsheet")

    if len(all_values) > 0:
        print(f"\nFirst row: {all_values[0]}")
        if len(all_values) > 1:
            print(f"Second row: {all_values[1]}")

except Exception as e:
    print(f"[FAIL] Error reading data: {e}")
    exit(1)

# Success!
print("\n" + "="*80)
print("SUCCESS! Google Sheets is configured correctly and working!")
print("="*80)
print("\nYou can now run: python -m tools.google_sheets_sync")
