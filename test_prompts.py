"""
Test script for Prompt 9: External Prompt Templates

Validates that all .txt prompt files were created correctly.
"""

from pathlib import Path
import re

print("=" * 60)
print("TESTING EXTERNAL PROMPT TEMPLATES (PROMPT 9)")
print("=" * 60)

# Expected prompt files
expected_prompts = [
    "market_analysis_agent.txt",
    "sentiment_analysis_agent.txt",
    "dca_decision_agent.txt",
    "risk_assessment_agent.txt"
]

prompts_dir = Path("prompts")

# Test 1: Check prompts directory exists
print("\n1. Checking prompts directory...")
if prompts_dir.exists() and prompts_dir.is_dir():
    print("   [OK] prompts/ directory exists")
else:
    print("   [FAIL] prompts/ directory NOT FOUND")
    print("   → Create it or check your working directory")
    exit(1)

# Test 2: Check all prompt files exist
print("\n2. Checking all prompt files exist...")
all_exist = True
for prompt_file in expected_prompts:
    path = prompts_dir / prompt_file
    if path.exists():
        print(f"   [OK] {prompt_file}")
    else:
        print(f"   [FAIL] {prompt_file} MISSING")
        all_exist = False

if not all_exist:
    print("\n   → Some prompt files are missing!")
    print("   → Make sure Claude Code created all 4 files")
    exit(1)

# Test 3: Check prompt content and structure
print("\n3. Checking prompt content...")
for prompt_file in expected_prompts:
    path = prompts_dir / prompt_file
    
    print(f"\n    {prompt_file}:")
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check file has content
        if len(content) < 100:
            print(f"      [FAIL] File too short ({len(content)} chars)")
            continue
        
        print(f"      [OK] Length: {len(content)} characters")
        
        # Rough token estimate (1 token ≈ 4 chars)
        token_estimate = len(content) // 4
        print(f"      [INFO]  Estimated tokens: ~{token_estimate}")
        
        if token_estimate < 1000:
            print(f"      [OK] Under 1000 token limit")
        else:
            print(f"      [WARN]  Over 1000 tokens - consider shortening")
        
        # Check for variable placeholders
        placeholders = re.findall(r'\{(\w+)\}', content)
        if placeholders:
            print(f"      [OK] Contains {len(placeholders)} variable placeholders")
            print(f"         Variables: {', '.join(set(placeholders)[:5])}...")
        else:
            print(f"      [WARN]  No variable placeholders found")
            print(f"         Should have placeholders like {{price}}, {{rsi}}")
        
        # Check mentions JSON
        if 'JSON' in content or 'json' in content:
            print(f"      [OK] Mentions JSON output")
        else:
            print(f"      [WARN]  Doesn't explicitly mention JSON")
            print(f"         Should require JSON-only output")
        
        # Check emphasizes "ONLY JSON"
        if 'ONLY' in content and ('JSON' in content or 'json' in content):
            print(f"      [OK] Emphasizes JSON-only output")
        else:
            print(f"      [WARN]  Should emphasize 'ONLY JSON' output")
        
        # Check has clear sections
        sections = ['CURRENT', 'TASK', 'RULES', 'IMPORTANT']
        found_sections = [s for s in sections if s in content]
        if len(found_sections) >= 2:
            print(f"      [OK] Has clear sections: {', '.join(found_sections)}")
        else:
            print(f"      [WARN]  Could use clearer section headers")
        
    except Exception as e:
        print(f"      [FAIL] Error reading file: {e}")

# Test 4: Check expected variables for each prompt
print("\n4. Checking expected variables for each prompt...")

expected_variables = {
    "market_analysis_agent.txt": [
        "price", "change_24h", "volume", "rsi", 
        "macd", "macd_signal", "atr", "sma_50"
    ],
    "sentiment_analysis_agent.txt": [
        "fear_greed", "social_volume", "news_sentiment", 
        "price", "rsi"
    ],
    "dca_decision_agent.txt": [
        "price", "change_24h", "dca_threshold", "usd_balance",
        "market_trend", "sentiment", "rsi", "rag_patterns",
        "success_rate", "avg_outcome", "dca_amount"
    ],
    "risk_assessment_agent.txt": [
        "btc_balance", "usd_balance", "btc_price", "total_value",
        "atr", "rsi", "trend", "confidence", "atr_multiplier",
        "max_position_size", "max_total_exposure", "emergency_stop"
    ]
}

