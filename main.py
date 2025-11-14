"""Main entry point for autonomous Bitcoin trading system.

WHY THIS FILE EXISTS:
    This is the main control loop that runs 24/7, orchestrating the entire
    autonomous trading system. It coordinates data collection, AI analysis,
    strategy selection, risk management, and trade execution.

ARCHITECTURE (7-Node LangGraph Workflow):
    1. PARALLEL data collection (3 sources simultaneously: Binance, CoinMarketCap, Blockchain.com)
    2. Calculate technical indicators (RSI, MACD, ATR, etc.)
    3. SELECT STRATEGY (NEW): Detect market regime, select DCA/SWING/DAY
    4. SEQUENTIAL AI analysis (4 LLM agents):
       - Market Analysis (technical indicators + RAG historical patterns)
       - Sentiment Analysis (Fear & Greed Index)
       - Risk Assessment (on-chain metrics + volatility)
       - DCA Decision (final buy/hold decision)
    5. Guardrails (pre-execution safety checks)
    6. Execution via Position Manager (if approved)
    7. Portfolio monitoring (every 30 minutes, check stop-losses)

KEY ABBREVIATIONS:
    - DCA: Dollar-Cost Averaging (buying fixed USD amounts regularly)
    - ATR: Average True Range (volatility measure for stop-loss placement)
    - RSI: Relative Strength Index (momentum indicator, 0-100 scale)
    - MACD: Moving Average Convergence Divergence (trend strength)
    - LLM: Large Language Model (AI agent like Mistral-7B)
    - RAG: Retrieval-Augmented Generation (query historical patterns)
    - BTC: Bitcoin
    - P&L: Profit & Loss

TRADING CYCLE (Every 30 minutes):
    1. Monitor existing positions (update prices, check stop-losses)
    2. Load configuration (Google Sheets or defaults)
    3. Run LangGraph workflow (1-2 minutes, calls 4 LLM agents)
    4. Apply guardrails (validate trade decision)
    5. Execute trade through Position Manager (if buy signal)
    6. Log results and send Telegram notifications

Usage:
    python main.py

To stop:
    Press Ctrl+C (will complete current cycle first)
"""

import asyncio
import logging
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Workflow and guardrails
from graph.trading_workflow import run_trading_cycle
from guardrails.safety_checks import run_all_guardrails

# Configuration
from config.settings import Settings
from tools.google_sheets_sync import GoogleSheetsSync

# Position management
from tools.position_manager import PositionManager
from tools.binance_client import BinanceClient

# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================


def setup_logging():
    """Configure comprehensive logging.

    Logs to both file and console.
    File: logs/trading_system.log (appends, no rotation for simplicity)
    Console: INFO level

    Sets third-party loggers to WARNING to reduce noise.
    """
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("logs/trading_system.log"),
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Set third-party loggers to WARNING to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

    logging.info("[OK] Logging configured")


# ============================================================================
# SHUTDOWN HANDLING
# ============================================================================

SHUTDOWN = False


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully.

    Sets shutdown flag to complete current cycle before exiting.

    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global SHUTDOWN
    logging.info("\n" + "=" * 60)
    logging.info(" SHUTDOWN SIGNAL RECEIVED")
    logging.info("Completing current cycle before exit...")
    logging.info("=" * 60)
    SHUTDOWN = True


# ============================================================================
# TELEGRAM NOTIFICATIONS (OPTIONAL)
# ============================================================================


async def send_telegram_notification(message: str):
    """Send Telegram notification (optional).

    Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env

    Args:
        message: Notification text (supports HTML formatting)

    Example:
        >>> await send_telegram_notification("<b>Trading alert!</b>")
    """
    try:
        settings = Settings.get_instance()

        # Check if Telegram is configured
        if not hasattr(settings, "TELEGRAM_BOT_TOKEN") or not settings.TELEGRAM_BOT_TOKEN:
            logging.debug("Telegram not configured, skipping notification")
            return

        import httpx

        url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)

            if response.status_code == 200:
                logging.info(" Telegram notification sent")
            else:
                logging.warning(f"[WARN] Telegram failed: {response.status_code}")

    except Exception as e:
        logging.warning(f"[WARN] Telegram notification failed: {e}")


