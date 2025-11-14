"""
Test script for Prompt 14: Main Entry Point

Runs one cycle to test the complete system.
"""

import asyncio
import logging
from main import run_one_cycle, setup_logging

print("=" * 60)
print("TESTING MAIN ENTRY POINT (PROMPT 14)")
print("=" * 60)

print("\n[WARN]  This will run ONE complete cycle:")
print("   - Fetch real BTC data")
print("   - Run all 4 agents (OpenRouter)")
print("   - Apply guardrails")
print("   - Log results")
print("   - Take ~30-60 seconds")
print()

input("Press ENTER to start test cycle...")

# Setup logging
setup_logging()

# Run one cycle
try:
    success = asyncio.run(run_one_cycle(cycle_number=1))
    
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    
    if success:
        print("\n[OK] CYCLE COMPLETED SUCCESSFULLY!")
        print("\nThe system:")
        print("  [OK] Fetched market data")
        print("  [OK] Ran all analysis agents")
        print("  [OK] Applied guardrails")
        print("  [OK] Made a decision")
        print("  [OK] Handled errors gracefully")
        
        print("\n READY FOR PRODUCTION!")
        print("\nTo run 24/7:")
        print("  python main.py")
        print("\nTo stop:")
        print("  Press Ctrl+C (completes current cycle first)")
        
    else:
        print("\n[FAIL] CYCLE FAILED")
        print("\nCheck the logs above for errors.")
        print("Common issues:")
        print("  - API keys not set in .env")
        print("  - Network connection issues")
        print("  - Rate limits exceeded")
    
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"\n[FAIL] Test failed: {e}")
    import traceback
    traceback.print_exc()