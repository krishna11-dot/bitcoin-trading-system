"""CSV RAG (Retrieval-Augmented Generation) for Bitcoin trading patterns.

This module implements a RAG pipeline that uses historical market data to find
similar past market conditions and predict likely outcomes. It employs FAISS
vector similarity search to match current market state with historical patterns.

The RAG system helps trading agents make informed decisions by:
1. Finding similar historical market conditions
2. Calculating success rates of those patterns
3. Providing average outcome predictions
4. Offering historical context for decision-making

Example:
    >>> from tools.csv_rag_pipeline import RAGRetriever
    >>> from data_models import MarketData, TechnicalIndicators
    >>>
    >>> rag = RAGRetriever("data/investing_btc_history.csv")
    >>> results = rag.query(market_data, indicators, k=50)
    >>> print(f"Success rate: {results['success_rate']:.1%}")
    >>> print(f"Avg outcome: {results['avg_outcome']:+.2f}%")
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from data_models import MarketData, TechnicalIndicators


# Configure logger
logger = logging.getLogger(__name__)

# Try to import FAISS (optional dependency)
try:
    import faiss

    FAISS_AVAILABLE = True
    logger.info("FAISS library available for similarity search")
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning(
        "FAISS not available. Install with: pip install faiss-cpu. "
        "RAG queries will use fallback similarity."
    )


class RAGRetriever:
    """Retrieval-Augmented Generation for Bitcoin trading patterns.

    Uses historical market data to find similar past conditions and
    predict likely outcomes. Employs FAISS vector similarity search
    to match current market state with historical patterns.

    The system creates embeddings from normalized market features:
    - Price (normalized to 0-1 range)
    - RSI (0-100, normalized to 0-1)
    - MACD (normalized based on typical range)
    - ATR (normalized based on typical range)

    Attributes:
        csv_path: Path to historical data CSV file
        df: Loaded DataFrame with historical patterns
        index: FAISS index for similarity search
        embeddings: Numpy array of all embeddings
        _loaded: Whether data has been loaded

    Example:
        >>> rag = RAGRetriever("data/investing_btc_history.csv")
        >>> results = rag.query(market_data, indicators, k=50)
        >>> if results['success_rate'] > 0.7:
        ...     print("High probability trade!")
    """

    def __init__(self, csv_path: str):
        """Initialize RAG retriever with historical data path.

        Data is loaded lazily on first query to improve initialization time.

        Args:
            csv_path: Path to CSV file with historical patterns

        Example:
            >>> rag = RAGRetriever("data/investing_btc_history.csv")
        """
        self.csv_path = Path(csv_path)
        self.df: Optional[pd.DataFrame] = None
        self.index: Optional["faiss.Index"] = None
        self.embeddings: Optional[np.ndarray] = None

        # Feature normalization parameters (calculated from data)
        self.price_min: float = 10000.0  # Will be updated from data
        self.price_max: float = 100000.0
        self.macd_min: float = -500.0
        self.macd_max: float = 500.0
        self.atr_min: float = 100.0
        self.atr_max: float = 3000.0

        # Load data lazily (on first query)
        self._loaded = False

        logger.info(f"RAGRetriever initialized with path: {csv_path}")

    def _load_data(self) -> None:
        """Load CSV data and create FAISS index.

        This method:
        1. Loads CSV file into pandas DataFrame
        2. Validates required columns exist
        3. Calculates normalization parameters from data
        4. Creates embeddings for all rows
        5. Builds FAISS index for similarity search

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If required columns are missing
        """
        if not self.csv_path.exists():
            raise FileNotFoundError(
                f"CSV file not found: {self.csv_path}. "
                f"Create historical data file with columns: "
                f"Date, Price, RSI, MACD, ATR, Volume, Action, Outcome, Success"
            )

        try:
            logger.info(f"Loading historical data from {self.csv_path}")

            # Load CSV
            self.df = pd.read_csv(self.csv_path)

            # Validate required columns
            required_cols = ["Price", "RSI", "MACD", "ATR", "Success", "Outcome"]
            missing = [col for col in required_cols if col not in self.df.columns]
            if missing:
                raise ValueError(
                    f"Missing required columns: {missing}. "
                    f"Required: {required_cols}"
                )

            logger.info(f"Loaded {len(self.df)} rows from CSV")

            # Calculate normalization parameters from data
            # This ensures embeddings are well-scaled for the actual data distribution
            self.price_min = float(self.df["Price"].min())
            self.price_max = float(self.df["Price"].max())
            self.macd_min = float(self.df["MACD"].min())
            self.macd_max = float(self.df["MACD"].max())
            self.atr_min = float(self.df["ATR"].min())
            self.atr_max = float(self.df["ATR"].max())

            logger.debug(
                f"Normalization params: "
                f"Price [{self.price_min:.0f}, {self.price_max:.0f}], "
                f"MACD [{self.macd_min:.1f}, {self.macd_max:.1f}], "
                f"ATR [{self.atr_min:.1f}, {self.atr_max:.1f}]"
            )

            # Create embeddings for all rows
            embeddings_list = []
            valid_indices = []  # Track which rows have valid embeddings

            for idx, row in self.df.iterrows():
                try:
                    emb = self._create_embeddings(row)
                    embeddings_list.append(emb)
                    valid_indices.append(idx)
                except Exception as e:
                    logger.warning(f"Skipping row {idx} due to error: {e}")
                    continue

            if not embeddings_list:
                raise ValueError("No valid embeddings could be created from data")

            # Filter DataFrame to only include rows with valid embeddings
            self.df = self.df.iloc[valid_indices].reset_index(drop=True)

            # Convert to numpy array (FAISS requires float32)
            self.embeddings = np.array(embeddings_list, dtype=np.float32)

            logger.info(f"Created {len(self.embeddings)} embeddings (dimension: {self.embeddings.shape[1]})")

            # Create FAISS index for similarity search
            if FAISS_AVAILABLE:
                self._create_faiss_index()
            else:
                logger.warning("FAISS not available. Similarity search will use fallback method.")

            self._loaded = True
            logger.info(
                f"[OK] RAG system ready: {len(self.df)} patterns loaded, "
                f"success rate: {self.df['Success'].mean():.1%}"
            )

        except Exception as e:
            logger.error(f"Failed to load RAG data: {e}", exc_info=True)
            raise

    def _create_faiss_index(self) -> None:
        """Create FAISS index for fast similarity search.

        Uses IndexFlatL2 which computes exact L2 (Euclidean) distances.
        For larger datasets, consider IndexIVFFlat for approximate search.
        """
        if not FAISS_AVAILABLE:
            return

        try:
            dimension = self.embeddings.shape[1]

            # Use exact L2 distance search (IndexFlatL2)
            # For datasets > 100k rows, consider IndexIVFFlat for speed
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(self.embeddings)

            logger.info(f"FAISS index created: {self.index.ntotal} vectors indexed")

        except Exception as e:
            logger.error(f"Failed to create FAISS index: {e}")
            self.index = None

    def _create_embeddings(self, row: pd.Series) -> np.ndarray:
        """Create embedding vector from market data row.

        Normalizes features to 0-1 range for better similarity matching.
        Features chosen represent different aspects of market state:
        - Price: Overall market level
        - RSI: Momentum (overbought/oversold)
        - MACD: Trend strength and direction
        - ATR: Volatility

        Args:
            row: DataFrame row with market data

        Returns:
            np.ndarray: Embedding vector (4 dimensions)

        Raises:
            ValueError: If row contains invalid values
        """
        # Normalize price to 0-1 range using min-max scaling
        # This makes price comparable across different market levels
        price_range = self.price_max - self.price_min
        if price_range == 0:
            price_norm = 0.5  # Avoid division by zero
        else:
            price_norm = (row["Price"] - self.price_min) / price_range

        # RSI is already 0-100, normalize to 0-1
        rsi_norm = row["RSI"] / 100.0

        # MACD normalization using min-max scaling
        # MACD can be positive or negative, so we scale the full range
        macd_range = self.macd_max - self.macd_min
        if macd_range == 0:
            macd_norm = 0.5
        else:
            macd_norm = (row["MACD"] - self.macd_min) / macd_range

        # ATR normalization (always positive, represents volatility)
        atr_range = self.atr_max - self.atr_min
        if atr_range == 0:
            atr_norm = 0.5
        else:
            atr_norm = (row["ATR"] - self.atr_min) / atr_range

        # Clip values to 0-1 range (handle outliers)
        price_norm = np.clip(price_norm, 0.0, 1.0)
        rsi_norm = np.clip(rsi_norm, 0.0, 1.0)
        macd_norm = np.clip(macd_norm, 0.0, 1.0)
        atr_norm = np.clip(atr_norm, 0.0, 1.0)

        return np.array([price_norm, rsi_norm, macd_norm, atr_norm], dtype=np.float32)

    def _fallback_similarity_search(
        self, query_embedding: np.ndarray, k: int
    ) -> tuple[np.ndarray, np.ndarray]:
        """Fallback similarity search when FAISS is not available.

        Uses simple Euclidean distance calculation with numpy.

        Args:
            query_embedding: Query vector (1, dimension)
            k: Number of nearest neighbors to find

        Returns:
            Tuple of (distances, indices) similar to FAISS output
        """
        # Calculate Euclidean distances to all embeddings
        distances = np.linalg.norm(self.embeddings - query_embedding, axis=1)

        # Get indices of k smallest distances
        k = min(k, len(distances))  # Don't exceed available data
        indices = np.argpartition(distances, k - 1)[:k]

        # Sort by distance
        sorted_idx = np.argsort(distances[indices])
        indices = indices[sorted_idx]
        distances = distances[indices]

        return distances, indices

    def query(
        self, market_data: MarketData, indicators: TechnicalIndicators, k: int = 50
    ) -> Dict:
        """Query similar historical patterns.

        Finds k most similar historical market conditions and calculates
        the success rate and average outcome of those patterns. This provides
        context for trading decisions by showing what happened in similar
        situations in the past.

        Args:
            market_data: Current market data (price, volume, etc.)
            indicators: Current technical indicators (RSI, MACD, ATR, etc.)
            k: Number of similar patterns to retrieve (default: 50)

        Returns:
            dict: {
                "similar_patterns": int - Number of patterns found,
                "success_rate": float - Success rate (0-1) of similar patterns,
                "avg_outcome": float - Average profit/loss % of similar patterns,
                "historical_context": str - Human-readable summary
            }

        Example:
            >>> results = rag.query(market_data, indicators, k=50)
            >>> if results["success_rate"] > 0.7:
            ...     print(f"High confidence: {results['historical_context']}")
            >>> else:
            ...     print("Cautious approach recommended")
        """
        # Load data if not already loaded (lazy loading)
        if not self._loaded:
            try:
                self._load_data()
            except Exception as e:
                logger.error(f"RAG query failed - could not load data: {e}")
                return self._get_default_response(
                    "No historical data available - file missing or invalid"
                )

        try:
            # Create query embedding from current market state
            query_row = pd.Series(
                {
                    "Price": market_data.price,
                    "RSI": indicators.rsi_14,
                    "MACD": indicators.macd,
                    "ATR": indicators.atr_14,
                }
            )

            query_embedding = self._create_embeddings(query_row)
            query_embedding = query_embedding.reshape(1, -1)

            # Ensure k doesn't exceed available data
            k = min(k, len(self.df))

            logger.debug(f"Querying RAG for {k} similar patterns")

            # Search for similar patterns
            if FAISS_AVAILABLE and self.index is not None:
                # Use FAISS for fast similarity search
                distances, indices = self.index.search(query_embedding, k)
                distances = distances[0]  # Extract from batch dimension
                indices = indices[0]
            else:
                # Fallback to numpy-based search
                distances, indices = self._fallback_similarity_search(query_embedding, k)

            # Get similar rows from DataFrame
            similar_rows = self.df.iloc[indices]

            # Calculate statistics from similar patterns
            success_rate = similar_rows["Success"].mean()
            avg_outcome = similar_rows["Outcome"].mean()
            median_outcome = similar_rows["Outcome"].median()

            # Calculate additional statistics
            num_wins = int(similar_rows["Success"].sum())
            num_losses = len(similar_rows) - num_wins
            best_outcome = similar_rows["Outcome"].max()
            worst_outcome = similar_rows["Outcome"].min()

            # Calculate average distance (similarity measure)
            avg_distance = float(distances.mean())

            # Create context description
            context = (
                f"Found {k} similar patterns: "
                f"{num_wins} wins ({success_rate:.1%}), {num_losses} losses. "
                f"Avg outcome: {avg_outcome:+.2f}% (median: {median_outcome:+.2f}%). "
                f"Range: [{worst_outcome:+.2f}%, {best_outcome:+.2f}%]. "
                f"Avg similarity: {1.0 / (1.0 + avg_distance):.2%}"
            )

            logger.info(f"RAG query result: {success_rate:.1%} success rate from {k} patterns")

            return {
                "similar_patterns": k,
                "success_rate": float(success_rate),
                "avg_outcome": float(avg_outcome),
                "median_outcome": float(median_outcome),
                "best_outcome": float(best_outcome),
                "worst_outcome": float(worst_outcome),
                "num_wins": num_wins,
                "num_losses": num_losses,
                "avg_distance": avg_distance,
                "historical_context": context,
            }

        except Exception as e:
            logger.error(f"RAG query error: {e}", exc_info=True)
            return self._get_default_response(f"Query failed: {str(e)}")

    def _get_default_response(self, message: str) -> Dict:
        """Get default response when query fails.

        Args:
            message: Error message to include

        Returns:
            dict: Default response with neutral values
        """
        return {
            "similar_patterns": 0,
            "success_rate": 0.5,  # Neutral (50/50)
            "avg_outcome": 0.0,  # No bias
            "median_outcome": 0.0,
            "best_outcome": 0.0,
            "worst_outcome": 0.0,
            "num_wins": 0,
            "num_losses": 0,
            "avg_distance": float("inf"),
            "historical_context": message,
        }

    def get_stats(self) -> Dict:
        """Get statistics about loaded historical data.

        Returns:
            dict: Statistics including total patterns, success rate, etc.

        Example:
            >>> rag = RAGRetriever("data/investing_btc_history.csv")
            >>> stats = rag.get_stats()
            >>> print(f"Total patterns: {stats['total_patterns']}")
        """
        if not self._loaded:
            try:
                self._load_data()
            except Exception as e:
                logger.error(f"Could not load stats: {e}")
                return {"error": str(e)}

        return {
            "total_patterns": len(self.df),
            "overall_success_rate": float(self.df["Success"].mean()),
            "avg_outcome": float(self.df["Outcome"].mean()),
            "median_outcome": float(self.df["Outcome"].median()),
            "best_outcome": float(self.df["Outcome"].max()),
            "worst_outcome": float(self.df["Outcome"].min()),
            "price_range": [float(self.price_min), float(self.price_max)],
            "data_loaded": self._loaded,
            "faiss_available": FAISS_AVAILABLE,
        }

    def __repr__(self) -> str:
        """Return string representation.

        Returns:
            str: RAGRetriever representation
        """
        status = "loaded" if self._loaded else "not loaded"
        return f"RAGRetriever(csv_path={self.csv_path}, status={status})"


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    # Example usage and testing
    logging.basicConfig(level=logging.INFO)

    # Test with sample data
    csv_path = "data/investing_btc_history.csv"

    try:
        rag = RAGRetriever(csv_path)
        print(f"RAG Retriever: {rag}")

        # Get stats
        stats = rag.get_stats()
        print(f"\nHistorical Data Stats:")
        print(f"  Total patterns: {stats.get('total_patterns', 'N/A')}")
        print(f"  Success rate: {stats.get('overall_success_rate', 0):.1%}")
        print(f"  Avg outcome: {stats.get('avg_outcome', 0):+.2f}%")

        # Test query with sample data
        print("\nTesting query with sample market data...")

        # Create sample MarketData
        from data_models import MarketData, TechnicalIndicators

        sample_market = MarketData(
            price=45000.0,
            volume=1000000.0,
            timestamp="2025-01-01T00:00:00Z",
            change_24h=2.5,
            high_24h=46000.0,
            low_24h=44000.0,
        )

        sample_indicators = TechnicalIndicators(
            rsi_14=65.0,
            macd=120.0,
            macd_signal=115.0,
            macd_histogram=5.0,
            atr_14=850.0,
            sma_50=44500.0,
            ema_12=45200.0,
            ema_26=44800.0,
        )

        results = rag.query(sample_market, sample_indicators, k=50)
        print(f"\nQuery Results:")
        print(f"  Similar patterns: {results['similar_patterns']}")
        print(f"  Success rate: {results['success_rate']:.1%}")
        print(f"  Avg outcome: {results['avg_outcome']:+.2f}%")
        print(f"  Context: {results['historical_context']}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nCreate sample CSV file first:")
        print("  python -c 'from tools.csv_rag_pipeline import create_sample_csv; create_sample_csv()'")
    except Exception as e:
        print(f"Error: {e}")
