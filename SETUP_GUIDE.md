# Complete Setup Guide - Autonomous Bitcoin Trading System

## 🎯 Quick Answer to Your Questions

**Q: Is real Binance free?**
- ❌ **Real Binance**: Costs real money, trades real Bitcoin, has real financial risk
- ✅ **Binance Testnet**: Completely FREE, fake "test" Bitcoin, zero risk, perfect for testing!

**You should use Testnet first**, then switch to real trading only when confident.

---

## 📋 Step-by-Step Setup

### STEP 1: Get FREE Binance Testnet API Keys (5 minutes)

#### 1.1 Create Testnet Account
```
1. Go to: https://testnet.binance.vision/
2. Click "Login" → Sign in with your GitHub account
3. (This is separate from real Binance - no credit card needed!)
```

#### 1.2 Generate API Keys
```
1. Once logged in, click "Generate HMAC_SHA256 Key"
2. Label it: "MyTradingBot"
3. Click "Generate"
4. SAVE BOTH KEYS IMMEDIATELY:
   - API Key: starts with "abc123..."
   - Secret Key: starts with "xyz789..."

⚠️ WARNING: Secret key shown only ONCE! Save it now!
```

#### 1.3 Get Free Test Bitcoin
```
1. In testnet dashboard, find "Spot Test Network"
2. Click "Get Test Funds"
3. You'll receive free fake BTC and USDT to test with!
```

---

### STEP 2: Configure Your System

#### 2.1 Create .env File

```bash
# In your project root, create .env file
cd c:\Users\krish\bitcoin-trading-system
copy config\.env.example .env
```

#### 2.2 Edit .env with Your Keys

Open `.env` in Notepad and update:

```bash
# ============================================================================
# Binance Testnet (FREE - No Real Money)
# ============================================================================
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_secret_here
TESTNET_MODE=true
TRADING_MODE=PAPER

# ============================================================================
# Position Manager Settings
# ============================================================================
INITIAL_BUDGET=10000.0
DCA_ENABLED=true
SWING_ENABLED=true
DAY_ENABLED=false

# ============================================================================
# Telegram Alerts (Optional - Get from @BotFather)
# ============================================================================
TELEGRAM_BOT_TOKEN=your_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# ============================================================================
# LLM Keys (Free Tier)
# ============================================================================
HUGGINGFACE_API_KEY=your_key_here
OPENROUTER_API_KEY=your_key_here
```

---

### STEP 3: Configure Position Manager

Create a file `config_trading.py`:

