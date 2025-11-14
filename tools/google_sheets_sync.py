"""Google Sheets Configuration Sync.

This module synchronizes trading system configuration from Google Sheets with
multi-level fallback and bulletproof error handling.

Why Google Sheets?
- Real-time strategy adjustments without code changes
- Easy to update from mobile/anywhere
- Built-in version history
- No deployment needed for config changes

Fetch Strategy:
- Fetch every hour = 24 requests/day
- Google Sheets API limit: 60 reads/min per user
- Our usage: 0.0167 calls/min (3,600x under limit!)
- Even with retries, we'll never hit rate limits

Fallback Hierarchy:
1. Try fetch from Google Sheets (with rate limiting)
2. On 429 error: Exponential backoff (up to 5 retries)
3. On timeout/network error: Use local cache
4. On cache miss: Use default configuration
5. On success: Sync to local cache for offline operation

Example:
    >>> from tools.google_sheets_sync import GoogleSheetsSync
    >>>
    >>> sheets = GoogleSheetsSync()
    >>> config = sheets.get_config()  # Tries Sheets, falls back to cache
    >>> print(f"DCA percentage: {config['dca_percentage']}%")
    >>>
    >>> # Force refresh from Sheets
    >>> config = sheets.get_config(force_refresh=True)
"""

import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import gspread
    from gspread.exceptions import APIError, GSpreadException
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False
    logging.warning("gspread not installed. Google Sheets sync will use cache/defaults only.")

from config.settings import Settings
from tools.rate_limiter import google_sheets_rate_limit


logger = logging.getLogger(__name__)


# ============================================================================
# Default Configuration
# ============================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    "dca_percentage": 2.0,
    "atr_multiplier": 1.5,
    "strategy_mode": "dca",
    "time_dca_enabled": False,
    "time_dca_interval": "weekly",
    "atr_dca_enabled": False,
    "max_position_size": 0.5,
    "global_safeguard_threshold": 0.25,
}


# ============================================================================
# Google Sheets Sync Client
# ============================================================================


class GoogleSheetsSyncError(Exception):
    """Base exception for Google Sheets sync errors."""
    pass


