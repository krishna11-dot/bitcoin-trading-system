"""Setup Google Sheets Configuration Template.

This script populates your Google Sheet with the trading system configuration
in the format expected by tools.google_sheets_sync.

Run this ONCE after setting up the Google Sheets integration.
"""

import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def setup_config_sheet():
    """Populate Google Sheet with trading configuration template."""

    # Load service account credentials
    service_account_path = Path("config/service_account.json")

    if not service_account_path.exists():
        logger.error(f"Service account file not found: {service_account_path}")
        return

    # Authenticate with Google Sheets
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = Credentials.from_service_account_file(
        str(service_account_path),
        scopes=scopes
    )

    client = gspread.authorize(creds)

    # Open the spreadsheet
    sheet_url = "https://docs.google.com/spreadsheets/d/1CBPInr3_DSGTii8wX1wqQfYRHRJdLJAW1Cv5wrDHrxU/edit"
    spreadsheet = client.open_by_url(sheet_url)
    worksheet = spreadsheet.sheet1  # Use the first worksheet

    logger.info(f"Opened spreadsheet: {spreadsheet.title}")
    logger.info(f"Worksheet: {worksheet.title}")

    # Trading configuration template
    # Format: [["Parameter", "Value", "Description"], ...]
    config_data = [
        ["Parameter", "Value", "Description"],
        ["", "", ""],  # Empty row for visual separation
        ["dca_percentage", "2.0", "DCA trigger: Buy when price drops X% in 24h"],
        ["atr_multiplier", "1.5", "Stop-loss: entry_price - (X * ATR)"],
        ["strategy_mode", "dca", "Trading strategy: dca / swing / day"],
        ["time_dca_enabled", "False", "Enable time-based DCA (buy at intervals)"],
        ["time_dca_interval", "weekly", "Time DCA interval: daily / weekly / monthly"],
        ["atr_dca_enabled", "False", "Enable ATR-based DCA (volatility triggers)"],
        ["max_position_size", "0.5", "Max 50% of portfolio per trade"],
        ["global_safeguard_threshold", "0.25", "Emergency stop: close all at -25% loss"],
        ["", "", ""],  # Empty row
        ["", "", "HOW TO UPDATE:"],
        ["", "", "1. Change values in the 'Value' column"],
        ["", "", "2. System auto-syncs every hour"],
        ["", "", "3. No code deployment needed!"],
        ["", "", ""],
        ["", "", "STRATEGY MODES:"],
        ["", "", "- dca: Conservative (2.0x ATR stop-loss, 50% budget)"],
        ["", "", "- swing: Moderate (1.5x ATR stop-loss, 40% budget)"],
        ["", "", "- day: Aggressive (1.0x ATR stop-loss, 30% budget)"],
    ]

    # Clear existing content
    worksheet.clear()

    # Write configuration data
    worksheet.update("A1", config_data)

    # Format header row (bold)
    worksheet.format("A1:C1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
    })

    # Format parameter column (bold)
    worksheet.format("A3:A10", {
        "textFormat": {"bold": True}
    })

    # Auto-resize columns
    worksheet.columns_auto_resize(0, 2)

    logger.info("[OK] Google Sheet populated with configuration template!")
    logger.info(f"     View at: {sheet_url}")
    logger.info("")
    logger.info("Configuration written:")
    logger.info("  dca_percentage = 2.0")
    logger.info("  atr_multiplier = 1.5")
    logger.info("  strategy_mode = dca")
    logger.info("  time_dca_enabled = False")
    logger.info("  time_dca_interval = weekly")
    logger.info("  atr_dca_enabled = False")
    logger.info("  max_position_size = 0.5")
    logger.info("  global_safeguard_threshold = 0.25")
    logger.info("")
    logger.info("[NEXT] Test the sync with: python -m tools.google_sheets_sync")


if __name__ == "__main__":
    print("=" * 80)
    print("Setting up Google Sheets Configuration Template")
    print("=" * 80)
    print()

    try:
        setup_config_sheet()
        print()
        print("=" * 80)
        print("SUCCESS! Configuration template created in Google Sheets")
        print("=" * 80)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