```python
"""
Trading System Configuration

This file configures your Position Manager for 24/7 autonomous operation.
"""

from tools.position_manager import PositionManager

def setup_position_manager():
    """Initialize Position Manager with your settings."""

    # =========================================================================
    # BUDGET CONFIGURATION
    # =========================================================================
    # Starting capital (in USD equivalent)
    # Testnet: Use $10,000 fake money
    # Real trading: Adjust to your actual budget
    INITIAL_BUDGET = 10000.0

    # =========================================================================
    # INITIALIZE MANAGER
    # =========================================================================
    manager = PositionManager(
        initial_budget=INITIAL_BUDGET,
        positions_file="data/positions.json"
    )

    # =========================================================================
    # STRATEGY CONFIGURATION
    # =========================================================================

    # DCA Strategy (Dollar Cost Averaging)
    manager.STRATEGY_DEFAULTS["dca"]["enabled"] = True           # Enable DCA
    manager.STRATEGY_DEFAULTS["dca"]["atr_multiplier"] = 2.0     # Wide stops
    manager.STRATEGY_DEFAULTS["dca"]["allocation_limit"] = 0.5   # Max 50% of budget
    manager.STRATEGY_DEFAULTS["dca"]["time_between_buys"] = 3600 # 1 hour minimum

    # Swing Trading Strategy
    manager.STRATEGY_DEFAULTS["swing"]["enabled"] = True         # Enable Swing
    manager.STRATEGY_DEFAULTS["swing"]["atr_multiplier"] = 1.5   # Moderate stops
    manager.STRATEGY_DEFAULTS["swing"]["allocation_limit"] = 0.3 # Max 30% of budget

    # Day Trading Strategy (DISABLED BY DEFAULT)
    manager.STRATEGY_DEFAULTS["day"]["enabled"] = False          # Keep disabled
    manager.STRATEGY_DEFAULTS["day"]["atr_multiplier"] = 1.0     # Tight stops
    manager.STRATEGY_DEFAULTS["day"]["allocation_limit"] = 0.2   # Max 20% of budget

    # =========================================================================
    # EMERGENCY SAFEGUARDS
    # =========================================================================
    # These are already set by default, but you can adjust:
    # manager.EMERGENCY_STOP_THRESHOLD = -0.25  # -25% portfolio loss
    # manager.MAX_TOTAL_ALLOCATION = 0.95       # Keep 5% cash buffer

    print(f"[OK] Position Manager configured")
    print(f"     Budget: ${INITIAL_BUDGET:,.2f}")
    print(f"     DCA: {'Enabled' if manager.STRATEGY_DEFAULTS['dca']['enabled'] else 'Disabled'}")
    print(f"     Swing: {'Enabled' if manager.STRATEGY_DEFAULTS['swing']['enabled'] else 'Disabled'}")
    print(f"     Day: {'Enabled' if manager.STRATEGY_DEFAULTS['day']['enabled'] else 'Disabled'}")

    return manager


if __name__ == "__main__":
    # Test configuration
    manager = setup_position_manager()

    # Show budget stats
    stats = manager.get_budget_stats()
    print(f"\nBudget Status:")
    print(f"  Available: ${stats['available_capital']:,.2f}")
    print(f"  Allocated: ${stats['allocated_capital']:,.2f}")
    print(f"  Portfolio Value: ${stats['portfolio_value']:,.2f}")
```

**Test your configuration:**
```bash
python config_trading.py
```

---

### STEP 4: Integrate into main.py for 24/7 Operation

Update your `main.py`:

