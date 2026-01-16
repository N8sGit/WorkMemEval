#!/usr/bin/env python3
"""
Parse Claude Code JSONL transcript and convert to WorkMemEval history format.

Usage:
    python scripts/parse_claude_code_transcript.py <input.jsonl> <output.json>
"""

import json
import sys
from pathlib import Path
from typing import Any


def parse_jsonl(filepath: Path) -> list[dict]:
    """Parse JSONL file into list of records."""
    records = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping malformed JSON at line {line_num}: {e}")
    return records


def extract_text_content(content: Any, full_content: bool = True) -> str:
    """Extract text from various content formats.
    
    Args:
        content: The content to extract from
        full_content: If True, include full file contents (for history). 
                      If False, truncate (for summaries).
    """
    if isinstance(content, str):
        return content
    
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get('type') == 'text':
                    text_parts.append(item.get('text', ''))
                elif item.get('type') == 'tool_use':
                    tool_name = item.get('name', 'unknown_tool')
                    tool_input = item.get('input', {})
                    
                    # For Write tool, capture the FULL file content
                    if tool_name == 'Write' and 'file_path' in tool_input:
                        file_path = tool_input['file_path']
                        file_content = tool_input.get('content', '')
                        if full_content:
                            text_parts.append(f"[Writing file: {file_path}]\n```\n{file_content}\n```")
                        else:
                            text_parts.append(f"[Writing file: {file_path}] ({len(file_content)} chars)")
                    
                    elif tool_name == 'Edit' and 'file_path' in tool_input:
                        file_path = tool_input['file_path']
                        old_str = tool_input.get('old_string', '')
                        new_str = tool_input.get('new_string', '')
                        if full_content:
                            text_parts.append(f"[Editing {file_path}]\nOld:\n```\n{old_str}\n```\nNew:\n```\n{new_str}\n```")
                        else:
                            text_parts.append(f"[Editing: {file_path}]")
                    
                    elif tool_name == 'Bash':
                        cmd = tool_input.get('command', '')
                        desc = tool_input.get('description', '')
                        text_parts.append(f"[Running: {cmd}]" + (f" # {desc}" if desc else ""))
                    
                    elif tool_name == 'Read':
                        file_path = tool_input.get('file_path', '')
                        text_parts.append(f"[Reading: {file_path}]")
                    
                    elif tool_name == 'TodoWrite':
                        todos = tool_input.get('todos', [])
                        todo_text = '\n'.join(f"- [{t.get('status', '?')}] {t.get('content', '')}" for t in todos)
                        text_parts.append(f"[TODO List]\n{todo_text}")
                    
                    elif tool_name == 'ExitPlanMode':
                        plan = tool_input.get('plan', '')
                        if plan and full_content:
                            text_parts.append(f"[Plan]\n{plan}")
                    
                    else:
                        # Generic tool capture
                        text_parts.append(f"[Tool: {tool_name}]")
                
                elif item.get('type') == 'tool_result':
                    # Tool results from user messages - these contain file reads, command outputs
                    result_content = item.get('content', '')
                    if result_content:
                        if full_content and len(result_content) < 10000:
                            text_parts.append(f"[Tool result]\n{result_content}")
                        elif len(result_content) < 500:
                            text_parts.append(f"[Tool result: {result_content[:300]}]")
                
                elif item.get('type') == 'thinking':
                    # Include thinking blocks - valuable reasoning context
                    thinking = item.get('thinking', '')
                    if thinking:
                        if full_content:
                            text_parts.append(f"[Thinking]\n{thinking}")
                        elif len(thinking) > 100:
                            text_parts.append(f"[Thinking: {thinking[:500]}...]")
            elif isinstance(item, str):
                text_parts.append(item)
        return '\n'.join(text_parts)
    
    return str(content) if content else ''