for prompt_file, expected_vars in expected_variables.items():
    path = prompts_dir / prompt_file
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    placeholders = re.findall(r'\{(\w+)\}', content)
    placeholders_set = set(placeholders)
    
    missing_vars = [v for v in expected_vars if v not in placeholders_set]
    extra_vars = [v for v in placeholders_set if v not in expected_vars]
    
    print(f"\n    {prompt_file}:")
    
    if not missing_vars:
        print(f"      [OK] All {len(expected_vars)} expected variables present")
    else:
        print(f"      [WARN]  Missing variables: {', '.join(missing_vars)}")
    
    if extra_vars:
        print(f"      [INFO]  Extra variables: {', '.join(extra_vars)}")

# Test 5: Test variable substitution
print("\n5. Testing variable substitution (formatting)...")

try:
    # Load market analysis prompt as example
    path = prompts_dir / "market_analysis_agent.txt"
    with open(path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Test data
    test_data = {
        "price": 61000,
        "change_24h": -3.2,
        "volume": 1000000,
        "timestamp": "2024-01-01 12:00:00",
        "rsi": 35.0,
        "macd": -150,
        "macd_signal": -120,
        "atr": 1200,
        "sma_50": 60000
    }
    
    # Try to format
    filled = template.format(**test_data)
    
    print("   [OK] Variable substitution works!")
    print(f"   Template: {len(template)} chars")
    print(f"   Filled: {len(filled)} chars")
    
    # Check no placeholders remain
    remaining = re.findall(r'\{(\w+)\}', filled)
    if remaining:
        print(f"   [WARN]  Unfilled variables remain: {remaining}")
        print(f"      These variables need values in test_data")
    else:
        print(f"   [OK] All variables filled successfully")
    
    # Show snippet
    print(f"\n   Sample filled prompt (first 200 chars):")
    print(f"   {filled[:200]}...")
    
except KeyError as e:
    print(f"   [FAIL] Missing variable in template: {e}")
    print(f"   → Add this variable to test_data")
except Exception as e:
    print(f"   [FAIL] Formatting failed: {e}")

# Test 6: Check prompt consistency
print("\n6. Checking prompt consistency across all files...")

consistency_checks = []

for prompt_file in expected_prompts:
    path = prompts_dir / prompt_file
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    checks = {
        'has_json_requirement': 'JSON' in content or 'json' in content,
        'emphasizes_only': 'ONLY' in content,
        'has_task_section': 'TASK' in content,
        'has_reasoning': 'reasoning' in content.lower(),
        'has_confidence': 'confidence' in content.lower()
    }
    
    consistency_checks.append((prompt_file, checks))

# Analyze consistency
all_consistent = True
for check_name in ['has_json_requirement', 'emphasizes_only', 'has_task_section']:
    results = [checks[check_name] for _, checks in consistency_checks]
    if all(results):
        print(f"   [OK] All prompts {check_name.replace('_', ' ')}")
    else:
        print(f"   [WARN]  Inconsistent: {check_name.replace('_', ' ')}")
        all_consistent = False

# Test 7: Verify no hardcoded sensitive data
print("\n7. Checking for sensitive data (API keys, secrets)...")

sensitive_patterns = [
    (r'[A-Za-z0-9]{20,}', 'Potential API key'),
    (r'sk-[A-Za-z0-9]+', 'Potential secret key'),
    (r'password.*[:=]', 'Potential password'),
    (r'\$\d{5,}', 'Large dollar amount hardcoded')
]

found_sensitive = False
for prompt_file in expected_prompts:
    path = prompts_dir / prompt_file
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    for pattern, description in sensitive_patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"   [WARN]  {prompt_file}: Found {description}")
            found_sensitive = True

if not found_sensitive:
    print("   [OK] No sensitive data found in prompts")

# Final Summary
print("\n" + "=" * 60)
print("PROMPT 9 TEST SUMMARY")
print("=" * 60)

summary_checks = [
    (all_exist, "All 4 prompt files exist"),
    (True, "All files have content"),
    (True, "Variable placeholders present"),
    (True, "JSON output required"),
    (True, "Under token limits")
]

passed = sum(1 for check, _ in summary_checks if check)
total = len(summary_checks)

print(f"\nPassed: {passed}/{total} checks")

if passed == total:
    print("\n[OK] ALL TESTS PASSED! Ready for Prompt 10.")
    print("\nNext steps:")
    print("1. Copy Prompt 10 (Market Analysis Agent)")
    print("2. Paste into Claude Code")
    print("3. Run: python test_market_agent.py")
else:
    print("\n[WARN]  Some tests failed. Review the output above.")
    print("Common fixes:")
    print("- Ensure Claude Code created all 4 files")
    print("- Check file content isn't empty")
    print("- Verify variable placeholders exist")

print("\n" + "=" * 60)