```python
"""
Main 24/7 Trading Loop

Monitors positions every 30 minutes and executes trading logic.
"""

import logging
import time
from datetime import datetime
from config_trading import setup_position_manager
from tools.binance_client import BinanceClient
from agents.rag_enhanced_market_analyst import RAGEnhancedMarketAnalyst
from agents.rag_enhanced_strategy_agent import RAGEnhancedStrategyAgent
from tools.indicator_calculator import IndicatorCalculator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trading.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def send_telegram_alert(message: str):
    """Send Telegram notification (implement if needed)."""
    try:
        import os
        import requests

        token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

        if token and chat_id:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message})
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")


def monitor_positions_loop():
    """
    Main 24/7 monitoring loop.

    Runs every 30 minutes:
    1. Update all position prices
    2. Check for stop-loss triggers
    3. Check emergency conditions
    4. Execute any necessary closures
    5. Send alerts
    """

    # Initialize components
    logger.info("=" * 80)
    logger.info("STARTING 24/7 TRADING SYSTEM")
    logger.info("=" * 80)

    manager = setup_position_manager()
    binance = BinanceClient()
    indicator_calc = IndicatorCalculator()

    # Send startup notification
    send_telegram_alert(
        "🤖 Trading System Started\n"
        f"Budget: ${manager.initial_budget:,.2f}\n"
        f"Strategies: DCA, Swing\n"
        "Monitoring every 30 minutes"
    )

    iteration = 0

    while True:
        try:
            iteration += 1
            logger.info(f"\n{'='*80}")
            logger.info(f"MONITORING CYCLE #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*80}")

            # ================================================================
            # STEP 1: Get Current Market Data
            # ================================================================
            logger.info("Fetching current market data...")

            try:
                market_data = binance.get_current_price("BTCUSDT")
                current_price = market_data.price

                logger.info(f"[OK] BTC Price: ${current_price:,.2f}")

            except Exception as e:
                logger.error(f"Failed to fetch price: {e}")
                time.sleep(300)  # Wait 5 minutes and retry
                continue

            # ================================================================
            # STEP 2: Update All Positions
            # ================================================================
            logger.info("Updating position prices...")

            result = manager.update_all_positions(current_price)

            logger.info(
                f"[OK] Updated {result['positions_updated']} positions\n"
                f"     Portfolio Value: ${result['portfolio_value']:,.2f}\n"
                f"     Portfolio P&L: {result['portfolio_pnl_pct']:+.2%}\n"
                f"     Unrealized P&L: ${result['total_unrealized_pnl']:+,.2f}"
            )

            # Report large moves
            if result['positions_with_large_moves']:
                for move in result['positions_with_large_moves']:
                    msg = (
                        f"📊 Large Move Alert\n"
                        f"Position: {move['position_id']}\n"
                        f"Change: {move['change']:+.2%}"
                    )
                    send_telegram_alert(msg)

            # ================================================================
            # STEP 3: Check Emergency Condition
            # ================================================================
            if result['emergency_triggered']:
                logger.critical("🚨 EMERGENCY CONDITION TRIGGERED!")

                # Send urgent alert
                send_telegram_alert(
                    "🚨🚨🚨 EMERGENCY STOP 🚨🚨🚨\n"
                    f"Portfolio down 25%!\n"
                    f"Value: ${result['portfolio_value']:,.2f}\n"
                    "Closing all positions..."
                )

                # Close all positions
                close_results = manager.close_all_positions(current_price)

                successful = sum(1 for r in close_results if r['success'])
                send_telegram_alert(
                    f"Emergency closure complete:\n"
                    f"{successful}/{len(close_results)} positions closed"
                )

                # Stop the system
                logger.critical("System halted due to emergency. Manual restart required.")
                break

            # ================================================================
            # STEP 4: Check Stop-Losses
            # ================================================================
            logger.info("Checking stop-losses...")

            triggered = manager.check_stop_losses(current_price)

            if triggered:
                logger.warning(f"[!] {len(triggered)} stop-losses triggered!")

                for position in triggered:
                    try:
                        # Execute stop-loss
                        result = manager.execute_stop_loss(position, current_price)

                        # Send alert
                        send_telegram_alert(
                            f"🚨 Stop-Loss Executed\n"
                            f"Position: {position.position_id}\n"
                            f"Strategy: {position.strategy.upper()}\n"
                            f"P&L: ${result['realized_pnl']:+,.2f} ({result['realized_pnl_pct']:+.2%})\n"
                            f"Capital Freed: ${result['capital_freed']:,.2f}"
                        )

                        logger.info(f"[OK] Executed stop-loss for {position.position_id}")

                    except Exception as e:
                        logger.error(f"Failed to execute stop-loss for {position.position_id}: {e}")
                        send_telegram_alert(f"❌ Stop-loss execution failed: {position.position_id}")
            else:
                logger.info("[OK] No stop-losses triggered")

            # ================================================================
            # STEP 5: Display Current Status
            # ================================================================
            stats = manager.get_statistics()
            budget_stats = stats['budget_stats']

            logger.info(
                f"\nCurrent Status:\n"
                f"  Open Positions: {stats['open_positions']}\n"
                f"  Allocated: ${budget_stats['allocated_capital']:,.2f} ({budget_stats['allocation_pct']:.1%})\n"
                f"  Available: ${budget_stats['available_capital']:,.2f}\n"
                f"  Emergency Mode: {stats['emergency_mode']}"
            )

            # ================================================================
            # STEP 6: Wait 30 Minutes
            # ================================================================
            wait_seconds = 1800  # 30 minutes
            logger.info(f"\n[...] Sleeping for {wait_seconds/60:.0f} minutes until next check...")
            logger.info(f"      Next check at: {datetime.fromtimestamp(time.time() + wait_seconds).strftime('%H:%M:%S')}")

            time.sleep(wait_seconds)

        except KeyboardInterrupt:
            logger.info("\n\n[!] System shutdown requested by user")
            send_telegram_alert("🛑 Trading system stopped by user")
            break

        except Exception as e:
            logger.exception(f"Error in monitoring loop:")
            send_telegram_alert(f"❌ Error in monitoring loop: {str(e)[:100]}")

            # Wait 5 minutes before retry
            logger.info("Waiting 5 minutes before retry...")
            time.sleep(300)


def main():
    """Entry point for 24/7 trading system."""

    # Create logs directory
    import os
    os.makedirs('logs', exist_ok=True)

    logger.info("Bitcoin Trading System Starting...")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        monitor_positions_loop()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        send_telegram_alert(f"🚨 FATAL ERROR: {str(e)[:100]}")
        raise


if __name__ == "__main__":
    main()
```

