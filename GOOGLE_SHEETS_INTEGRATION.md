# Google Sheets Integration - Complete

**Status**: ACTIVE

The system now loads trading configuration from Google Sheets with automatic fallback to local defaults.

---

## How It Works

### Configuration Hierarchy

1. **Google Sheets** (if available) - Dynamic config loaded at the start of each trading cycle
2. **Local Defaults** (fallback) - Hardcoded values in [main.py:175-182](main.py#L175-L182)

### Config Mapping

| Google Sheets Field | Internal Config Key | Description |
|---------------------|---------------------|-------------|
| `dca_percentage` | `dca_threshold` | Price drop % that triggers DCA buy |
| `atr_multiplier` | `atr_multiplier` | ATR multiplier for stop-loss calculation |
| `max_position_size` | `max_position_size` | Max % of portfolio per trade (0.0-1.0) |
| `global_safeguard_threshold` | `emergency_stop` | Emergency stop loss % (0.0-1.0) |

---

## Setup Instructions

### 1. Create Google Sheet

Create a spreadsheet with this structure:

| Parameter | Value |
|-----------|-------|
| dca_percentage | 1.5 |
| atr_multiplier | 1.5 |
| max_position_size | 0.2 |
| global_safeguard_threshold | 0.25 |

**Note**: The first row is a header and will be skipped.

### 2. Create Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google Sheets API
4. Create a Service Account:
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "bitcoin-trading-bot")
   - Click "Create and Continue"
   - Skip role assignment (click "Continue")
   - Click "Done"
5. Generate credentials:
   - Click on the service account you just created
   - Go to "Keys" tab
   - Click "Add Key" → "Create new key"
   - Choose JSON format
   - Download the file

### 3. Share Your Google Sheet

1. Open your Google Sheet
2. Click "Share" button
3. Share with the service account email (looks like `bitcoin-trading-bot@project-name.iam.gserviceaccount.com`)
4. Give it "Editor" permissions
5. Copy the Google Sheet URL

### 4. Configure Environment

Add these to your `.env` file:

```bash
# Google Sheets Configuration (optional)
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit
```

Save the service account JSON file as:
```
config/service_account.json
```

### 5. Install Dependencies

If not already installed:
```bash
pip install gspread
```

---

## Testing

### Test Google Sheets Connection

```bash
python tools/google_sheets_sync.py
```

Expected output:
```
[OK] Google Sheets client initialized: Your Sheet Name
Configuration:
  dca_percentage               = 1.5
  atr_multiplier               = 1.5
  max_position_size            = 0.2
  global_safeguard_threshold   = 0.25
```

### Run System

```bash
python main.py
```

Look for these logs:
```
[CONFIG] Initializing Google Sheets sync...
[OK] Google Sheets sync initialized: GoogleSheetsSync(status=connected, cache=config/sheets_cache.json)
[SYSTEM] AUTONOMOUS BITCOIN TRADING SYSTEM
Configuration: Google Sheets (with local fallback)

[STARTING] TRADING CYCLE #1
[CONFIG] Loading configuration from Google Sheets...
[OK] Configuration loaded from Google Sheets
   DCA Threshold: 1.5%
   ATR Multiplier: 1.5x
   Max Position: 20.0%
```

---

## Fallback Behavior

The system is designed to NEVER crash due to Google Sheets issues:

| Scenario | Behavior |
|----------|----------|
| Google Sheets URL not configured | Uses local defaults, logs warning |
| Service account file missing | Uses local defaults, logs warning |
| Network error during fetch | Uses cached config, logs warning |
| Rate limit (429 error) | Retries with exponential backoff (up to 5 attempts) |
| Invalid configuration in sheet | Uses local defaults, logs error |
| All retries fail | Uses cached config from last successful fetch |
| Cache file missing | Uses local defaults |

---

## Dynamic Configuration Updates

**How to Update Config Without Restarting**:

1. Edit values in your Google Sheet
2. Save the sheet
3. Wait for next trading cycle (system fetches config at start of each cycle)
4. Changes will be applied automatically

**Example**: If you want to make DCA more aggressive during a market dip:
- Change `dca_percentage` from `1.5` to `1.0` in Google Sheets
- Save
- Next cycle will use the new 1.0% threshold

---

## Caching

The system maintains a local cache at `config/sheets_cache.json`:

- **Updated**: After every successful fetch from Google Sheets
- **Used**: When Google Sheets is unavailable (network error, rate limit, etc.)
- **Atomic Writes**: Uses temp file pattern to prevent corruption

Cache file example:
```json
{
  "dca_percentage": 1.5,
  "atr_multiplier": 1.5,
  "max_position_size": 0.2,
  "global_safeguard_threshold": 0.25,
  "strategy_mode": "dca",
  "time_dca_enabled": false,
  "time_dca_interval": "weekly",
  "atr_dca_enabled": false
}
```

---

## Rate Limits

Google Sheets API limits:
- **60 reads/minute per user**
- Our usage: **1 read per 30 minutes** (0.0333 reads/min)
- **Safety margin**: 1,800x under limit

Even with retries (5 attempts max), we'll never hit rate limits.

---

## Files Modified

1. [main.py:19](main.py#L19) - Import GoogleSheetsSync
2. [main.py:145](main.py#L145) - Updated run_one_cycle signature to accept sheets_sync
3. [main.py:185-211](main.py#L185-L211) - Load config from Google Sheets with fallback
4. [main.py:370-378](main.py#L370-L378) - Initialize GoogleSheetsSync in main()
5. [main.py:411](main.py#L411) - Pass sheets_sync to run_one_cycle

---

## Security Best Practices

- Service account credentials stored locally in `config/service_account.json`
- **NEVER commit** `service_account.json` to Git
- Add to `.gitignore`:
  ```
  config/service_account.json
  config/sheets_cache.json
  ```
- Use restrictive file permissions:
  ```bash
  chmod 600 config/service_account.json  # Linux/Mac
  ```
- Service account should only have access to this specific Google Sheet

---

## Troubleshooting

### Error: "Service account file not found"
**Solution**: Download service account JSON and place at `config/service_account.json`

### Error: "Failed to open spreadsheet"
**Solution**: Make sure you shared the Google Sheet with the service account email

### Warning: "gspread not installed"
**Solution**: Run `pip install gspread`

### "Using cache/defaults only"
**Solution**: Check:
1. Is `GOOGLE_SHEET_URL` set in `.env`?
2. Does `config/service_account.json` exist?
3. Is the sheet shared with service account?

---

## Advanced: Multiple Environments

You can use different Google Sheets for different environments:

```bash
# .env.production
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/PROD_SHEET_ID/edit

# .env.staging
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/STAGING_SHEET_ID/edit
```

This allows you to:
- Test aggressive strategies in staging
- Keep conservative strategies in production
- A/B test different configurations

---

## Next Steps

1. Create your Google Sheet
2. Set up service account
3. Add credentials to `config/service_account.json`
4. Add `GOOGLE_SHEET_URL` to `.env`
5. Test with `python tools/google_sheets_sync.py`
6. Run `python main.py` and verify logs show "Configuration: Google Sheets"

**That's it!** Your system is now dynamically configured via Google Sheets.
