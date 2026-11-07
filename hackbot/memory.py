"""
HackBot Memory & Session Persistence
=====================================
Manages chat session persistence, auto-save, session history browsing,
and conversation summarization for reduced hallucination.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from hackbot.config import SESSIONS_DIR


# ── Session Data ─────────────────────────────────────────────────────────────

@dataclass
class SessionMeta:
    """Metadata for a saved session."""
    id: str
    mode: str  # chat | agent | plan
    name: str
    created: float
    updated: float
    message_count: int
    target: str = ""  # agent mode target
    summary: str = ""  # brief description of the session
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode,
            "name": self.name,
            "created": self.created,
            "updated": self.updated,
            "message_count": self.message_count,
            "target": self.target,
            "summary": self.summary,
        }


# ── Memory Manager ───────────────────────────────────────────────────────────

class MemoryManager:
    """
    Manages session persistence and conversation memory.

    Features:
    - Auto-save sessions after each exchange
    - Load/resume previous sessions
    - List and search session history
    - Conversation summarization for long contexts
    """

    def __init__(self, sessions_dir: Optional[Path] = None):
        self.sessions_dir = sessions_dir or SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._current_session_id: Optional[str] = None

    # ── Session CRUD ─────────────────────────────────────────────────────

    def new_session_id(self, mode: str = "chat") -> str:
        """Generate a unique session ID."""
        ts = int(time.time() * 1000)
        self._current_session_id = f"{mode}_{ts}"
        return self._current_session_id

    @property
    def current_session_id(self) -> Optional[str]:
        return self._current_session_id

    @current_session_id.setter
    def current_session_id(self, value: Optional[str]) -> None:
        self._current_session_id = value

    def save_session(
        self,
        session_id: str,
        mode: str,
        messages: List[Dict[str, Any]],
        name: str = "",
        target: str = "",
        summary: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Save a session to disk."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        path = self.sessions_dir / f"{session_id}.json"

        # Filter out system messages for storage
        stored_msgs = [
            m for m in messages if m.get("role") != "system"
        ]

        now = time.time()
        data: Dict[str, Any] = {
            "id": session_id,
            "mode": mode,
            "name": name or session_id,
            "created": extra.get("created", now) if extra else now,
            "updated": now,
            "target": target,
            "summary": summary,
            "message_count": len(stored_msgs),
            "messages": stored_msgs,
        }

        if extra:
            for k, v in extra.items():
                if k not in data:
                    data[k] = v

        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        return path

    def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load a session from disk by ID."""
        path = self.sessions_dir / f"{session_id}.json"
        if not path.exists():
            # Try to find by partial match
            matches = list(self.sessions_dir.glob(f"*{session_id}*.json"))
            if matches:
                path = matches[0]
            else:
                return None

        try:
            with open(path) as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return None
            self._current_session_id = str(data.get("id", session_id))
            res: Dict[str, Any] = dict(data)
            return res
        except (json.JSONDecodeError, IOError):
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file."""
        path = self.sessions_dir / f"{session_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(
        self,
        mode: Optional[str] = None,
        limit: int = 50,
    ) -> List[SessionMeta]:
        """List saved sessions, newest first."""
        sessions: List[SessionMeta] = []

        if not self.sessions_dir.exists():
            return sessions

        for f in self.sessions_dir.glob("*.json"):
            try:
                with open(f) as fh:
                    data = json.load(fh)

                session_mode = data.get("mode", "chat")
                if mode and session_mode != mode:
                    continue

                sessions.append(SessionMeta(
                    id=data.get("id", f.stem),
                    mode=session_mode,
                    name=data.get("name", f.stem),
                    created=data.get("created", 0),
                    updated=data.get("updated", 0),
                    message_count=data.get("message_count", 0),
                    target=data.get("target", ""),
                    summary=data.get("summary", ""),
                    path=str(f),
                ))
            except (json.JSONDecodeError, IOError, KeyError):
                continue

        sessions.sort(key=lambda s: s.updated, reverse=True)
        return sessions[:limit]

    def search_sessions(self, query: str) -> List[SessionMeta]:
        """Search sessions by name, target, or summary content."""
        query_lower = query.lower()
        results = []
        for session in self.list_sessions(limit=200):
            if (
                query_lower in session.name.lower()
                or query_lower in session.target.lower()
                or query_lower in session.summary.lower()
            ):
                results.append(session)
        return results

    # ── Auto-Save Helpers ────────────────────────────────────────────────

    def auto_save_chat(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        name: str = "",
    ) -> Path:
        """Quick auto-save for chat mode after each exchange."""
        return self.save_session(
            session_id=session_id,
            mode="chat",
            messages=messages,
            name=name or f"Chat {time.strftime('%Y-%m-%d %H:%M')}",
        )

    def auto_save_agent(
        self,
        session_id: str,
        messages: List[Dict[str, Any]],
        target: str = "",
        findings: Optional[List[Dict[str, Any]]] = None,
        scripts: Optional[List[Dict[str, Any]]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
    ) -> Path:
        """Quick auto-save for agent mode with findings and execution logs."""
        path = self.save_session(
            session_id=session_id,
            mode="agent",
            messages=messages,
            name=f"Agent: {target}" if target else "",
            target=target,
            extra={"findings": findings or [], "scripts": scripts or []},
        )
        
        # Save Agent Execution Logs
        if steps is not None:
            try:
                from hackbot.config import REPORTS_DIR
                sess_report_dir = REPORTS_DIR / f"session_{session_id}"
                sess_report_dir.mkdir(parents=True, exist_ok=True)
                
                # JSON log
                json_path = sess_report_dir / "execution_log.json"
                with open(json_path, "w") as f:
                    json.dump(steps, f, indent=2, default=str)
                
                # TXT log
                txt_path = sess_report_dir / "execution_log.txt"
                with open(txt_path, "w") as f:
                    for step in steps:
                        f.write(f"[Step {step.get('step_num', 0)}]\n")
                        
                        ts = step.get('timestamp', 0)
                        if ts:
                            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))
                            f.write(f"Timestamp: {time_str}\n")
                        
                        if step.get("ai_analysis"):
                            f.write(f"Agent Thought: {step['ai_analysis'].strip()}\n")
                        
                        tool_res = step.get("tool_result")
                        if tool_res:
                            f.write(f"Tool: {tool_res.get('tool', 'unknown')}\n")
                            f.write(f"Command: {tool_res.get('command', '')}\n\n")
                            val_out = tool_res.get('stdout', '') or ''
                            f.write("[Output]\n")
                            f.write(f"{val_out.strip()}\n\n")
                            
                            val_err = tool_res.get('stderr', '') or ''
                            if val_err.strip():
                                f.write("[Errors]\n")
                                f.write(f"{val_err.strip()}\n\n")
                                
                            f.write(f"Execution Status: {'Success' if tool_res.get('success') else 'Failure'}\n")
                        else:
                            f.write(f"Action: {step.get('action', 'unknown')}\n")
                            f.write(f"Description: {step.get('description', '')}\n")
                        
                        f.write("-" * 40 + "\n\n")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("Failed to auto-save execution logs: %s", e)
                
        return path


# ── Conversation Summarizer ─────────────────────────────────────────────────

SUMMARIZE_SYSTEM = """You are a concise summarizer for a cybersecurity penetration testing AI assistant.
Summarize the conversation so far into a structured brief that preserves:
1. Key findings and vulnerabilities discovered
2. Tools executed and their important results
3. Current assessment state and what phase we're in
4. Any important targets, IPs, URLs, or credentials found
5. What was planned vs what was completed