---

### STEP 5: Test Your Setup

#### 5.1 Test Position Manager Configuration
```bash
python config_trading.py
```

Expected output:
```
[OK] Position Manager configured
     Budget: $10,000.00
     DCA: Enabled
     Swing: Enabled
     Day: Disabled

Budget Status:
  Available: $10,000.00
  Allocated: $0.00
  Portfolio Value: $10,000.00
```

#### 5.2 Test Binance Connection
```bash
python -c "from tools.binance_client import BinanceClient; client = BinanceClient(); print(f'BTC: ${client.get_current_price(\"BTCUSDT\").price:,.2f}')"
```

#### 5.3 Start 24/7 Monitoring (Dry Run)
```bash
# This will run forever until you press Ctrl+C
python main.py
```

---

## 🎯 Summary: What You Need to Do

### ✅ Immediate Setup (15 minutes):

1. **Get Testnet Keys** (5 min)
   - Go to https://testnet.binance.vision/
   - Login with GitHub
   - Generate API key
   - Get free test funds

2. **Create .env File** (2 min)
   ```bash
   copy config\.env.example .env
   # Edit .env with your testnet keys
   ```

3. **Create config_trading.py** (3 min)
   - Copy the configuration code above
   - Set your budget and strategy preferences

4. **Update main.py** (5 min)
   - Copy the 24/7 monitoring code above
   - Customize alerts as needed

### ✅ Testing Phase (1-2 weeks):

1. **Run Tests**
   ```bash
   python config_trading.py          # Test configuration
   python test_position_manager_quick.py  # Test Position Manager
   python main.py                    # Start monitoring
   ```

2. **Monitor Testnet Trading**
   - Watch for 1-2 weeks
   - Verify stop-losses work
   - Check emergency triggers
   - Track performance

3. **Tune Parameters**
   - Adjust ATR multipliers if needed
   - Modify allocation limits
   - Fine-tune DCA intervals

### ✅ Go Live (When Ready):

1. **Get Real Binance API Keys**
   - Sign up at https://www.binance.com
   - Complete KYC verification
   - Generate API keys
   - **IMPORTANT**: Enable only "Spot Trading", disable withdrawals!

2. **Update .env**
   ```bash
   TESTNET_MODE=false
   TRADING_MODE=LIVE
   BINANCE_API_KEY=your_real_api_key
   BINANCE_API_SECRET=your_real_secret
   ```

3. **Start with Small Budget**
   - Begin with $100-$500
   - Monitor closely for first week
   - Scale up gradually

---

## 📞 Getting Help

If you encounter issues:

1. **Check Logs**: `logs/trading.log`
2. **Test Components Individually**:
   ```bash
   python config_trading.py
   python test_position_manager_quick.py
   ```
3. **Verify API Keys**: Make sure testnet keys are correct
4. **Check Telegram**: Ensure bot token and chat ID are valid

---

## 🚀 You're Ready!

Your Position Manager is **production-ready** with:
- ✅ Multi-strategy support (DCA, Swing, Day)
- ✅ ATR-based stop-losses
- ✅ Budget management
- ✅ Emergency safeguards (-25%)
- ✅ Time-based DCA protection
- ✅ 24/7 monitoring
- ✅ RAG integration
- ✅ Binance execution
- ✅ Telegram alerts

Start with testnet, test thoroughly, then go live when confident! 🎉
