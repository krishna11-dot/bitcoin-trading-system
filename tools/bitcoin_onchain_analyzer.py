"""
Bitcoin On-Chain Analyzer - Blockchain.com API Integration

Uses Blockchain.com Data API as a free alternative to CryptoQuant for on-chain metrics.
Provides block size metrics, hash rate estimation, and mempool analysis.

API Documentation: https://www.blockchain.com/api/blockchain_api
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
import requests
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class BitcoinOnChainAnalyzer:
    """
    Analyzes Bitcoin on-chain metrics using Blockchain.com API.

    Features:
    - Block size metrics (current, average, trends)
    - Hash rate estimation from block data
    - Mempool analysis (transaction backlog, fees, congestion)
    - Automatic caching to respect rate limits
    - Error handling with exponential backoff
    """

    def __init__(self, cache_duration: int = 120):
        """
        Initialize the on-chain analyzer.

        Args:
            cache_duration: Cache lifetime in seconds (default: 120 = 2 minutes)
        """
        self.base_url = "https://blockchain.info"
        self.cache_duration = cache_duration
        self._cache: Dict[str, Dict[str, Any]] = {}

        # API configuration
        self.timeout = 30  # seconds
        self.max_retries = 3
        self.retry_delay = 1  # seconds
        self.user_agent = "BitcoinTradingAgent/1.0"

        logger.info(f"BitcoinOnChainAnalyzer initialized (cache: {cache_duration}s)")


    def get_block_size_metrics(self) -> Dict[str, Any]:
        """
        Get current block size metrics.

        Returns:
            dict: {
                'current_size_mb': float,
                'current_size_bytes': int,
                'avg_size_mb': float,
                'avg_size_bytes': float,
                'trend': str,  # 'increasing', 'decreasing', 'stable'
                'block_height': int,
                'last_10_blocks': list,
                'timestamp': str
            }
        """
        try:
            logger.info("Fetching block size metrics...")

            # Get latest block
            latest_block = self._api_request("/latestblock")
            if not latest_block or 'error' in latest_block:
                return self._get_default_block_metrics()

            block_height = latest_block.get('height', 0)
            latest_block_hash = latest_block.get('hash', '')

            # Get detailed data for last 10 blocks
            block_sizes = []

            # Get the latest block details first
            latest_block_data = self._api_request(f"/rawblock/{latest_block_hash}")
            if latest_block_data and 'error' not in latest_block_data:
                current_size = latest_block_data.get('size', 0)
                block_sizes.append(current_size)

                # Get previous block hash to traverse backwards
                prev_hash = latest_block_data.get('prev_block', '')

                # Fetch 9 more blocks
                for i in range(9):
                    if not prev_hash:
                        break

                    block_data = self._api_request(f"/rawblock/{prev_hash}")
                    if block_data and 'error' not in block_data:
                        block_sizes.append(block_data.get('size', 0))
                        prev_hash = block_data.get('prev_block', '')
                    else:
                        break
            else:
                current_size = 1_500_000  # Default ~1.5 MB
                block_sizes = [current_size]

            # Calculate metrics
            current_size_mb = current_size / (1024 * 1024)
            avg_size_bytes = mean(block_sizes) if block_sizes else current_size
            avg_size_mb = avg_size_bytes / (1024 * 1024)

            # Determine trend
            trend = self._calculate_trend(block_sizes)

            result = {
                'current_size_mb': round(current_size_mb, 2),
                'current_size_bytes': current_size,
                'avg_size_mb': round(avg_size_mb, 2),
                'avg_size_bytes': round(avg_size_bytes, 0),
                'trend': trend,
                'block_height': block_height,
                'last_10_blocks': block_sizes[:10],
                'blocks_analyzed': len(block_sizes),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"[OK] Block metrics: {current_size_mb:.2f} MB, Trend: {trend}")
            return result

        except Exception as e:
            logger.error(f"Error fetching block size metrics: {e}")
            return self._get_default_block_metrics()


    def get_hash_rate_estimation(self, blocks_back: int = 100) -> Dict[str, Any]:
        """
        Estimate current network hash rate from recent block data.

        Formula: Hash Rate ≈ (Current Difficulty × 2³²) / Average Block Time

        Args:
            blocks_back: Number of blocks to analyze (default: 100)

        Returns:
            dict: {
                'hash_rate_ths': float,  # Tera Hashes per second
                'hash_rate_ehs': float,  # Exa Hashes per second
                'avg_block_time': float,  # seconds
                'difficulty': float,
                'confidence': str,  # 'high', 'medium', 'low'
                'blocks_analyzed': int,
                'timestamp': str
            }
        """
        try:
            logger.info(f"Estimating hash rate from last {blocks_back} blocks...")

            # Get latest block
            latest_block = self._api_request("/latestblock")
            if not latest_block or 'error' in latest_block:
                return self._get_default_hashrate()

            latest_hash = latest_block.get('hash', '')

            # Collect block timestamps
            block_times = []
            prev_hash = latest_hash

            # Sample every 10 blocks to reduce API calls (analyze ~10 blocks out of 100)
            sample_interval = max(1, blocks_back // 10)
            blocks_sampled = 0

            for i in range(min(blocks_back, 20)):  # Max 20 API calls
                if not prev_hash:
                    break

                block_data = self._api_request(f"/rawblock/{prev_hash}")
                if block_data and 'error' not in block_data:
                    timestamp = block_data.get('time', 0)
                    if timestamp:
                        block_times.append(timestamp)
                    prev_hash = block_data.get('prev_block', '')
                    blocks_sampled += 1

                    # Skip intermediate blocks
                    if i % sample_interval != 0 and i < blocks_back - 1:
                        continue
                else:
                    break

            # Calculate average block time
            if len(block_times) >= 2:
                time_diffs = []
                for i in range(len(block_times) - 1):
                    diff = abs(block_times[i] - block_times[i + 1])
                    if diff > 0:
                        time_diffs.append(diff)

                avg_block_time = mean(time_diffs) if time_diffs else 600  # Default 10 minutes
            else:
                avg_block_time = 600  # Default 10 minutes

            # Use the simple hash rate API (returns plain number in TH/s)
            difficulty = None  # Will be set if we calculate it
            try:
                hash_rate_ths = self._api_request("/q/hashrate", is_json=False)
                if hash_rate_ths and isinstance(hash_rate_ths, (int, float)):
                    hash_rate_ehs = hash_rate_ths / (10 ** 6)  # TH/s to EH/s
                    difficulty = None  # Not calculated, hash rate from API
                else:
                    # Fallback: calculate from block time
                    difficulty = 70_000_000_000_000  # Approximate
                    hash_rate = (difficulty * (2 ** 32)) / avg_block_time
                    hash_rate_ths = hash_rate / (10 ** 12)
                    hash_rate_ehs = hash_rate / (10 ** 18)
            except Exception as e:
                logger.warning(f"Failed to fetch hash rate from API: {e}")
                # Fallback: calculate from block time
                difficulty = 70_000_000_000_000  # Approximate
                hash_rate = (difficulty * (2 ** 32)) / avg_block_time
                hash_rate_ths = hash_rate / (10 ** 12)
                hash_rate_ehs = hash_rate / (10 ** 18)

            # Determine confidence based on sample size
            if blocks_sampled >= 15:
                confidence = 'high'
            elif blocks_sampled >= 8:
                confidence = 'medium'
            else:
                confidence = 'low'

            result = {
                'hash_rate_ths': round(hash_rate_ths, 2),
                'hash_rate_ehs': round(hash_rate_ehs, 2),
                'avg_block_time': round(avg_block_time, 2),
                'difficulty': difficulty,
                'confidence': confidence,
                'blocks_analyzed': blocks_sampled,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"[OK] Hash rate: {hash_rate_ehs:.2f} EH/s (confidence: {confidence})")
            return result

        except Exception as e:
            logger.error(f"Error estimating hash rate: {e}")
            return self._get_default_hashrate()


    def get_mempool_metrics(self) -> Dict[str, Any]:
        """
        Analyze current mempool status.

        Returns:
            dict: {
                'tx_count': int,
                'total_size_mb': float,
                'total_size_bytes': int,
                'avg_fee_satoshis': float,
                'avg_fee_btc': float,
                'congestion_level': str,  # 'Low', 'Medium', 'High', 'Critical'
                'backlog_severity': float,  # 0-1 scale
                'timestamp': str
            }
        """
        try:
            logger.info("Fetching mempool metrics...")

            # Get unconfirmed transactions
            mempool_data = self._api_request("/unconfirmed-transactions?format=json")
            if not mempool_data or 'error' in mempool_data:
                return self._get_default_mempool()

            transactions = mempool_data.get('txs', [])
            tx_count = len(transactions)

            # Calculate total size and fees
            total_size_bytes = 0
            total_fees = 0
            fee_samples = []

            for tx in transactions[:100]:  # Analyze first 100 transactions
                tx_size = tx.get('size', 0)
                tx_fee = tx.get('fee', 0)

                total_size_bytes += tx_size
                total_fees += tx_fee

                if tx_size > 0:
                    fee_per_byte = tx_fee / tx_size
                    fee_samples.append(fee_per_byte)

            # Extrapolate total size if we have more transactions
            if tx_count > 100:
                avg_tx_size = total_size_bytes / min(100, len(transactions))
                total_size_bytes = int(avg_tx_size * tx_count)

            total_size_mb = total_size_bytes / (1024 * 1024)

            # Calculate average fee
            avg_fee_satoshis = mean(fee_samples) if fee_samples else 0
            avg_fee_btc = avg_fee_satoshis / 100_000_000

            # Determine congestion level
            congestion_level, backlog_severity = self._calculate_congestion(
                tx_count, total_size_mb, avg_fee_satoshis
            )

            result = {
                'tx_count': tx_count,
                'total_size_mb': round(total_size_mb, 2),
                'total_size_bytes': total_size_bytes,
                'avg_fee_satoshis': round(avg_fee_satoshis, 2),
                'avg_fee_btc': round(avg_fee_btc, 8),
                'congestion_level': congestion_level,
                'backlog_severity': round(backlog_severity, 2),
                'fee_samples_analyzed': len(fee_samples),
                'timestamp': datetime.now().isoformat()
            }

            logger.info(
                f"[OK] Mempool: {tx_count} txs, {total_size_mb:.2f} MB, "
                f"Congestion: {congestion_level}"
            )
            return result

        except Exception as e:
            logger.error(f"Error fetching mempool metrics: {e}")
            return self._get_default_mempool()


    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """
        Get all on-chain metrics combined for ML feature extraction.

        Returns:
            dict: Combined metrics from all analysis methods plus metadata
        """
        logger.info("Fetching comprehensive on-chain metrics...")

        try:
            # Get all metrics
            block_metrics = self.get_block_size_metrics()
            hash_metrics = self.get_hash_rate_estimation(blocks_back=100)
            mempool_metrics = self.get_mempool_metrics()

            # Combine into comprehensive report
            comprehensive = {
                'block_metrics': block_metrics,
                'hash_rate_metrics': hash_metrics,
                'mempool_metrics': mempool_metrics,
                'summary': {
                    'block_size_mb': block_metrics.get('current_size_mb', 0),
                    'block_size_trend': block_metrics.get('trend', 'unknown'),
                    'hash_rate_ehs': hash_metrics.get('hash_rate_ehs', 0),
                    'mempool_tx_count': mempool_metrics.get('tx_count', 0),
                    'mempool_congestion': mempool_metrics.get('congestion_level', 'Unknown'),
                    'network_health': self._assess_network_health(
                        block_metrics, hash_metrics, mempool_metrics
                    )
                },
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'data_source': 'Blockchain.com API',
                    'analyzer_version': '1.0'
                }
            }

            logger.info("[OK] Comprehensive metrics retrieved successfully")
            return comprehensive

        except Exception as e:
            logger.error(f"Error fetching comprehensive metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }


    # =========================================================================
    # PRIVATE HELPER METHODS
    # =========================================================================

    def _api_request(self, endpoint: str, params: Optional[Dict] = None, is_json: bool = True):
        """
        Make API request with caching, retries, and error handling.

        Args:
            endpoint: API endpoint (e.g., '/latestblock')
            params: Optional query parameters
            is_json: If True, parse response as JSON. If False, return plain text/number

        Returns:
            dict/float/int: API response data or None on failure
        """
        # Check cache first
        cache_key = f"{endpoint}:{str(params)}"
        if cache_key in self._cache:
            cached_data = self._cache[cache_key]
            cache_age = time.time() - cached_data['timestamp']

            if cache_age < self.cache_duration:
                logger.debug(f"Using cached data for {endpoint} (age: {cache_age:.0f}s)")
                return cached_data['data']

        # Prepare request
        url = f"{self.base_url}{endpoint}"
        if params is None:
            params = {}

        # Add CORS support
        params['cors'] = 'true'

        headers = {
            'User-Agent': self.user_agent
        }

        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"API request: {url} (attempt {attempt + 1}/{self.max_retries})")

                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    if is_json:
                        data = response.json()
                    else:
                        # Parse plain text/number response
                        text = response.text.strip()
                        try:
                            # Try to convert to float/int
                            if '.' in text:
                                data = float(text)
                            else:
                                data = int(text)
                        except ValueError:
                            data = text

                    # Cache successful response
                    self._cache[cache_key] = {
                        'data': data,
                        'timestamp': time.time()
                    }

                    return data

                elif response.status_code == 429:
                    # Rate limited - wait longer
                    wait_time = self.retry_delay * (2 ** attempt) * 2
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    continue

                else:
                    logger.warning(f"API returned status {response.status_code}")

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout on attempt {attempt + 1}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error on attempt {attempt + 1}: {e}")

            # Exponential backoff
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)
                logger.debug(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)

        # All retries failed - check cache for stale data
        if cache_key in self._cache:
            logger.warning(f"Using stale cached data for {endpoint}")
            return self._cache[cache_key]['data']

        logger.error(f"API request failed after {self.max_retries} retries: {endpoint}")
        return {'error': f'Failed to fetch {endpoint}'}


    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate trend from a series of values.

        Args:
            values: List of numeric values (most recent first)

        Returns:
            str: 'increasing', 'decreasing', or 'stable'
        """
        if len(values) < 3:
            return 'unknown'

        # Compare first half vs second half
        mid = len(values) // 2
        first_half_avg = mean(values[:mid])
        second_half_avg = mean(values[mid:])

        # Calculate percentage change
        if second_half_avg == 0:
            return 'stable'

        pct_change = ((first_half_avg - second_half_avg) / second_half_avg) * 100

        if pct_change > 5:
            return 'increasing'
        elif pct_change < -5:
            return 'decreasing'
        else:
            return 'stable'


    def _calculate_congestion(
        self,
        tx_count: int,
        total_size_mb: float,
        avg_fee: float
    ) -> tuple:
        """
        Calculate mempool congestion level.

        Args:
            tx_count: Number of unconfirmed transactions
            total_size_mb: Total mempool size in MB
            avg_fee: Average fee in satoshis per byte

        Returns:
            tuple: (congestion_level: str, severity: float 0-1)
        """
        # Define thresholds
        severity = 0.0

        # Transaction count contribution (0-0.4)
        if tx_count < 5000:
            tx_severity = 0.0
        elif tx_count < 20000:
            tx_severity = 0.2
        elif tx_count < 50000:
            tx_severity = 0.3
        else:
            tx_severity = 0.4

        # Size contribution (0-0.3)
        if total_size_mb < 50:
            size_severity = 0.0
        elif total_size_mb < 150:
            size_severity = 0.15
        elif total_size_mb < 300:
            size_severity = 0.25
        else:
            size_severity = 0.3

        # Fee contribution (0-0.3)
        if avg_fee < 10:
            fee_severity = 0.0
        elif avg_fee < 50:
            fee_severity = 0.15
        elif avg_fee < 100:
            fee_severity = 0.25
        else:
            fee_severity = 0.3

        severity = tx_severity + size_severity + fee_severity

        # Determine level
        if severity < 0.2:
            level = 'Low'
        elif severity < 0.5:
            level = 'Medium'
        elif severity < 0.8:
            level = 'High'
        else:
            level = 'Critical'

        return level, severity


    def _assess_network_health(
        self,
        block_metrics: Dict,
        hash_metrics: Dict,
        mempool_metrics: Dict
    ) -> str:
        """
        Assess overall network health.

        Args:
            block_metrics: Block size metrics
            hash_metrics: Hash rate metrics
            mempool_metrics: Mempool metrics

        Returns:
            str: 'Excellent', 'Good', 'Fair', or 'Poor'
        """
        score = 0
        max_score = 10

        # Hash rate confidence (0-3 points)
        confidence = hash_metrics.get('confidence', 'low')
        if confidence == 'high':
            score += 3
        elif confidence == 'medium':
            score += 2
        else:
            score += 1

        # Block size trend (0-2 points)
        trend = block_metrics.get('trend', 'unknown')
        if trend == 'stable':
            score += 2
        elif trend in ['increasing', 'decreasing']:
            score += 1

        # Mempool congestion (0-5 points)
        congestion = mempool_metrics.get('congestion_level', 'Unknown')
        if congestion == 'Low':
            score += 5
        elif congestion == 'Medium':
            score += 3
        elif congestion == 'High':
            score += 1
        # Critical = 0 points

        # Determine health level
        health_pct = (score / max_score) * 100

        if health_pct >= 80:
            return 'Excellent'
        elif health_pct >= 60:
            return 'Good'
        elif health_pct >= 40:
            return 'Fair'
        else:
            return 'Poor'


    # =========================================================================
    # DEFAULT FALLBACK VALUES
    # =========================================================================

    def _get_default_block_metrics(self) -> Dict:
        """Return default block metrics during API failure."""
        return {
            'current_size_mb': 1.5,
            'current_size_bytes': 1_500_000,
            'avg_size_mb': 1.5,
            'avg_size_bytes': 1_500_000,
            'trend': 'unknown',
            'block_height': 0,
            'last_10_blocks': [],
            'blocks_analyzed': 0,
            'timestamp': datetime.now().isoformat(),
            'error': 'Using default values due to API failure'
        }


    def _get_default_hashrate(self) -> Dict:
        """Return default hash rate during API failure."""
        return {
            'hash_rate_ths': 400_000_000,  # ~400 EH/s in TH/s
            'hash_rate_ehs': 400,
            'avg_block_time': 600,
            'difficulty': 70_000_000_000_000,
            'confidence': 'low',
            'blocks_analyzed': 0,
            'timestamp': datetime.now().isoformat(),
            'error': 'Using default values due to API failure'
        }


    def _get_default_mempool(self) -> Dict:
        """Return default mempool metrics during API failure."""
        return {
            'tx_count': 10000,
            'total_size_mb': 50.0,
            'total_size_bytes': 52_428_800,
            'avg_fee_satoshis': 25.0,
            'avg_fee_btc': 0.00000025,
            'congestion_level': 'Unknown',
            'backlog_severity': 0.5,
            'fee_samples_analyzed': 0,
            'timestamp': datetime.now().isoformat(),
            'error': 'Using default values due to API failure'
        }


    def clear_cache(self):
        """Clear all cached data."""
        self._cache.clear()
        logger.info("Cache cleared")


    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        now = time.time()
        valid_entries = sum(
            1 for data in self._cache.values()
            if now - data['timestamp'] < self.cache_duration
        )

        return {
            'total_entries': len(self._cache),
            'valid_entries': valid_entries,
            'stale_entries': len(self._cache) - valid_entries,
            'cache_duration': self.cache_duration
        }
