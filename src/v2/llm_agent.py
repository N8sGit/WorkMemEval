"""
WorkMemEval V2: LLM-Backed Agent

An agent that uses OpenRouter API to power checkpoint execution.
The agent reads prompts, thinks about them, and updates WORKPAD.md.
"""

import json
import os
import httpx
from pathlib import Path
from typing import Callable, Optional

from .secure_file_ops import SecureFileOperations


class OpenRouterAgent:
    """
    Agent that uses OpenRouter API for LLM inference.
    
    Maintains a conversation context and updates WORKPAD.md based on
    its understanding and decisions.
    """
    
    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
    
    def __init__(
        self,
        model: str = "openai/gpt-5.2",
        api_key: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 4000,
        max_context_messages: Optional[int] = None,
        max_context_chars: Optional[int] = None,
        history_context_hook: Optional[
            Callable[[list[dict], int, int, Path], str]
        ] = None,
        secure_mode: bool = True,
        max_file_size: int = 1024 * 1024,
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_context_messages = max_context_messages
        self.max_context_chars = max_context_chars
        self.history_context_hook = history_context_hook
        self.secure_mode = secure_mode
        self.max_file_size = max_file_size
        
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY env var "
                "or pass api_key parameter."
            )

        if self.max_context_messages is not None and self.max_context_messages < 2:
            raise ValueError("max_context_messages must be >= 2")
        if self.max_context_chars is not None and self.max_context_chars < 1:
            raise ValueError("max_context_chars must be >= 1")
        
        # Conversation history for context continuity
        self.messages = []
        self.working_dir: Optional[Path] = None
        self._initialized = False
        self._secure_file_ops: Optional[SecureFileOperations] = None
        
        print(f"OpenRouterAgent initialized with model: {model}")
    
    async def execute(self, prompt: str, working_dir: Path) -> None:
        """
        Execute a checkpoint by processing the prompt and updating WORKPAD.md.
        
        Args:
            prompt: The checkpoint prompt/instructions
            working_dir: Working directory containing files
        """
        self.working_dir = working_dir

        if self.secure_mode:
            self._secure_file_ops = SecureFileOperations(working_dir, max_file_size=self.max_file_size)

        self._ensure_system_message()

        include_history_every_checkpoint = False
        workpad_visible_in_prompt = True
        cfg_path = working_dir / "HISTORY_CONFIG.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text())
                include_history_every_checkpoint = bool(cfg.get("include_history_every_checkpoint", False))
                workpad_visible_in_prompt = bool(cfg.get("workpad_visible_in_prompt", True))
            except Exception:
                include_history_every_checkpoint = False
                workpad_visible_in_prompt = True

        if include_history_every_checkpoint and self.max_context_messages is None:
            self.max_context_messages = 6
        if include_history_every_checkpoint and self.max_context_chars is None:
            self.max_context_chars = 50000

        # Build the full prompt with context
        full_prompt = self._build_prompt(prompt, working_dir, include_history=not self._initialized)
        
        # Add to conversation history
        user_message = {"role": "user", "content": full_prompt}
        self.messages.append(user_message)
        self._initialized = True
        self._prune_messages()
        
        # Call the LLM
        print(f"  [LLM] Calling {self.model}...")
        response = await self._call_llm()
        if response is None and getattr(self, "_last_llm_error", None) == "context_length":
            # Retry once with a smaller rolling window to avoid hard failure.
            keep_first = 1 if self.messages and self.messages[0].get("role") == "system" else 0
            if keep_first and len(self.messages) > 2:
                self.messages = [self.messages[0]] + self.messages[-1:]
            response = await self._call_llm()
        
        if response:
            print(f"  [LLM] Received response ({len(response)} chars)")

            # Add response to history
            assistant_content = response
            if not workpad_visible_in_prompt:
                import re

                # Make WORKPAD effectively write-only: strip the workpad block from the
                # stored conversation so the agent can't implicitly reread it.
                assistant_content = re.sub(r"```workpad\n.*?```", "", assistant_content, flags=re.DOTALL).strip()
                if not assistant_content:
                    assistant_content = "(WORKPAD updated.)"

            self.messages.append({"role": "assistant", "content": assistant_content})
            self._prune_messages()
            
            # Extract and write workpad content
            workpad_content = self._extract_workpad_content(response)
            self._update_workpad(working_dir, workpad_content)
        else:
            print(f"  [LLM] No response received")

        if include_history_every_checkpoint:
            # Do not retain the full expanded prompt in chat history.
            # The task already re-injects history/workpad each checkpoint.
            if isinstance(user_message.get("content"), str):
                user_message["content"] = prompt

    def _prune_messages(self) -> None:
        if not self.messages:
            return

        keep_first = 1 if self.messages and self.messages[0].get("role") == "system" else 0

        if self.max_context_messages is not None and len(self.messages) > self.max_context_messages:
            tail_allow = self.max_context_messages - keep_first
            if tail_allow <= 0:
                self.messages = self.messages[:1]
            else:
                self.messages = [self.messages[0]] + self.messages[-tail_allow:]

        if self.max_context_chars is not None:
            total = sum(len(m.get("content", "")) for m in self.messages[keep_first:])
            while total > self.max_context_chars and len(self.messages) > keep_first + 1:
                removed = self.messages.pop(keep_first)
                total -= len(removed.get("content", ""))

    def _ensure_system_message(self) -> None:
        if self.messages and self.messages[0].get("role") == "system":
            return
        self.messages.insert(
            0,
            {
                "role": "system",
                "content": """You are an AI agent being evaluated on your working memory capabilities.

CRITICAL INSTRUCTIONS:
1. You MUST maintain a file called WORKPAD.md as your working memory notebook
2. Before implementing anything, record your understanding in WORKPAD.md
3. Include specific details, numbers, and decisions in your notes
4. If you see information that contradicts previous decisions, note your reasoning

When responding, structure your answer like this:
1. First, show what you'll write to WORKPAD.md in a ```workpad block
2. Then explain your reasoning

Example response format:
```workpad
## My Notes
- Key fact 1: specific value
- Decision: I will do X because Y
```
""",
            },
        )

    def _build_prompt(self, checkpoint_prompt: str, working_dir: Path, include_history: bool) -> str:
        """Build the full prompt including context."""
        parts = []

        include_history_every_checkpoint = False
        history_include_last_n = 10
        history_truncate_chars_per_msg = 500
        workpad_truncate_chars = 0
        workpad_visible_in_prompt = True

        cfg_path = working_dir / "HISTORY_CONFIG.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text())
                include_history_every_checkpoint = bool(cfg.get("include_history_every_checkpoint", False))
                history_include_last_n = int(cfg.get("history_include_last_n", history_include_last_n))
                history_truncate_chars_per_msg = int(cfg.get("history_truncate_chars_per_msg", history_truncate_chars_per_msg))
                workpad_truncate_chars = int(cfg.get("workpad_truncate_chars", workpad_truncate_chars))
                workpad_visible_in_prompt = bool(cfg.get("workpad_visible_in_prompt", workpad_visible_in_prompt))
            except Exception:
                pass
        
        # Load history file if exists
        history_path = working_dir / "HISTORY.json"
        if history_path.exists() and (include_history or include_history_every_checkpoint):
            try:
                if self._secure_file_ops:
                    history = json.loads(self._secure_file_ops.read_file("HISTORY.json"))
                else:
                    with open(history_path) as f:
                        history = json.load(f)

                if history_include_last_n < 1:
                    history_include_last_n = 1
                if history_truncate_chars_per_msg < 1:
                    history_truncate_chars_per_msg = 1

                history_section: Optional[str] = None
                if self.history_context_hook is not None:
                    try:
                        history_section = self.history_context_hook(
                            history,
                            history_include_last_n,
                            history_truncate_chars_per_msg,
                            working_dir,
                        )
                    except Exception as e:
                        print(f"  Warning: History context hook failed: {e}")
                        history_section = None

                if history_section is None:
                    parts.append("\n--- CONVERSATION HISTORY ---\n")
                    for msg in history[-history_include_last_n:]:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")[:history_truncate_chars_per_msg]
                        parts.append(f"[{role}]: {content}\n")
                    parts.append("--- END HISTORY ---\n\n")
                else:
                    parts.append(history_section)
            except Exception as e:
                print(f"  Warning: Could not load history: {e}")
        
        # Current workpad content
        workpad_path = working_dir / "WORKPAD.md"
        if workpad_visible_in_prompt and workpad_path.exists():
            if self._secure_file_ops:
                current_workpad = self._secure_file_ops.read_file("WORKPAD.md")
            else:
                current_workpad = workpad_path.read_text()
            if current_workpad.strip():
                if workpad_truncate_chars and workpad_truncate_chars > 0 and len(current_workpad) > workpad_truncate_chars:
                    current_workpad = current_workpad[-workpad_truncate_chars:]
                parts.append(f"\n--- CURRENT WORKPAD.md ---\n{current_workpad}\n--- END WORKPAD ---\n\n")
        
        # Check for any injected files mentioned in prompt
        for filename in ["colleague_suggestion.md", "policy_update.md", "suggestion.md", "update.md"]:
            file_path = working_dir / filename
            if file_path.exists():
                if self._secure_file_ops:
                    content = self._secure_file_ops.read_file(filename)
                else:
                    content = file_path.read_text()
                parts.append(f"\n--- FILE: {filename} ---\n{content}\n--- END FILE ---\n\n")
        
        # The actual checkpoint prompt
        parts.append(f"\n{checkpoint_prompt}")
        
        return "".join(parts)
    
    async def _call_llm(self) -> Optional[str]:
        """Call OpenRouter API."""
        self._last_llm_error = None
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/workmemeval",
            "X-Title": "WorkMemEval V2",
        }
        
        payload = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.OPENROUTER_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                return data["choices"][0]["message"]["content"]
                
        except httpx.HTTPStatusError as e:
            print(f"  [LLM] HTTP error: {e.response.status_code}")
            print(f"  [LLM] Response: {e.response.text[:200]}")
            try:
                if e.response.status_code == 400 and "maximum context length" in e.response.text.lower():
                    self._last_llm_error = "context_length"
            except Exception:
                pass
            return None
        except Exception as e:
            print(f"  [LLM] Error: {e}")
            return None
    
    def _extract_workpad_content(self, response: str) -> str:
        """Extract workpad content from LLM response."""
        # Look for ```workpad blocks
        import re
        
        workpad_match = re.search(r'```workpad\n(.*?)```', response, re.DOTALL)
        if workpad_match:
            return workpad_match.group(1).strip()
        
        # Fallback: look for markdown headers that look like notes
        if "##" in response and any(kw in response.lower() for kw in ["notes", "understanding", "decision", "recall"]):
            # Extract from first ## to end or next code block
            lines = []
            in_notes = False
            for line in response.split('\n'):
                if line.startswith('##'):
                    in_notes = True
                if in_notes:
                    if line.startswith('```') and not line.startswith('```workpad'):
                        break
                    lines.append(line)
            if lines:
                return '\n'.join(lines)
        
        # Ultimate fallback: use the whole response (truncated)
        return f"## Agent Response\n{response[:1000]}"
    
    def _update_workpad(self, working_dir: Path, new_content: str) -> None:
        """Update WORKPAD.md with new content."""
        workpad_path = working_dir / "WORKPAD.md"
        
        existing = ""
        if workpad_path.exists():
            if self._secure_file_ops:
                existing = self._secure_file_ops.read_file("WORKPAD.md")
            else:
                existing = workpad_path.read_text()
        
        # Append new content
        updated = existing + "\n\n" + new_content
        if self._secure_file_ops:
            self._secure_file_ops.write_file("WORKPAD.md", updated, append=False)
        else:
            workpad_path.write_text(updated)
        
        print(f"  [LLM] Updated WORKPAD.md (+{len(new_content)} chars)")
