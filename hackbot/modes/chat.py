"""
HackBot Chat Mode
=================
Interactive cybersecurity Q&A with streaming responses, conversation history,
session management, auto-save memory, RAG vector recall, and rich terminal
formatting.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hackbot.config import HackBotConfig, SESSIONS_DIR
from hackbot.core.engine import AIEngine, create_conversation
from hackbot.core.rag_memory import get_rag_memory, RAGMemory
from hackbot.memory import ConversationSummarizer, MemoryManager, CONTINUE_PROMPT

logger = logging.getLogger(__name__)


class ChatMode:
    """Interactive chat mode for cybersecurity Q&A with persistent memory."""

    def __init__(self, engine: AIEngine, config: HackBotConfig):
        self.engine = engine
        self.config = config
        self.conversation = create_conversation("chat", language=config.ui.language)
        self.session_name: str = ""
        self._last_response: str = ""
        self._was_truncated: bool = False

        # Memory & auto-save
        self.memory = MemoryManager()
        self.session_id = self.memory.new_session_id("chat")

        # Summarizer for long conversations
        self.summarizer = ConversationSummarizer(
            engine=engine,
            max_messages=40,
            keep_recent=10,
        )

        # RAG vector memory (graceful fallback if ChromaDB not installed)
        self.rag: RAGMemory = get_rag_memory()
        self._rag_enabled = config.rag.enabled and self.rag.is_available()
        if self._rag_enabled:
            logger.debug("RAG memory active for chat mode")

    def ask(
        self,
        question: str,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Ask a cybersecurity question."""
        # ── RAG: inject relevant past context ────────────────────────────
        if self._rag_enabled:
            try:
                rag_context = self.rag.get_context(
                    question,
                    max_results=self.config.rag.max_results,
                    max_chars=self.config.rag.max_context_tokens * 4,
                )
                if rag_context:
                    self.conversation.add("system", rag_context)
            except Exception as exc:
                logger.debug("RAG context retrieval failed: %s", exc)

        self.conversation.add("user", question)

        # Summarize if conversation is getting too long
        if self.summarizer.needs_summarization(self.conversation.messages):
            self.summarizer.summarize(self.conversation)

        response = self.engine.chat(
            self.conversation,
            stream=stream,
            on_token=on_token,
        )

        self.conversation.add("assistant", response)
        self._last_response = response

        # ── RAG: store exchange ──────────────────────────────────────────
        if self._rag_enabled:
            try:
                self.rag.store_conversation(
                    "user", question,
                    session_id=self.session_id, mode="chat",
                )
                self.rag.store_conversation(
                    "assistant", response,
                    session_id=self.session_id, mode="chat",
                )
            except Exception as exc:
                logger.debug("RAG store failed: %s", exc)

        # Detect if response was likely truncated (ends mid-sentence)
        self._was_truncated = self._detect_truncation(response)

        # Auto-save after each exchange
        self._auto_save()

        return response

    def continue_response(
        self,
        stream: bool = True,
        on_token: Optional[Callable[[str], None]] = None,
    ) -> str:
        """Continue a response that was cut off or stopped."""
        self.conversation.add("user", CONTINUE_PROMPT)

        response = self.engine.chat(
            self.conversation,
            stream=stream,
            on_token=on_token,
        )

        self.conversation.add("assistant", response)
        self._last_response = response
        self._was_truncated = self._detect_truncation(response)
        self._auto_save()
        return response

    @property
    def was_truncated(self) -> bool:
        """Check if the last response was likely truncated."""
        return self._was_truncated

    def _detect_truncation(self, text: str) -> bool:
        """Heuristically detect if a response was truncated."""
        if not text or len(text) < 50:
            return False
        stripped = text.rstrip()
        if not stripped:
            return False
        # Likely truncated if ends mid-word, mid-sentence, or mid-code-block
        last_char = stripped[-1]
        open_blocks = stripped.count("```") % 2 != 0
        ends_incomplete = last_char not in '.!?"\')]}>`\n*-' and not stripped.endswith("---")
        return open_blocks or ends_incomplete

    def reset(self) -> None:
        """Clear conversation history and start fresh session."""
        self.conversation = create_conversation("chat", language=self.config.ui.language)
        self.session_id = self.memory.new_session_id("chat")
        self._last_response = ""
        self._was_truncated = False

    def _auto_save(self) -> None:
        """Auto-save current session to disk."""
        try:
            messages = [
                {"role": m.role, "content": m.content, "timestamp": m.timestamp}
                for m in self.conversation.messages
                if m.role != "system"
            ]
            self.memory.auto_save_chat(
                session_id=self.session_id,
                messages=messages,
                name=self.session_name or f"Chat {time.strftime('%Y-%m-%d %H:%M')}",
            )
        except Exception:
            pass  # Don't let save failures break chat

    def save_session(self, name: str = "") -> Path:
        """Save current session to disk with a name."""
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.session_name = name or f"chat_{int(time.time())}"

        messages = [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in self.conversation.messages
            if m.role != "system"
        ]

        return self.memory.save_session(
            session_id=self.session_id,
            mode="chat",
            messages=messages,
            name=self.session_name,
        )

    def load_session(self, path_or_id) -> bool:
        """Load a session from disk by path or ID."""
        if isinstance(path_or_id, Path):
            session_id = path_or_id.stem
        else:
            session_id = str(path_or_id)

        data = self.memory.load_session(session_id)
        if not data:
            # Legacy format fallback
            if isinstance(path_or_id, Path) and path_or_id.exists():
                with open(path_or_id) as f:
                    data = json.load(f)
            else:
                return False

        self.conversation = create_conversation("chat", language=self.config.ui.language)
        self.session_name = data.get("name", "")
        self.session_id = data.get("id", session_id)
        self.memory.current_session_id = self.session_id

        for msg in data.get("messages", []):
            self.conversation.add(msg["role"], msg["content"])

        return True

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List available saved sessions."""
        sessions = []
        for s in self.memory.list_sessions(mode="chat"):
            sessions.append({
                "path": Path(s.path) if s.path else SESSIONS_DIR / f"{s.id}.json",
                "id": s.id,
                "name": s.name,
                "timestamp": s.updated,
                "message_count": s.message_count,
            })
        return sessions

    def get_context_summary(self) -> str:
        """Get a summary of the current conversation context."""
        user_msgs = [m for m in self.conversation.messages if m.role == "user"]
        return f"Chat session with {len(user_msgs)} exchanges"

    def recall(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Explicit memory search — used by /recall command."""
        if not self._rag_enabled:
            return []
        results = self.rag.query(query, n_results=n_results)
        return [r.to_dict() for r in results]