def extract_tool_use_result(record: dict) -> str:
    """Extract content from toolUseResult field on user records.
    
    This contains the actual file content for Write operations,
    command outputs for Bash, etc.
    """
    tr = record.get('toolUseResult', {})
    if not tr or not isinstance(tr, dict):
        return ''
    
    parts = []
    tr_type = tr.get('type', '')
    file_path = tr.get('filePath', '')
    
    # File creation/write results
    if tr_type == 'create' and file_path:
        content = tr.get('content', '')
        if content:
            parts.append(f"[Created file: {file_path}]\n```\n{content}\n```")
    
    # File edit results  
    elif tr_type == 'edit' and file_path:
        old_str = tr.get('oldString', '')
        new_str = tr.get('newString', '')
        original_file = tr.get('originalFile', '')
        
        if original_file:
            # Include the full original file for context
            parts.append(f"[Original file: {file_path}]\n```\n{original_file}\n```")
        
        if old_str or new_str:
            parts.append(f"[Edit applied to: {file_path}]")
            if old_str:
                parts.append(f"Replaced:\n```\n{old_str}\n```")
            if new_str:
                parts.append(f"With:\n```\n{new_str}\n```")
    
    # File read results (the 'file' field contains read content)
    file_content = tr.get('file', '')
    if file_content and not file_path:
        # This is a read result
        parts.append(f"[File content]\n```\n{file_content}\n```")
    
    # Command results
    stdout = tr.get('stdout', '')
    stderr = tr.get('stderr', '')
    if stdout:
        parts.append(f"[Output]\n{stdout}")
    if stderr:
        parts.append(f"[Stderr]\n{stderr}")
    
    # Plan results
    plan = tr.get('plan', '')
    if plan:
        parts.append(f"[Plan]\n{plan}")
    
    # Todo changes
    new_todos = tr.get('newTodos', [])
    if new_todos and isinstance(new_todos, list):
        todo_text = '\n'.join(f"- [{t.get('status', '?')}] {t.get('content', '')}" for t in new_todos if isinstance(t, dict))
        if todo_text:
            parts.append(f"[Updated TODOs]\n{todo_text}")
    
    return '\n'.join(parts)


