# Google Sheets Connection Fix

## Current Error
```
APIError: [403]: The caller does not have permission
```

## Root Causes
1. Google Sheets API is not enabled in your Google Cloud project
2. Sheet permissions may not be correctly configured

## Fix Step-by-Step

### Step 1: Enable Google Sheets API

1. **Open Google Cloud Console** - Visit this URL (auto-selects your project):
   ```
   https://console.cloud.google.com/apis/library/sheets.googleapis.com?project=analog-foundry-434413-i7
   ```

2. **Click "ENABLE" button** (big blue button at the top)

3. **Wait 2-3 minutes** for the API to activate

### Step 2: Verify Sheet Sharing

1. **Open your Google Sheet**:
   ```
   https://docs.google.com/spreadsheets/d/1CBPInr3_DSGTii8wX1wqQfYRHRJdLJAW1Cv5wrDHrxU/edit
   ```

2. **Click "Share" button** (top right corner)

3. **Verify this email is added** with "Editor" access:
   ```
   bitcoin-trading-bot@analog-foundry-434413-i7.iam.gserviceaccount.com
   ```

4. **If not present, add it**:
   - Click "Add people and groups"
   - Paste the email above
   - Set role to **"Editor"**
   - **UNCHECK** "Notify people" (it's a service account, won't receive emails)
   - Click "Share"

### Step 3: Test Connection

After completing Steps 1 & 2, run:
```bash
python test_google_sheets.py
```

You should see:
```
[OK] Authentication successful!
[OK] Spreadsheet opened: [Your Sheet Name]
[OK] Worksheet found: Sheet1
[OK] Read X rows
[SUCCESS] Google Sheets connection is working perfectly!
```

### Step 4: Test the Trading System Integration

Once the test passes, run:
```bash
python -m tools.google_sheets_sync
```

This should successfully fetch your configuration from Google Sheets!

---

## Troubleshooting

### If you still get permission errors:
1. Make sure you enabled the API in the CORRECT project: `analog-foundry-434413-i7`
2. Wait a few minutes after enabling the API
3. Make sure the service account email has "Editor" (not "Viewer") access
4. Try copying the service account email directly from `config/service_account.json` to avoid typos

### If you get "API not enabled" error:
1. You need to enable Google Sheets API in Google Cloud Console
2. The link in Step 1 will take you directly there
3. Make sure you're logged into the correct Google account that owns the project
