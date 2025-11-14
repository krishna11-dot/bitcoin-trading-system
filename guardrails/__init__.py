"""Safety guardrails and validation checks.

This module implements pre-execution safety mechanisms to prevent
catastrophic trading errors and ensure system reliability.

The main function is run_all_guardrails() which runs all checks
and blocks trades if ANY check fails.
"""

from guardrails.safety_checks import (
    check_emergency_stop,
    check_position_limits,
    check_price_sanity,
    check_sufficient_balance,
    check_total_exposure,
    check_trade_frequency,
    get_recent_trades_count,
    record_trade,
    run_all_guardrails,
)

__all__ = [
    "run_all_guardrails",
    "check_sufficient_balance",
    "check_position_limits",
    "check_total_exposure",
    "check_emergency_stop",
    "check_trade_frequency",
    "check_price_sanity",
    "record_trade",
    "get_recent_trades_count",
]
