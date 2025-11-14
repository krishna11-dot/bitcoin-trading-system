"""
Script to remove emojis and add clarity to the trading system.

This script:
1. Removes ALL emojis from Python files
2. Adds clear explanations for non-technical users
3. Replaces emojis with clear text prefixes
"""

import os
import re
from pathlib import Path

# Emoji to text mapping for clarity
EMOJI_REPLACEMENTS = {
    # Status indicators
    "[OK]": "[OK]",
    "[FAIL]": "[FAIL]",
    "[WARN]": "[WARN]",
    "[INFO]": "[INFO]",
    "[OK]": "[OK]",

    # Process indicators
    "[STARTING]": "[STARTING]",
    "[PROCESSING]": "[PROCESSING]",
    "[WAITING]": "[WAITING]",
    "[SLEEPING]": "[SLEEPING]",
    "[SCHEDULED]": "[SCHEDULED]",

    # Data/Analysis
    "[DATA]": "[DATA]",
    "[ANALYSIS]": "[ANALYSIS]",
    "[ANALYZING]": "[ANALYZING]",
    "[CONFIGURING]": "[CONFIGURING]",

    # Financial
    "[FINANCIAL]": "[FINANCIAL]",
    "[DECISION]": "[DECISION]",
    "[USD]": "[USD]",

    # Sentiment
    "[SENTIMENT]": "[SENTIMENT]",
    "[SYSTEM]": "[SYSTEM]",

    # Network
    "[BLOCKCHAIN]": "[BLOCKCHAIN]",
    "[SAFETY]": "[SAFETY]",

    # Misc
    "[ALERT]": "[ALERT]",
    "[NOTE]": "[NOTE]",
}

def remove_emojis_from_file(file_path):
    """Remove emojis from a single file and replace with clear text."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Replace each emoji with clear text
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            content = content.replace(emoji, replacement)

        # Remove any remaining emojis (catch-all)
        # This regex matches most emoji ranges
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        content = emoji_pattern.sub('', content)

        # Only write if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_directory(directory):
    """Process all Python files in directory."""
    py_files = list(Path(directory).rglob("*.py"))

    print(f"Found {len(py_files)} Python files")
    modified = 0

    for py_file in py_files:
        # Skip __pycache__ and .venv
        if '__pycache__' in str(py_file) or '.venv' in str(py_file):
            continue

        if remove_emojis_from_file(py_file):
            print(f"  Modified: {py_file.name}")
            modified += 1

    print(f"\nModified {modified} files")
    return modified

if __name__ == "__main__":
    print("="*60)
    print("REMOVING EMOJIS AND ADDING CLARITY")
    print("="*60)
    print()

    # Process main directories
    directories = [
        ".",  # Root
        "agents",
        "graph",
        "tools",
        "guardrails",
        "monitoring"
    ]

    total_modified = 0
    for directory in directories:
        if os.path.exists(directory):
            print(f"\nProcessing {directory}/...")
            total_modified += process_directory(directory)

    print()
    print("="*60)
    print(f"COMPLETE: Modified {total_modified} files total")
    print("="*60)