Be thorough but concise. Use bullet points. This summary will replace the old messages
to keep context manageable. Preserve ALL technical details (IPs, ports, CVEs, paths, etc.)."""

CONTINUE_PROMPT = """Continue where you left off. Do not repeat what was already said.
Pick up exactly from the last point and continue with the next steps or complete the
response that was cut off."""


class ConversationSummarizer:
    """
    Summarizes long conversations to reduce context window usage.

    When a conversation exceeds a threshold, older messages are summarized
    into a compact brief. The system prompt + summary + recent messages
    are kept, replacing the full history.
    """

    def __init__(
        self,
        engine: Any = None,
        max_messages: int = 30,
        keep_recent: int = 8,
    ):
        """
        Args:
            engine: AIEngine instance for generating summaries
            max_messages: Trigger summarization when message count exceeds this
            keep_recent: Number of recent messages to keep after summarization
        """
        self.engine = engine
        self.max_messages = max_messages
        self.keep_recent = keep_recent
        self._summary_count = 0

    def needs_summarization(self, messages: list) -> bool:
        """Check if the conversation needs summarization."""
        non_system = [
            m for m in messages
            if (m.role if hasattr(m, 'role') else m.get('role', '')) != 'system'
        ]
        return len(non_system) > self.max_messages

    def summarize(self, conversation: Any) -> str:
        """
        Summarize and compact a conversation.

        Replaces old messages with a summary message, keeping:
        - System prompt(s)
        - Summary of older messages
        - Recent messages (keep_recent)

        Returns the summary text.
        """
        if not self.engine:
            return ""

        messages = conversation.messages
        non_system = [m for m in messages if m.role != "system"]
        system_msgs = [m for m in messages if m.role == "system"]

        if len(non_system) <= self.keep_recent:
            return ""  # Nothing to summarize

        # Split: old messages to summarize, recent to keep
        old_messages = non_system[:-self.keep_recent]
        recent_messages = non_system[-self.keep_recent:]

        # Build the text to summarize
        summary_text_parts = []
        for msg in old_messages:
            role_label = "User" if msg.role == "user" else "Assistant"
            # Truncate very long messages to avoid blowing up the summary request
            content = msg.content[:2000] if len(msg.content) > 2000 else msg.content
            summary_text_parts.append(f"[{role_label}]: {content}")

        text_to_summarize = "\n\n".join(summary_text_parts)

        # Generate summary via AI
        try:
            summary = self.engine.quick_ask(
                prompt=f"Summarize this cybersecurity assessment conversation:\n\n{text_to_summarize}",
                system=SUMMARIZE_SYSTEM,
            )
        except Exception:
            # Fallback: just truncate
            summary = f"[Previous conversation with {len(old_messages)} messages summarized]"

        self._summary_count += 1

        # Rebuild conversation: system + summary + recent
        conversation.messages = list(system_msgs)

        # Add summary as a system-level context message
        from hackbot.core.engine import Message
        summary_msg = Message(
            role="user",
            content=f"[CONVERSATION SUMMARY — Part {self._summary_count}]\n\n{summary}\n\n[End of summary. The conversation continues below with the most recent messages.]",
        )
        conversation.messages.append(summary_msg)

        # Add a brief assistant acknowledgment
        ack_msg = Message(
            role="assistant",
            content="Understood. I have the context from the summary above. Continuing with the assessment.",
        )
        conversation.messages.append(ack_msg)

        # Re-add recent messages
        conversation.messages.extend(recent_messages)

        return str(summary)

    def get_continue_prompt(self) -> str:
        """Get the prompt to send when user wants to continue a stopped response."""
        return CONTINUE_PROMPT