def convert_to_history(records: list[dict], max_entries: int = None) -> list[dict]:
    """Convert Claude Code records to WorkMemEval history format.
    
    Args:
        records: Parsed JSONL records
        max_entries: If set, limit output to this many entries (sampling strategy).
                    If None, include all entries.
    """
    # First pass: deduplicate by UUID, keeping the longest (final) version
    # Claude Code streams responses - each chunk has same UUID but more content
    messages_by_uuid = {}
    
    for record in records:
        if record.get('type') not in ('user', 'assistant'):
            continue
        
        uuid = record.get('uuid')
        if not uuid:
            continue
            
        message = record.get('message', {})
        content = message.get('content')
        if not content:
            continue
        
        # Calculate content size
        content_size = len(json.dumps(content)) if content else 0
        
        # Keep the version with most content (final streamed version)
        if uuid not in messages_by_uuid or content_size > messages_by_uuid[uuid][1]:
            messages_by_uuid[uuid] = (record, content_size)
    
    # Sort by timestamp to maintain order
    sorted_records = sorted(
        [r for r, _ in messages_by_uuid.values()],
        key=lambda r: r.get('timestamp', '')
    )
    
    print(f"  Deduplicated to {len(sorted_records)} unique messages")
    
    history = []
    total_chars = 0
    filter_stats = {'short': 0, 'tool_result': 0}
    
    for record in sorted_records:
        message = record.get('message', {})
        role = message.get('role')
        content = message.get('content')
        
        if not role or not content:
            continue
        
        # Extract text content with full file contents
        text = extract_text_content(content, full_content=True)
        
        # For user records, also extract toolUseResult content (file writes, command outputs)
        if role == 'user':
            tool_result_text = extract_tool_use_result(record)
            if tool_result_text:
                text = (text + '\n' + tool_result_text) if text else tool_result_text
        
        if not text or len(text.strip()) < 10:
            filter_stats['short'] += 1
            continue
        
        # Skip pure tool results that are just confirmations
        if role == 'user' and text.strip() in ('[Tool result]', '[Tool result: ]'):
            filter_stats['tool_result'] += 1
            continue
        
        # Map role
        if role == 'user':
            history_role = 'user'
        elif role == 'assistant':
            history_role = 'assistant'
        else:
            history_role = 'system'
        
        total_chars += len(text)
        history.append({
            'role': history_role,
            'content': text
        })
    
    print(f"  Filtered: {filter_stats}")
    print(f"  Total content: {total_chars:,} chars (~{total_chars//4:,} tokens)")
    
    # Optional: Limit to max entries, keeping most important (first and last)
    if max_entries and len(history) > max_entries:
        # Keep first 30%, last 30%, sample middle
        first_n = int(max_entries * 0.3)
        last_n = int(max_entries * 0.3)
        middle_n = max_entries - first_n - last_n
        
        middle_start = first_n
        middle_end = len(history) - last_n
        middle_step = max(1, (middle_end - middle_start) // middle_n)
        
        sampled = (
            history[:first_n] +
            history[middle_start:middle_end:middle_step][:middle_n] +
            history[-last_n:]
        )
        
        # Add compaction marker
        sampled.insert(first_n, {
            'role': 'system',
            'content': f'[Session compacted. {len(history) - max_entries} messages summarized.]'
        })
        
        history = sampled
    
    return history


def add_context_summary(history: list[dict]) -> list[dict]:
    """Add a system message summarizing key context at the start."""
    # Analyze history to extract key decisions
    key_info = []
    
    for entry in history:
        content = entry.get('content', '').lower()
        
        # Look for architectural decisions
        if 'fastapi' in content and 'why' in content:
            key_info.append("Framework: FastAPI (async support, OpenAPI docs)")
        if 'postgresql' in content or 'sqlalchemy' in content:
            key_info.append("Database: PostgreSQL with SQLAlchemy ORM")
        if 'jsonb' in content and 'variant' in content:
            key_info.append("Product variants stored as JSONB for flexibility")
        if 'event' in content and 'bus' in content:
            key_info.append("Event-driven architecture with in-memory event bus")
        if 'modular monolith' in content:
            key_info.append("Architecture: Modular monolith (services can be extracted later)")
    
    # Deduplicate
    key_info = list(dict.fromkeys(key_info))
    
    if key_info:
        summary = {
            'role': 'system',
            'content': (
                "This is a continuation of a ShopMind e-commerce development session. "
                "Key architectural decisions made:\n" +
                "\n".join(f"- {info}" for info in key_info[:10])
            )
        }
        return [summary] + history
    
    return history


def main():
    if len(sys.argv) < 3:
        print("Usage: python parse_claude_code_transcript.py <input.jsonl> <output.json>")
        print("\nOptions:")
        print("  --max-entries N    Maximum history entries (default: 100)")
        sys.exit(1)
    
    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    max_entries = None  # No limit by default - capture full context
    if '--max-entries' in sys.argv:
        idx = sys.argv.index('--max-entries')
        max_entries = int(sys.argv[idx + 1])
    
    print(f"Parsing {input_path}...")
    records = parse_jsonl(input_path)
    print(f"Found {len(records)} records")
    
    print("Converting to history format...")
    history = convert_to_history(records, max_entries=max_entries)
    print(f"Extracted {len(history)} history entries")
    
    print("Adding context summary...")
    history = add_context_summary(history)
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Writing to {output_path}...")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)
    
    print(f"Done! Created history with {len(history)} entries")
    
    # Print sample
    print("\n--- First 3 entries ---")
    for entry in history[:3]:
        role = entry['role']
        content = entry['content'][:150].replace('\n', ' ')
        print(f"[{role}] {content}...")


if __name__ == '__main__':
    main()