# ============================================================================
# TRADING CYCLE EXECUTION
# ============================================================================


async def run_one_cycle(
    cycle_number: int,
    position_manager: PositionManager,
    binance_client: BinanceClient,
    sheets_sync: Optional[GoogleSheetsSync] = None
) -> bool:
    """Run one complete trading cycle.

    Flow:
    1. Monitor existing positions (update prices, check stop-losses)
    2. Load configuration (Google Sheets -> local defaults)
    3. Run LangGraph workflow (parallel data + sequential analysis)
    4. Apply guardrails (pre-execution safety checks)
    5. Execute trade through Position Manager (if approved)
    6. Log results and position statistics
    7. Send Telegram notification

    Args:
        cycle_number: Cycle counter for logging
        position_manager: PositionManager instance for position tracking
        binance_client: BinanceClient instance for price data
        sheets_sync: Optional GoogleSheetsSync instance for dynamic config

    Returns:
        bool: True if successful, False if failed

    Example:
        >>> sheets = GoogleSheetsSync()
        >>> manager = PositionManager(initial_budget=10000)
        >>> client = BinanceClient()
        >>> success = await run_one_cycle(1, manager, client, sheets)
        >>> if success:
        ...     print("Cycle completed successfully")
    """
    logging.info("\n" + "=" * 60)
    logging.info(f"[STARTING] TRADING CYCLE #{cycle_number}")
    logging.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info("=" * 60)

    try:
        # =====================================================================
        # STEP 1: MONITOR EXISTING POSITIONS
        # =====================================================================
        logging.info("\n[POSITIONS] Monitoring existing positions...")

        try:
            # Get current BTC price
            current_price_data = binance_client.get_current_price("BTCUSDT")
            current_price = current_price_data.price
            logging.info(f"[PRICE] Current BTC: ${current_price:,.2f}")

            # Get open positions before monitoring
            open_positions_before = position_manager.get_open_positions()

            # Update all positions with current price
            update_result = position_manager.update_all_positions(current_price)

            # Check for emergency mode
            if update_result.get('emergency_triggered'):
                logging.critical("\n" + "!" * 60)
                logging.critical("[EMERGENCY] PORTFOLIO LOSS EXCEEDS 25% THRESHOLD!")
                logging.critical("Closing all positions immediately...")
                logging.critical("!" * 60)

                # Close all positions
                close_result = position_manager.close_all_positions(current_price)

                # Send emergency notification
                emergency_msg = (
                    f"[EMERGENCY] <b>EMERGENCY STOP TRIGGERED</b>\n\n"
                    f"Portfolio loss exceeded 25% threshold\n"
                    f"All positions closed\n"
                    f"Positions closed: {close_result['closed_count']}\n"
                    f"Total realized P&L: ${close_result['total_realized_pnl']:,.2f}"
                )
                await send_telegram_notification(emergency_msg)

                logging.info("[EMERGENCY] All positions closed. System continuing in safe mode.")

            # Check stop-losses
            triggered_stops = position_manager.check_stop_losses(current_price)

            if triggered_stops:
                logging.warning(f"\n[STOP-LOSS] {len(triggered_stops)} stop-loss(es) triggered!")

                for position in triggered_stops:
                    # Execute stop-loss
                    stop_result = position_manager.execute_stop_loss(position, current_price)

                    logging.warning(
                        f"   Position {position.position_id}: "
                        f"Stopped at ${current_price:,.2f} | "
                        f"P&L: ${stop_result['realized_pnl']:+,.2f} "
                        f"({stop_result['realized_pnl_pct']:+.2%})"
                    )

                    # Send stop-loss notification
                    stop_msg = (
                        f"[STOP-LOSS] <b>Stop-Loss Executed</b>\n\n"
                        f"Strategy: {position.strategy.upper()}\n"
                        f"Entry: ${position.entry_price:,.2f}\n"
                        f"Exit: ${current_price:,.2f}\n"
                        f"P&L: ${stop_result['realized_pnl']:+,.2f} ({stop_result['realized_pnl_pct']:+.2%})"
                    )
                    await send_telegram_notification(stop_msg)

            # Log positions with large moves (>2%)
            large_moves = update_result.get('positions_with_large_moves', [])
            if large_moves:
                logging.info(f"\n[ALERT] {len(large_moves)} position(s) with large moves:")
                for move in large_moves:
                    logging.info(
                        f"   {move['position_id']}: {move['change']:+.2%} "
                        f"(${move['unrealized_pnl']:+,.2f})"
                    )

            # Get budget stats
            budget = position_manager.get_budget_stats()
            logging.info(
                f"\n[BUDGET] Portfolio: ${budget['portfolio_value']:,.2f} | "
                f"P&L: ${budget['total_pnl']:+,.2f} | "
                f"Open: {len(open_positions_before)} positions | "
                f"Allocated: {budget['allocation_pct']:.1%}"
            )

        except Exception as e:
            logging.error(f"[ERROR] Position monitoring failed: {e}")
            logging.exception("Position monitoring error:")

        # =====================================================================
        # STEP 2: LOAD CONFIGURATION
        # =====================================================================
        # WHY: Configuration can be dynamically adjusted via Google Sheets
        # without code changes. This allows tweaking parameters based on
        # market conditions or backtesting results.
        #
        # DCA (Dollar-Cost Averaging): Buy fixed USD amounts when conditions are met
        # ATR (Average True Range): Volatility measure used for stop-loss placement
        #
        # WHY THESE VALUES:
        # - 3.0% DCA threshold: Only buy on significant dips (not noise)
        # - $100 per trade: Small enough to avoid large losses, big enough to matter
        # - 1.5x ATR multiplier: Gives position room to breathe without getting stopped out by normal volatility
        # - 20% max position: Prevents over-concentration in single trade
        # - 80% max exposure: Keeps 20% USD for future opportunities
        # - 25% emergency stop: Circuit breaker to prevent catastrophic losses
        # =====================================================================
        default_config = {
            "dca_threshold": 3.0,  # DCA trigger: Only buy if price drops 3.0% or more in 24h
            "dca_amount": 100,  # DCA amount: Spend exactly $100 USD per buy (NOT 100 BTC!)
            "atr_multiplier": 1.5,  # Stop-loss: Place stop at (entry_price - 1.5 * ATR)
            "max_position_size": 0.20,  # Max 20% of portfolio per single trade
            "max_total_exposure": 0.80,  # Max 80% total BTC exposure (keep 20% USD)
            "emergency_stop": 0.25,  # Emergency: Close all if portfolio drops 25%
            "max_trades_per_hour": 5,  # Rate limit: Max 5 trades/hour to avoid overtrading
        }

        # Load configuration from Google Sheets (if available)
        config = default_config.copy()
        if sheets_sync:
            try:
                logging.info("[CONFIG] Loading configuration from Google Sheets...")
                sheets_config = sheets_sync.get_config()

                # Map Google Sheets config to our internal config keys
                if "dca_percentage" in sheets_config:
                    config["dca_threshold"] = sheets_config["dca_percentage"]
                if "atr_multiplier" in sheets_config:
                    config["atr_multiplier"] = sheets_config["atr_multiplier"]
                if "max_position_size" in sheets_config:
                    config["max_position_size"] = sheets_config["max_position_size"]
                if "global_safeguard_threshold" in sheets_config:
                    config["emergency_stop"] = sheets_config["global_safeguard_threshold"]

                logging.info("[OK] Configuration loaded from Google Sheets")
                logging.info(f"   DCA Threshold: {config['dca_threshold']}%")
                logging.info(f"   ATR Multiplier: {config['atr_multiplier']}x")
                logging.info(f"   Max Position: {config['max_position_size']*100}%")

            except Exception as e:
                logging.warning(f"[WARN] Failed to load Google Sheets config: {e}")
                logging.info("[INFO] Using default configuration")
        else:
            logging.info("[INFO] Google Sheets not configured, using default configuration")

        # =====================================================================
        # STEP 3: RUN LANGGRAPH WORKFLOW (7-Node State Machine)
        # =====================================================================
        # WHY: LangGraph coordinates 7 specialized nodes in a state machine:
        #   1. PARALLEL data collection (Binance, CoinMarketCap, Blockchain.com)
        #   2. Calculate indicators (RSI, MACD, ATR, SMA, EMA)
        #   3. SELECT STRATEGY (NEW): Detect regime, select DCA/SWING/DAY
        #   4. Market Analysis Agent: Technical analysis + RAG historical patterns
        #   5. Sentiment Analysis Agent: Fear & Greed Index interpretation
        #   6. Risk Assessment Agent: On-chain metrics + volatility evaluation
        #   7. DCA Decision Agent: Final buy/hold decision
        #
        # TIMING: Takes 1-2 minutes because it calls 4 LLM (Large Language Model)
        # agents sequentially (Mistral-7B via OpenRouter, HuggingFace API)
        #
        # OUTPUT: TradingState dict with all analysis results and trade decision
        # =====================================================================
        logging.info("\n[PROCESSING] Running LangGraph workflow...")
        logging.info("   This may take 1-2 minutes (multiple LLM agents)...")

        # Get current portfolio state from Position Manager
        portfolio_state = position_manager.get_portfolio_state()

        result = await run_trading_cycle(config, portfolio_state)
        logging.info("[OK] Workflow complete")

        # =====================================================================
        # STEP 4: APPLY GUARDRAILS
        # =====================================================================
        logging.info("\n[SAFETY] Applying guardrails...")
        result = run_all_guardrails(result)
        logging.info("[OK] Guardrails passed")

        # Log results
        logging.info("\n" + "-" * 60)
        logging.info("[DATA] CYCLE RESULTS")
        logging.info("-" * 60)

        # Market data
        if result.get("market_data"):
            md = result["market_data"]
            logging.info(f"[FINANCIAL] BTC Price: ${md.price:,.2f} ({md.change_24h:+.2f}%)")
        else:
            logging.warning("[WARN] No market data")

        # Indicators
        if result.get("indicators"):
            ind = result["indicators"]
            logging.info(f"[ANALYSIS] RSI: {ind.rsi_14:.1f} | MACD: {ind.macd:.1f}")
        else:
            logging.warning("[WARN] No indicators")

        # Market analysis
        if result.get("market_analysis"):
            ma = result["market_analysis"]
            logging.info(
                f"[ANALYZING] Market: {ma['trend'].upper()} (conf: {ma['confidence']:.0%})"
            )
        else:
            logging.warning("[WARN] No market analysis")

        # Sentiment
        if result.get("sentiment_analysis"):
            sa = result["sentiment_analysis"]
            logging.info(
                f"[SENTIMENT] Sentiment: {sa['sentiment'].upper()} (conf: {sa['confidence']:.0%})"
            )
        else:
            logging.warning("[WARN] No sentiment analysis")

        # Risk
        if result.get("risk_assessment"):
            ra = result["risk_assessment"]
            logging.info(
                f"[WARN] Risk: ${ra['recommended_position_usd']:.2f} (approved: {ra['approved']})"
            )
        else:
            logging.warning("[WARN] No risk assessment")

        # Strategy recommendation (NEW)
        if result.get("strategy_recommendation"):
            sr = result["strategy_recommendation"]
            logging.info(
                f"[STRATEGY] Selected: {sr['strategy'].upper()} | "
                f"Regime: {sr['market_regime']} | "
                f"Confidence: {sr['confidence']:.0%} | "
                f"Adaptive Trigger: {sr['adaptive_dca_trigger']:.1f}%"
            )
        else:
            logging.warning("[WARN] No strategy recommendation")

        # Final decision
        trade_executed = False
        position_result = None

        if result.get("trade_decision"):
            td = result["trade_decision"]
            logging.info(f"\n[DECISION] DECISION: {td.action.upper()}")
            logging.info(f"   Amount: {td.amount:.4f} BTC")
            logging.info(f"   Entry: ${td.entry_price:,.2f}")
            logging.info(f"   Confidence: {td.confidence:.0%}")
            logging.info(f"   Reasoning: {td.reasoning[:100]}...")

            # =====================================================================
            # STEP 5: EXECUTE TRADE THROUGH POSITION MANAGER
            # =====================================================================
            if td.action.upper() == "BUY":
                try:
                    # Get indicators for ATR calculation
                    indicators = result.get("indicators")
                    if not indicators or not hasattr(indicators, 'atr_14'):
                        logging.warning("[WARN] No ATR data, using default 2% for stop-loss")
                        atr = td.entry_price * 0.02  # Fallback: 2% of entry price
                    else:
                        atr = indicators.atr_14

                    # Get selected strategy from Strategy Switcher (NEW)
                    strategy_rec = result.get("strategy_recommendation", {})
                    strategy = strategy_rec.get("strategy", "dca").lower()
                    adaptive_trigger = strategy_rec.get("adaptive_dca_trigger", config.get("dca_threshold", 3.0))

                    # Fallback validation
                    if strategy not in ['dca', 'swing', 'day']:
                        logging.warning(f"[WARN] Invalid strategy '{strategy}', defaulting to DCA")
                        strategy = 'dca'

                    # Calculate position size in USD
                    amount_usd = td.amount * td.entry_price

                    # Calculate drop percentage for DCA (if market data available)
                    # Use adaptive trigger if strategy is DCA
                    drop_pct = None
                    if result.get("market_data") and hasattr(result["market_data"], 'change_24h'):
                        drop_pct = abs(result["market_data"].change_24h)

                    # Override with adaptive trigger for DCA strategy
                    if strategy == 'dca' and drop_pct and drop_pct < adaptive_trigger:
                        logging.info(f"[INFO] Price drop {drop_pct:.2f}% below adaptive trigger {adaptive_trigger:.1f}%")

                    # Build RAG context (if available)
                    rag_context = None
                    if result.get("rag_insights"):
                        rag_insights = result["rag_insights"]
                        rag_context = {
                            'success_rate': rag_insights.get('success_rate', 0),
                            'expected_outcome': rag_insights.get('expected_outcome', 0),
                            'similar_patterns': rag_insights.get('similar_patterns', 0),
                            'confidence': rag_insights.get('confidence', 0),
                        }

                    # Try to open position
                    logging.info(f"\n[EXECUTION] Attempting to open {strategy.upper()} position...")
                    logging.info(f"   Amount: ${amount_usd:.2f}")
                    logging.info(f"   Entry: ${td.entry_price:,.2f}")
                    logging.info(f"   ATR: ${atr:.2f}")
                    if drop_pct:
                        logging.info(f"   Drop: {drop_pct:.2f}%")

                    can_open, reason = position_manager.can_open_position(
                        strategy=strategy,
                        amount_usd=amount_usd,
                        current_price=td.entry_price,
                        drop_percentage=drop_pct
                    )

                    if can_open:
                        # Open the position
                        position_result = position_manager.open_position(
                            strategy=strategy,
                            entry_price=td.entry_price,
                            amount_usd=amount_usd,
                            atr=atr,
                            signal_data={
                                'reasoning': td.reasoning,
                                'confidence': td.confidence,
                                'drop_percentage': drop_pct
                            },
                            rag_context=rag_context
                        )

                        trade_executed = True

                        logging.info(f"[OK] Position opened successfully!")
                        logging.info(f"   Position ID: {position_result['position_id']}")
                        logging.info(f"   Amount: {position_result['amount_btc']:.6f} BTC")
                        logging.info(f"   Stop-Loss: ${position_result['stop_loss']:,.2f}")

                        # Send execution notification
                        exec_msg = (
                            f"[TRADE] <b>Position Opened</b>\n\n"
                            f"Strategy: {strategy.upper()}\n"
                            f"Entry: ${td.entry_price:,.2f}\n"
                            f"Amount: {position_result['amount_btc']:.6f} BTC (${amount_usd:.2f})\n"
                            f"Stop-Loss: ${position_result['stop_loss']:,.2f}\n"
                            f"Confidence: {td.confidence:.0%}\n\n"
                            f"Reasoning: {td.reasoning[:150]}..."
                        )
                        await send_telegram_notification(exec_msg)

                    else:
                        logging.warning(f"[BLOCKED] Cannot open position: {reason}")
                        # Send blocked notification
                        blocked_msg = (
                            f"[BLOCKED] <b>Trade Blocked</b>\n\n"
                            f"Reason: {reason}\n"
                            f"Entry: ${td.entry_price:,.2f}\n"
                            f"Amount: ${amount_usd:.2f}"
                        )
                        await send_telegram_notification(blocked_msg)

                except Exception as e:
                    logging.error(f"[ERROR] Position execution failed: {e}")
                    logging.exception("Execution error:")

            elif td.action.upper() in ["HOLD", "WAIT"]:
                logging.info("[INFO] Holding - no trade executed")

        else:
            logging.warning("[WARN] No trade decision")

        # Errors
        errors = result.get("errors", [])
        if errors:
            logging.warning(f"\n[WARN] Errors ({len(errors)}):")
            for error in errors:
                logging.warning(f"   - {error}")
        else:
            logging.info("\n[OK] No errors")

        logging.info("-" * 60)

        # =====================================================================
        # STEP 6: LOG FINAL POSITION STATISTICS
        # =====================================================================
        try:
            stats = position_manager.get_statistics()
            budget = position_manager.get_budget_stats()

            logging.info("\n[PORTFOLIO] Final Portfolio State:")
            logging.info(f"   Value: ${budget['portfolio_value']:,.2f}")
            logging.info(f"   Unrealized P&L: ${budget['unrealized_pnl']:+,.2f}")
            logging.info(f"   Realized P&L: ${budget['realized_pnl']:+,.2f}")
            logging.info(f"   Total P&L: ${budget['total_pnl']:+,.2f}")
            logging.info(f"   Open Positions: {stats['open_positions']}")
            logging.info(f"   Closed Positions: {stats['closed_positions']}")
            logging.info(f"   Stopped Positions: {stats['stopped_positions']}")

            if stats.get('win_rate'):
                logging.info(f"\n[PERFORMANCE] Trading Performance:")
                logging.info(f"   Win Rate: {stats['win_rate']:.1%}")
                logging.info(f"   Avg P&L: {stats['avg_realized_pnl_pct']:+.2%}")

        except Exception as e:
            logging.error(f"[ERROR] Failed to log position statistics: {e}")

        logging.info("-" * 60)

        # Send Telegram notification
        if result.get("trade_decision") and result.get("market_data"):
            td = result["trade_decision"]
            md = result["market_data"]

            # Build notification message
            notification = f"[SYSTEM] <b>Trading Cycle #{cycle_number}</b>\n\n"
            notification += f"[FINANCIAL] BTC: ${md.price:,.2f} ({md.change_24h:+.2f}%)\n"

            if result.get("indicators"):
                ind = result["indicators"]
                notification += f"[DATA] RSI: {ind.rsi_14:.1f}\n"

            notification += "\n"

            if result.get("market_analysis"):
                ma = result["market_analysis"]
                notification += f"[ANALYZING] Market: {ma['trend']}\n"

            if result.get("sentiment_analysis"):
                sa = result["sentiment_analysis"]
                notification += f"[SENTIMENT] Sentiment: {sa['sentiment']}\n"

            notification += f"\n<b>Decision: {td.action.upper()}</b>\n"
            notification += f"Amount: {td.amount:.4f} BTC\n"
            notification += f"Confidence: {td.confidence:.0%}\n\n"
            notification += f"Reasoning: {td.reasoning[:150]}..."

            if errors:
                notification += f"\n\n[WARN] Errors: {len(errors)}"

            await send_telegram_notification(notification)

        logging.info(f"[OK] Cycle #{cycle_number} complete\n")
        return True

    except Exception as e:
        logging.error(f"[FAIL] Cycle #{cycle_number} FAILED: {e}")
        logging.exception("Full traceback:")

        # Send error notification
        error_notification = (
            f"[FAIL] <b>Cycle #{cycle_number} FAILED</b>\n\n"
            f"Error: {str(e)[:200]}"
        )
        await send_telegram_notification(error_notification)

        return False


