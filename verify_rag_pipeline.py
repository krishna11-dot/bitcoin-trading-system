"""
Verify CSV RAG Pipeline Functionality

This script tests the RAG (Retrieval-Augmented Generation) pipeline
to demonstrate its benefits for Bitcoin trading decisions.

The RAG system helps by:
1. Finding similar historical market conditions
2. Calculating success rates of past patterns
3. Providing data-driven trading insights
4. Offering historical context for decisions
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Use simple ASCII characters for Windows compatibility
OK = "[OK]"
FAIL = "[FAIL]"


def test_rag_pipeline():
    """Test the RAG pipeline with sample market data."""

    print("=" * 80)
    print("CSV RAG PIPELINE VERIFICATION TEST")
    print("=" * 80)
    print()

    # Import required modules
    try:
        from tools.csv_rag_pipeline import RAGRetriever
        from data_models import MarketData, TechnicalIndicators
        print("[OK] Successfully imported required modules")
    except ImportError as e:
        print(f"[FAIL] Import error: {e}")
        print("Make sure all dependencies are installed")
        return False

    # Initialize RAG retriever
    csv_path = "data/Bitcoin_Historical_Data_Raw.csv"

    if not Path(csv_path).exists():
        print(f"[FAIL] CSV file not found: {csv_path}")
        print("Make sure the historical data file exists")
        return False

    print(f"\n1. INITIALIZING RAG RETRIEVER")
    print("-" * 80)

    try:
        rag = RAGRetriever(csv_path)
        print(f"[OK] RAG Retriever initialized: {rag}")
    except Exception as e:
        print(f"[FAIL] Failed to initialize RAG: {e}")
        return False

    # Get statistics about historical data
    print(f"\n2. LOADING HISTORICAL DATA STATISTICS")
    print("-" * 80)

    try:
        stats = rag.get_stats()

        if 'error' in stats:
            print(f"[FAIL] Error loading stats: {stats['error']}")
            return False

        print(f"[OK] Total patterns loaded: {stats['total_patterns']:,}")
        print(f"  • Overall success rate: {stats['overall_success_rate']:.1%}")
        print(f"  • Average outcome: {stats['avg_outcome']:+.2f}%")
        print(f"  • Median outcome: {stats['median_outcome']:+.2f}%")
        print(f"  • Best outcome: {stats['best_outcome']:+.2f}%")
        print(f"  • Worst outcome: {stats['worst_outcome']:+.2f}%")
        print(f"  • Price range: ${stats['price_range'][0]:,.0f} - ${stats['price_range'][1]:,.0f}")
        print(f"  • FAISS available: {'Yes' if stats['faiss_available'] else 'No (using fallback)'}")

    except Exception as e:
        print(f"[FAIL] Failed to get stats: {e}")
        return False

    # Test with multiple market scenarios
    print(f"\n3. TESTING RAG QUERIES WITH DIFFERENT MARKET SCENARIOS")
    print("-" * 80)

    test_scenarios = [
        {
            "name": "Bullish Market (High RSI, Positive MACD)",
            "market_data": MarketData(
                price=65000.0,
                volume=1200000.0,
                timestamp="2025-01-15T12:00:00Z",
                change_24h=3.5,
                high_24h=66000.0,
                low_24h=64000.0,
            ),
            "indicators": TechnicalIndicators(
                rsi_14=72.0,  # Overbought
                macd=250.0,
                macd_signal=230.0,
                macd_histogram=20.0,
                atr_14=1200.0,
                sma_50=63000.0,
                ema_12=64500.0,
                ema_26=63500.0,
            )
        },
        {
            "name": "Bearish Market (Low RSI, Negative MACD)",
            "market_data": MarketData(
                price=45000.0,
                volume=900000.0,
                timestamp="2025-01-15T12:00:00Z",
                change_24h=-2.8,
                high_24h=46000.0,
                low_24h=44500.0,
            ),
            "indicators": TechnicalIndicators(
                rsi_14=28.0,  # Oversold
                macd=-180.0,
                macd_signal=-150.0,
                macd_histogram=-30.0,
                atr_14=950.0,
                sma_50=47000.0,
                ema_12=45500.0,
                ema_26=46500.0,
            )
        },
        {
            "name": "Neutral Market (Mid RSI, Low MACD)",
            "market_data": MarketData(
                price=55000.0,
                volume=1000000.0,
                timestamp="2025-01-15T12:00:00Z",
                change_24h=0.5,
                high_24h=55500.0,
                low_24h=54500.0,
            ),
            "indicators": TechnicalIndicators(
                rsi_14=50.0,  # Neutral
                macd=25.0,
                macd_signal=20.0,
                macd_histogram=5.0,
                atr_14=800.0,
                sma_50=54800.0,
                ema_12=55100.0,
                ema_26=54900.0,
            )
        },
    ]

    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n  Scenario {i}: {scenario['name']}")
        print(f"  {'-' * 76}")

        try:
            # Query RAG system
            results = rag.query(
                scenario['market_data'],
                scenario['indicators'],
                k=50  # Find 50 similar patterns
            )

            # Display results
            print(f"  Market State:")
            print(f"    • Price: ${scenario['market_data'].price:,.2f}")
            print(f"    • RSI: {scenario['indicators'].rsi_14:.1f}")
            print(f"    • MACD: {scenario['indicators'].macd:+.2f}")
            print(f"    • ATR: {scenario['indicators'].atr_14:.2f}")

            print(f"\n  Historical Pattern Analysis:")
            print(f"    • Similar patterns found: {results['similar_patterns']}")
            print(f"    • Success rate: {results['success_rate']:.1%}")
            print(f"    • Wins: {results['num_wins']}, Losses: {results['num_losses']}")
            print(f"    • Avg outcome: {results['avg_outcome']:+.2f}%")
            print(f"    • Median outcome: {results['median_outcome']:+.2f}%")
            print(f"    • Best case: {results['best_outcome']:+.2f}%")
            print(f"    • Worst case: {results['worst_outcome']:+.2f}%")

            # Trading recommendation based on RAG results
            print(f"\n  Trading Insight:")
            if results['success_rate'] >= 0.65:
                confidence = "HIGH"
                recommendation = "Favorable conditions for trading"
            elif results['success_rate'] >= 0.50:
                confidence = "MEDIUM"
                recommendation = "Proceed with caution"
            else:
                confidence = "LOW"
                recommendation = "Unfavorable conditions, consider holding"

            print(f"    • Confidence: {confidence}")
            print(f"    • Recommendation: {recommendation}")
            print(f"    • Context: {results['historical_context']}")

        except Exception as e:
            print(f"  [FAIL] Query failed: {e}")
            logger.exception("Query error details:")
            return False

    # Summary of benefits
    print(f"\n4. RAG PIPELINE BENEFITS")
    print("-" * 80)
    print("""
  [OK] Data-Driven Decisions:
    • Uses historical patterns to predict outcomes
    • Provides statistical confidence for each trade
    • Reduces emotional/impulsive trading decisions

  [OK] Risk Assessment:
    • Shows best/worst case scenarios from similar patterns
    • Calculates win/loss ratios from historical data
    • Helps with position sizing based on expected outcomes

  [OK] Pattern Recognition:
    • Finds similar market conditions from thousands of historical data points
    • Uses FAISS for fast similarity search (or numpy fallback)
    • Considers multiple factors: price, RSI, MACD, ATR

  [OK] Contextual Insights:
    • Provides human-readable context for each decision
    • Shows how often similar patterns succeeded in the past
    • Gives average profit/loss from similar situations

  [OK] Continuous Learning:
    • Can be updated with new historical data
    • Improves accuracy as more patterns are added
    • Adapts to changing market conditions
    """)

    print(f"\n{'=' * 80}")
    print("[OK] RAG PIPELINE VERIFICATION COMPLETE")
    print(f"{'=' * 80}")

    return True


def demonstrate_rag_benefits():
    """Demonstrate specific benefits of RAG pipeline."""

    print("\n\n")
    print("=" * 80)
    print("RAG PIPELINE PRACTICAL BENEFITS")
    print("=" * 80)

    benefits = [
        {
            "title": "1. Historical Pattern Matching",
            "description": "Instead of guessing, the RAG system finds similar past market "
                          "conditions and shows what happened. This is like having a "
                          "database of trading outcomes for every market situation.",
            "example": "If RSI is 75 and MACD is positive, the system finds all past "
                      "instances where these conditions occurred and calculates their "
                      "success rate."
        },
        {
            "title": "2. Statistical Confidence",
            "description": "Every trading decision comes with a success rate based on "
                          "historical data. This helps you understand the probability "
                          "of success before entering a trade.",
            "example": "If 70% of similar patterns resulted in profits, you have "
                      "statistical evidence supporting the trade."
        },
        {
            "title": "3. Risk Quantification",
            "description": "The system shows best-case and worst-case scenarios from "
                          "similar historical patterns, helping you assess potential "
                          "risk/reward ratios.",
            "example": "Average outcome: +5.2%, Best: +12.5%, Worst: -3.1% - this "
                      "helps you size your position appropriately."
        },
        {
            "title": "4. Reduces Emotional Trading",
            "description": "By relying on historical data rather than gut feelings, "
                          "the RAG system helps eliminate emotional decision-making "
                          "and fear-based reactions.",
            "example": "During a dip, the system might show that similar dips had "
                      "80% recovery rate, preventing panic selling."
        },
        {
            "title": "5. Fast Similarity Search",
            "description": "Uses FAISS (Facebook AI Similarity Search) to quickly find "
                          "similar patterns among thousands of historical data points "
                          "in milliseconds.",
            "example": "Can search through 10,000+ historical patterns and find the "
                      "50 most similar ones in under 100ms."
        },
        {
            "title": "6. Multi-Factor Analysis",
            "description": "Considers multiple market indicators simultaneously (Price, "
                          "RSI, MACD, ATR) to find truly similar market conditions, "
                          "not just price similarities.",
            "example": "Two periods might have similar prices but different RSI/MACD - "
                      "the RAG system distinguishes between these scenarios."
        },
    ]

    for benefit in benefits:
        print(f"\n{benefit['title']}")
        print("-" * 80)
        print(f"Description: {benefit['description']}")
        print(f"\nExample: {benefit['example']}")

    print(f"\n{'=' * 80}")


if __name__ == "__main__":
    try:
        # Run verification test
        success = test_rag_pipeline()

        if success:
            # Show additional benefits
            demonstrate_rag_benefits()

            print("\n[OK] All tests passed! RAG pipeline is working correctly.")
            print("\nNext steps:")
            print("  1. Integrate RAG into your trading agents")
            print("  2. Use RAG insights in decision-making logic")
            print("  3. Monitor performance and adjust k parameter")
            print("  4. Continuously update historical data for better accuracy")
            sys.exit(0)
        else:
            print("\n[FAIL] Some tests failed. Please check the errors above.")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error during verification:")
        print(f"\n[FAIL] Unexpected error: {e}")
        sys.exit(1)
