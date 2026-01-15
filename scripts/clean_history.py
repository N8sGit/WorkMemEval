#!/usr/bin/env python3
"""
Clean and deduplicate history file content.

Issues to fix:
1. Plans repeated in both assistant messages and tool results
2. Consecutive near-duplicate entries
3. Overly verbose tool output entries
"""

import json
import re
import sys
from pathlib import Path


def content_signature(content: str, length: int = 200) -> str:
    """Create a signature for deduplication."""
    # Normalize whitespace and take first N chars
    normalized = ' '.join(content.split())[:length]
    return normalized


def is_similar(a: str, b: str, threshold: float = 0.8) -> bool:
    """Check if two strings are similar enough to be duplicates."""
    sig_a = content_signature(a, 300)
    sig_b = content_signature(b, 300)
    
    if sig_a == sig_b:
        return True
    
    # Check if one is a substring of the other
    if len(sig_a) > 100 and len(sig_b) > 100:
        if sig_a in sig_b or sig_b in sig_a:
            return True
    
    return False


def clean_content(content: str) -> str:
    """Clean individual content entry."""
    # Remove redundant [Plan] blocks if content already contains plan info
    if content.count('# ShopMind') > 1:
        # Keep only the first occurrence of the full plan
        parts = content.split('# ShopMind')
        if len(parts) > 2:
            content = parts[0] + '# ShopMind' + parts[1]
    
    # Clean up tool result prefixes for readability
    content = re.sub(r'\[Tool result\]\s*\n\s*User has approved', '[User approved', content)
    content = re.sub(r'\[Tool result\]\s*\n\s*File created', '[Created file', content)
    content = re.sub(r'\[Tool result\]\s*\n\s*Todos have been', '[TODOs', content)
    
    # Remove empty tool results
    if content.strip() in ['[Tool result]', '[Tool result]\n']:
        return ''
    
    return content.strip()


def should_skip_entry(entry: dict, prev_entries: list) -> bool:
    """Determine if entry should be skipped as duplicate."""
    content = entry.get('content', '')
    
    # Skip very short entries
    if len(content.strip()) < 20:
        return True
    
    # Skip entries that are just tool confirmations
    skip_patterns = [
        r'^\[Tool: \w+\]$',
        r'^\[Reading: .+\]$',
        r'^File created successfully',
        r'^Todos have been modified successfully',
    ]
    for pattern in skip_patterns:
        if re.match(pattern, content.strip()):
            return True
    
    # Check for similarity with recent entries
    for prev in prev_entries[-5:]:
        prev_content = prev.get('content', '')
        if is_similar(content, prev_content):
            # Keep the longer one
            if len(content) <= len(prev_content):
                return True
    
    return False


def merge_consecutive_assistant(entries: list) -> list:
    """Merge consecutive assistant entries that are part of same response."""
    merged = []
    i = 0
    
    while i < len(entries):
        entry = entries[i]
        
        if entry.get('role') == 'assistant':
            # Look ahead for consecutive assistant entries
            combined_content = [entry.get('content', '')]
            j = i + 1
            
            while j < len(entries) and entries[j].get('role') == 'assistant':
                next_content = entries[j].get('content', '')
                # Only merge if they seem related (e.g., thinking + action)
                if len(next_content) < 500 or '[Thinking]' in combined_content[-1]:
                    combined_content.append(next_content)
                    j += 1
                else:
                    break
            
            if len(combined_content) > 1:
                # Merge into single entry
                merged.append({
                    'role': 'assistant',
                    'content': '\n\n'.join(combined_content)
                })
                i = j
            else:
                merged.append(entry)
                i += 1
        else:
            merged.append(entry)
            i += 1
    
    return merged


def clean_history(history: list) -> list:
    """Clean and deduplicate history entries."""
    cleaned = []
    
    # First pass: clean individual entries and skip duplicates
    for entry in history:
        content = clean_content(entry.get('content', ''))
        if not content:
            continue
        
        new_entry = {'role': entry.get('role', 'user'), 'content': content}
        
        if not should_skip_entry(new_entry, cleaned):
            cleaned.append(new_entry)
    
    # Second pass: merge consecutive assistant entries
    cleaned = merge_consecutive_assistant(cleaned)
    
    # Third pass: remove tool-results that duplicate assistant content
    final = []
    seen_content = set()
    
    for entry in cleaned:
        content = entry.get('content', '')
        sig = content_signature(content, 500)
        
        if sig not in seen_content:
            seen_content.add(sig)
            final.append(entry)
    
    return final


def main():
    if len(sys.argv) < 2:
        input_path = Path('contexts/shopmind_real_history.json')
    else:
        input_path = Path(sys.argv[1])
    
    output_path = input_path  # Overwrite by default
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    
    print(f"Loading {input_path}...")
    with open(input_path) as f:
        history = json.load(f)
    
    print(f"Original entries: {len(history)}")
    original_chars = sum(len(e.get('content', '')) for e in history)
    print(f"Original chars: {original_chars:,}")
    
    print("\nCleaning...")
    cleaned = clean_history(history)
    
    print(f"Cleaned entries: {len(cleaned)}")
    cleaned_chars = sum(len(e.get('content', '')) for e in cleaned)
    print(f"Cleaned chars: {cleaned_chars:,}")
    print(f"Reduction: {(1 - cleaned_chars/original_chars)*100:.1f}%")
    
    print(f"\nWriting to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(cleaned, f, indent=2, ensure_ascii=False)
    
    print("Done!")


if __name__ == '__main__':
    main()