# ============================================================================
# MAIN SCHEDULER
# ============================================================================


async def main():
    """Main scheduler loop - runs 24/7.

    Executes trading cycles every 30 minutes.
    Handles errors gracefully.
    Allows clean shutdown with Ctrl+C.

    Flow:
        1. Setup logging and signal handlers
        2. Run trading cycles in infinite loop
        3. Wait 30 minutes between cycles
        4. Handle failures (pause after 3 consecutive)
        5. Shutdown gracefully on Ctrl+C

    Error Handling:
        - Never crashes, always recovers
        - Pauses 1 hour after 3 consecutive failures
        - Logs all errors with full traceback
        - Sends Telegram alerts on failures
    """
    # Setup
    setup_logging()

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Initialize Google Sheets sync (optional)
    try:
        logging.info("[CONFIG] Initializing Google Sheets sync...")
        sheets_sync = GoogleSheetsSync()
        logging.info(f"[OK] Google Sheets sync initialized: {sheets_sync}")
    except Exception as e:
        logging.warning(f"[WARN] Google Sheets sync initialization failed: {e}")
        logging.info("[INFO] Will use default configuration only")
        sheets_sync = None

    # Initialize Position Manager and Binance Client
    try:
        logging.info("[SYSTEM] Initializing Position Manager...")

        # Set initial budget (can be configured via environment or settings)
        settings = Settings.get_instance()
        initial_budget = getattr(settings, 'INITIAL_TRADING_BUDGET', 10000.0)

        position_manager = PositionManager(initial_budget=initial_budget)
        logging.info(f"[OK] Position Manager initialized with ${initial_budget:,.2f} budget")

        # Initialize Binance client
        binance_client = BinanceClient()
        logging.info("[OK] Binance client initialized")

    except Exception as e:
        logging.critical(f"[FAIL] Failed to initialize trading components: {e}")
        logging.exception("Initialization error:")
        sys.exit(1)

    # Welcome message
    logging.info("\n" + "=" * 60)
    logging.info("[SYSTEM] AUTONOMOUS BITCOIN TRADING SYSTEM")
    logging.info("Multi-Agent LLM System | LangChain + LangGraph")
    logging.info("Position Manager | ATR Stop-Losses | Budget Management")
    logging.info("=" * 60)
    logging.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logging.info(f"Initial budget: ${initial_budget:,.2f}")
    logging.info("Cycle interval: 30 minutes")
    logging.info("Press Ctrl+C to shutdown gracefully")
    if sheets_sync:
        logging.info("Configuration: Google Sheets (with local fallback)")
    else:
        logging.info("Configuration: Local defaults only")
    logging.info("=" * 60 + "\n")

    # Send startup notification
    startup_msg = (
        f"[STARTING] <b>Trading System Started</b>\n\n"
        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Budget: ${initial_budget:,.2f}\n"
        f"Cycle: Every 30 minutes\n"
        f"Mode: Autonomous\n\n"
        f"Features:\n"
        f"- Multi-strategy (DCA/Swing/Day)\n"
        f"- ATR-based stop-losses\n"
        f"- Budget management\n"
        f"- Emergency safeguards"
    )
    await send_telegram_notification(startup_msg)

    # Main loop
    cycle_number = 0
    consecutive_failures = 0

    while not SHUTDOWN:
        cycle_number += 1

        # Run cycle (pass position manager, binance client, and Google Sheets sync)
        success = await run_one_cycle(cycle_number, position_manager, binance_client, sheets_sync)

        if success:
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            logging.error(f"[WARN] Consecutive failures: {consecutive_failures}")

            # Pause if too many failures
            if consecutive_failures >= 3:
                logging.error("[ALERT] 3 CONSECUTIVE FAILURES - Pausing for 1 hour")
                pause_msg = (
                    f"[ALERT] <b>SYSTEM PAUSED</b>\n\n"
                    f"3 consecutive failures\n"
                    f"Pausing for 1 hour"
                )
                await send_telegram_notification(pause_msg)

                # Wait 1 hour (check shutdown every minute)
                for _ in range(60):
                    if SHUTDOWN:
                        break
                    await asyncio.sleep(60)

                consecutive_failures = 0
                logging.info(" Resuming after pause")
                continue

        # Wait for next cycle (30 minutes)
        if not SHUTDOWN:
            next_run = datetime.now() + timedelta(minutes=30)
            logging.info(f"[SCHEDULED] Next cycle: {next_run.strftime('%H:%M:%S')}")
            logging.info("[SLEEPING] Sleeping 30 minutes...\n")

            # Sleep in small intervals to check shutdown flag
            for _ in range(30):  # 30 minutes = 30 * 1 minute
                if SHUTDOWN:
                    break
                await asyncio.sleep(60)  # 1 minute

    # Shutdown sequence
    logging.info("\n" + "=" * 60)
    logging.info(" SHUTTING DOWN")
    logging.info("=" * 60)
    logging.info(f"Total cycles run: {cycle_number}")
    logging.info(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Final portfolio summary
    try:
        stats = position_manager.get_statistics()
        budget = position_manager.get_budget_stats()

        logging.info("\n[FINAL PORTFOLIO SUMMARY]")
        logging.info(f"Initial Budget: ${initial_budget:,.2f}")
        logging.info(f"Final Value: ${budget['portfolio_value']:,.2f}")
        logging.info(f"Total P&L: ${budget['total_pnl']:+,.2f} ({(budget['total_pnl']/initial_budget)*100:+.2f}%)")
        logging.info(f"Realized P&L: ${budget['realized_pnl']:+,.2f}")
        logging.info(f"Unrealized P&L: ${budget['unrealized_pnl']:+,.2f}")
        logging.info(f"\nTrading Statistics:")
        logging.info(f"Total Positions: {stats['total_positions']}")
        logging.info(f"Closed: {stats['closed_positions']}")
        logging.info(f"Stopped: {stats['stopped_positions']}")
        logging.info(f"Still Open: {stats['open_positions']}")

        if stats.get('win_rate'):
            logging.info(f"\nPerformance:")
            logging.info(f"Win Rate: {stats['win_rate']:.1%}")
            logging.info(f"Avg P&L: {stats['avg_realized_pnl_pct']:+.2%}")
            logging.info(f"Best Trade: {stats['best_trade_pct']:+.2%}")
            logging.info(f"Worst Trade: {stats['worst_trade_pct']:+.2%}")

        # Build comprehensive shutdown notification
        shutdown_msg = (
            f" <b>Trading System Shutdown</b>\n\n"
            f"Total cycles: {cycle_number}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"<b>Portfolio Summary</b>\n"
            f"Initial: ${initial_budget:,.2f}\n"
            f"Final: ${budget['portfolio_value']:,.2f}\n"
            f"P&L: ${budget['total_pnl']:+,.2f} ({(budget['total_pnl']/initial_budget)*100:+.2f}%)\n\n"
            f"Trades: {stats['total_positions']} total\n"
            f"Open: {stats['open_positions']}\n"
            f"Closed: {stats['closed_positions']}\n"
            f"Stopped: {stats['stopped_positions']}"
        )

        if stats.get('win_rate'):
            shutdown_msg += f"\n\nWin Rate: {stats['win_rate']:.1%}"

    except Exception as e:
        logging.error(f"[ERROR] Failed to generate final summary: {e}")
        shutdown_msg = (
            f" <b>Trading System Shutdown</b>\n\n"
            f"Total cycles: {cycle_number}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    logging.info("=" * 60)

    # Send shutdown notification
    await send_telegram_notification(shutdown_msg)

    logging.info(" Goodbye!\n")


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """Entry point for the trading system.

    Usage:
        python main.py

    To stop:
        Press Ctrl+C (will complete current cycle first)

    Environment Variables:
        Required:
            - OPENROUTER_API_KEY: OpenRouter API key for LLMs
            - BINANCE_API_KEY: Binance API key for market data
            - BINANCE_API_SECRET: Binance API secret

        Optional:
            - TELEGRAM_BOT_TOKEN: Telegram bot token for notifications
            - TELEGRAM_CHAT_ID: Telegram chat ID for notifications
            - COINMARKETCAP_API_KEY: CoinMarketCap API key for sentiment
            - CRYPTOQUANT_API_KEY: CryptoQuant API key for on-chain data
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[WARN] KeyboardInterrupt caught")
    except Exception as e:
        logging.critical(f" FATAL ERROR: {e}")
        logging.exception("Full traceback:")
        sys.exit(1)