class GoogleSheetsSync:
    """Synchronize trading configuration from Google Sheets.

    This class manages fetching, validating, and caching trading configuration
    from a Google Sheets document. It implements exponential backoff for rate
    limit errors and provides multi-level fallback to ensure the system always
    has valid configuration.

    Attributes:
        sheet_url: Google Sheets document URL
        cache_file: Path to local cache JSON file
        service_account_path: Path to service account credentials JSON

    Example:
        >>> sheets = GoogleSheetsSync()
        >>> config = sheets.get_config()
        >>> if config['time_dca_enabled']:
        ...     print(f"Time-based DCA: {config['time_dca_interval']}")
    """

    def __init__(
        self,
        sheet_url: Optional[str] = None,
        cache_file: str = "config/sheets_cache.json",
        service_account_path: str = "config/service_account.json",
    ):
        """Initialize Google Sheets sync client.

        Args:
            sheet_url: Google Sheets URL (defaults to GOOGLE_SHEET_URL env var)
            cache_file: Path to local cache file
            service_account_path: Path to service account credentials

        Raises:
            GoogleSheetsSyncError: If gspread not available or credentials invalid
        """
        settings = Settings.get_instance()

        self.sheet_url = sheet_url or settings.GOOGLE_SHEET_URL
        self.cache_file = Path(cache_file)
        self.service_account_path = Path(service_account_path)

        # Ensure cache directory exists
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Initialize gspread client if available
        self.client = None
        self.spreadsheet = None

        if GSPREAD_AVAILABLE:
            self._initialize_client()
        else:
            logger.warning(
                "[WARN] gspread not installed. Install with: pip install gspread"
            )
            logger.info(" Using cache/defaults only for configuration")

    def _initialize_client(self) -> None:
        """Initialize gspread client with service account credentials.

        Raises:
            GoogleSheetsSyncError: If credentials invalid or sheet not accessible
        """
        if not self.service_account_path.exists():
            logger.warning(
                f"[WARN] Service account file not found: {self.service_account_path}"
            )
            logger.info(" Using cache/defaults only for configuration")
            return

        if not self.sheet_url:
            logger.warning("[WARN] GOOGLE_SHEET_URL not configured in .env")
            logger.info(" Using cache/defaults only for configuration")
            return

        try:
            # Authenticate with service account
            self.client = gspread.service_account(filename=str(self.service_account_path))

            # Open spreadsheet by URL
            self.spreadsheet = self.client.open_by_url(self.sheet_url)

            logger.info(f"[OK] Google Sheets client initialized: {self.spreadsheet.title}")

        except FileNotFoundError:
            logger.error(f"[FAIL] Service account file not found: {self.service_account_path}")
            self.client = None

        except Exception as e:
            logger.error(f"[FAIL] Failed to initialize Google Sheets client: {e}")
            self.client = None

    @google_sheets_rate_limit
    def fetch_config(self) -> Dict[str, Any]:
        """Fetch configuration from Google Sheets with exponential backoff.

        This method implements a robust retry strategy for handling rate limits
        and transient errors:
        - 429 errors: Exponential backoff with jitter
        - Timeouts: Log and fall back to cache
        - Network errors: Fall back to cache
        - Validation errors: Use previous valid config

        Backoff Formula:
            wait_time = min((2^attempt) + random(0-1000ms), 64 seconds)

        Returns:
            Dict: Validated configuration dictionary

        Raises:
            GoogleSheetsSyncError: If fetch fails after all retries
        """
        if not GSPREAD_AVAILABLE or not self.client or not self.spreadsheet:
            logger.warning(" Google Sheets not available, using cache")
            return self.load_from_cache()

        max_retries = 5
        base_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                logger.info(
                    f" Fetching config from Google Sheets (attempt {attempt + 1}/{max_retries})"
                )

                # Get first worksheet
                worksheet = self.spreadsheet.get_worksheet(0)

                # Fetch all values (expects 2 columns: Parameter, Value)
                all_values = worksheet.get_all_values()

                if not all_values:
                    raise GoogleSheetsSyncError("Spreadsheet is empty")

                # Parse values into dict
                raw_config = {}
                for row in all_values:
                    if len(row) >= 2 and row[0] and row[1]:
                        # Skip header row
                        if row[0].lower() in ["parameter", "parameter name", "name"]:
                            continue
                        # Add to config
                        raw_config[row[0].strip()] = row[1].strip()

                logger.debug(f"[DATA] Parsed {len(raw_config)} parameters from sheet")

                # Convert types
                config = self._convert_types(raw_config)

                # Validate configuration
                if not self._validate_config(config):
                    logger.error("[FAIL] Configuration validation failed")
                    raise GoogleSheetsSyncError("Invalid configuration")

                logger.info(f"[OK] Successfully fetched config from Google Sheets")
                return config

            except APIError as e:
                # Handle rate limit errors (429) with exponential backoff
                if e.response.status_code == 429:
                    # Calculate backoff with exponential growth + jitter
                    jitter = random.uniform(0, 1)
                    wait_time = min((2 ** attempt) * base_delay + jitter, 64)

                    logger.warning(
                        f"[WAITING] Rate limit exceeded (429), waiting {wait_time:.1f}s "
                        f"before retry {attempt + 1}/{max_retries}"
                    )

                    time.sleep(wait_time)
                    continue

                else:
                    # Other API errors - log and retry with backoff
                    logger.error(f"[FAIL] Google Sheets API error {e.response.status_code}: {e}")

                    if attempt < max_retries - 1:
                        jitter = random.uniform(0, 1)
                        wait_time = min((2 ** attempt) * base_delay + jitter, 64)
                        logger.info(f"[WAITING] Retrying in {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error("[FAIL] Max retries exceeded, falling back to cache")
                        return self.load_from_cache()

            except GSpreadException as e:
                logger.error(f"[FAIL] gspread error: {e}")

                if attempt < max_retries - 1:
                    jitter = random.uniform(0, 1)
                    wait_time = min((2 ** attempt) * base_delay + jitter, 64)
                    logger.info(f"[WAITING] Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("[FAIL] Max retries exceeded, falling back to cache")
                    return self.load_from_cache()

            except Exception as e:
                logger.error(f"[FAIL] Unexpected error fetching config: {e}")

                if attempt < max_retries - 1:
                    jitter = random.uniform(0, 1)
                    wait_time = min((2 ** attempt) * base_delay + jitter, 64)
                    logger.info(f"[WAITING] Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error("[FAIL] Max retries exceeded, falling back to cache")
                    return self.load_from_cache()

        # If we get here, all retries failed
        logger.error("[FAIL] All fetch attempts failed, using cache")
        return self.load_from_cache()

    def sync_to_cache(self, config: Dict[str, Any]) -> None:
        """Save configuration to local cache with atomic write.

        Uses atomic write pattern (write to temp file, then rename) to prevent
        corruption from interrupted writes.

        Args:
            config: Configuration dictionary to cache

        Example:
            >>> sheets = GoogleSheetsSync()
            >>> config = sheets.fetch_config()
            >>> sheets.sync_to_cache(config)
        """
        try:
            # Atomic write: write to temp file, then rename
            temp_file = self.cache_file.with_suffix('.tmp')

            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)

            # Atomic rename (overwrites existing file)
            temp_file.replace(self.cache_file)

            logger.info(f"[OK] Configuration synced to cache: {self.cache_file}")

        except Exception as e:
            logger.error(f"[FAIL] Failed to sync config to cache: {e}")

    def load_from_cache(self) -> Dict[str, Any]:
        """Load configuration from local cache.

        Returns:
            Dict: Cached configuration or default config if cache missing

        Example:
            >>> sheets = GoogleSheetsSync()
            >>> config = sheets.load_from_cache()
        """
        if not self.cache_file.exists():
            logger.warning(f" Cache file not found: {self.cache_file}")
            logger.info(" Using default configuration")
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            logger.info(f"[OK] Configuration loaded from cache: {self.cache_file}")

            # Validate cached config
            if not self._validate_config(config):
                logger.warning("[WARN] Cached config invalid, using defaults")
                return DEFAULT_CONFIG.copy()

            return config

        except json.JSONDecodeError as e:
            logger.error(f"[FAIL] Failed to parse cache file: {e}")
            logger.info(" Using default configuration")
            return DEFAULT_CONFIG.copy()

        except Exception as e:
            logger.error(f"[FAIL] Failed to load cache: {e}")
            logger.info(" Using default configuration")
            return DEFAULT_CONFIG.copy()

    def get_config(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Get configuration with intelligent fallback.

        This is the main method for retrieving configuration. It implements a
        robust fallback hierarchy to ensure the system always has valid config.

        Fallback Priority:
        1. If force_refresh: Always fetch from Sheets
        2. Try fetch from Sheets (with rate limiting + retry)
        3. On fetch failure: Use local cache
        4. On cache miss: Use default configuration
        5. On success: Sync to cache for offline operation

        Args:
            force_refresh: If True, bypass cache and force fetch from Sheets

        Returns:
            Dict: Valid configuration dictionary

        Example:
            >>> sheets = GoogleSheetsSync()
            >>>
            >>> # Normal usage - tries Sheets, falls back to cache
            >>> config = sheets.get_config()
            >>>
            >>> # Force refresh from Sheets
            >>> config = sheets.get_config(force_refresh=True)
        """
        # If Google Sheets not available, use cache
        if not GSPREAD_AVAILABLE or not self.client or not self.spreadsheet:
            logger.info(" Google Sheets not available, using cache/defaults")
            cached = self.load_from_cache()
            return cached

        # If not forcing refresh, try cache first (faster)
        if not force_refresh:
            cached = self.load_from_cache()
            if cached and cached != DEFAULT_CONFIG:
                logger.debug(" Using cached configuration")
                return cached

        # Try to fetch from Google Sheets
        try:
            config = self.fetch_config()

            # Sync successful fetch to cache
            self.sync_to_cache(config)

            return config

        except Exception as e:
            logger.error(f"[FAIL] Failed to get config from Sheets: {e}")
            logger.info(" Falling back to cache")

            # Fall back to cache
            cached = self.load_from_cache()
            return cached

    def _validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration has required fields and valid values.

        Args:
            config: Configuration dictionary to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Check all required fields exist
        required_fields = [
            "dca_percentage",
            "atr_multiplier",
            "strategy_mode",
            "max_position_size",
            "global_safeguard_threshold",
        ]

        for field in required_fields:
            if field not in config:
                logger.error(f"[FAIL] Missing required field: {field}")
                return False

        # Validate types and ranges
        try:
            # dca_percentage: 0 < x < 100
            dca_pct = float(config["dca_percentage"])
            if not (0 < dca_pct < 100):
                logger.error(f"[FAIL] dca_percentage out of range: {dca_pct}")
                return False

            # atr_multiplier: 0 < x < 10
            atr_mult = float(config["atr_multiplier"])
            if not (0 < atr_mult < 10):
                logger.error(f"[FAIL] atr_multiplier out of range: {atr_mult}")
                return False

            # strategy_mode: must be valid strategy
            valid_modes = ["dca", "swing", "day", "hold"]
            if config["strategy_mode"].lower() not in valid_modes:
                logger.error(f"[FAIL] Invalid strategy_mode: {config['strategy_mode']}")
                return False

            # max_position_size: 0 < x <= 1
            max_pos = float(config["max_position_size"])
            if not (0 < max_pos <= 1):
                logger.error(f"[FAIL] max_position_size out of range: {max_pos}")
                return False

            # global_safeguard_threshold: 0 < x <= 1
            safeguard = float(config["global_safeguard_threshold"])
            if not (0 < safeguard <= 1):
                logger.error(f"[FAIL] global_safeguard_threshold out of range: {safeguard}")
                return False

            logger.debug("[OK] Configuration validation passed")
            return True

        except (ValueError, TypeError) as e:
            logger.error(f"[FAIL] Configuration validation failed: {e}")
            return False

    def _convert_types(self, raw_config: Dict[str, str]) -> Dict[str, Any]:
        """Convert string values from spreadsheet to appropriate types.

        Handles:
        - Boolean: "true"/"false" → True/False
        - Numbers: "2.5" → 2.5
        - Strings: Preserved as-is

        Args:
            raw_config: Raw configuration with string values

        Returns:
            Dict: Configuration with properly typed values
        """
        converted = {}

        for key, value in raw_config.items():
            # Normalize key (lowercase, replace spaces with underscores)
            normalized_key = key.lower().replace(" ", "_").replace("-", "_")

            # Convert value
            try:
                # Handle boolean
                if value.lower() in ["true", "yes", "1", "on"]:
                    converted[normalized_key] = True
                elif value.lower() in ["false", "no", "0", "off"]:
                    converted[normalized_key] = False
                # Handle numbers
                elif self._is_number(value):
                    # Try int first, then float
                    try:
                        converted[normalized_key] = int(value)
                    except ValueError:
                        converted[normalized_key] = float(value)
                # Handle strings
                else:
                    converted[normalized_key] = value

            except Exception as e:
                logger.warning(f"[WARN] Failed to convert {key}={value}: {e}")
                # Keep as string if conversion fails
                converted[normalized_key] = value

        logger.debug(f"[DATA] Converted {len(converted)} configuration parameters")
        return converted

    def _is_number(self, value: str) -> bool:
        """Check if string represents a number.

        Args:
            value: String to check

        Returns:
            bool: True if numeric, False otherwise
        """
        try:
            float(value)
            return True
        except ValueError:
            return False

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: Client representation
        """
        status = "connected" if self.client else "offline"
        return f"GoogleSheetsSync(status={status}, cache={self.cache_file})"


# ============================================================================
# Example Usage
# ============================================================================


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Initialize client
    sheets = GoogleSheetsSync()
    print(f"Client: {sheets}")

    # Get configuration (tries Sheets, falls back to cache)
    print("\n" + "=" * 80)
    print("Getting configuration...")
    print("=" * 80)
    config = sheets.get_config()

    print("\nConfiguration:")
    for key, value in config.items():
        print(f"  {key:30} = {value}")

    # Force refresh from Sheets
    print("\n" + "=" * 80)
    print("Force refreshing from Google Sheets...")
    print("=" * 80)
    config = sheets.get_config(force_refresh=True)

    print("\nRefreshed Configuration:")
    for key, value in config.items():
        print(f"  {key:30} = {value}")
