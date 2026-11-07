"""Tests for HackBot memory and session persistence."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from hackbot.memory import (
    ConversationSummarizer,
    MemoryManager,
    SessionMeta,
    CONTINUE_PROMPT,
)


@pytest.fixture
def tmp_sessions(tmp_path):
    """Provide a temp sessions directory."""
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir()
    return sessions_dir


@pytest.fixture
def memory(tmp_sessions):
    """Provide a MemoryManager with temp directory."""
    return MemoryManager(sessions_dir=tmp_sessions)


class TestMemoryManager:
    def test_new_session_id(self, memory):
        sid = memory.new_session_id("chat")
        assert sid.startswith("chat_")
        assert memory.current_session_id == sid

    def test_save_and_load_session(self, memory):
        sid = memory.new_session_id("chat")
        messages = [
            {"role": "user", "content": "Hello", "timestamp": time.time()},
            {"role": "assistant", "content": "Hi there!", "timestamp": time.time()},
        ]
        path = memory.save_session(
            session_id=sid,
            mode="chat",
            messages=messages,
            name="Test Session",
        )
        assert path.exists()

        data = memory.load_session(sid)
        assert data is not None
        assert data["name"] == "Test Session"
        assert data["mode"] == "chat"
        assert len(data["messages"]) == 2
        assert data["messages"][0]["content"] == "Hello"

    def test_save_filters_system_messages(self, memory):
        sid = memory.new_session_id("chat")
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]
        memory.save_session(session_id=sid, mode="chat", messages=messages)
        data = memory.load_session(sid)
        assert len(data["messages"]) == 2  # system filtered out

    def test_list_sessions(self, memory):
        # Create multiple sessions
        for i in range(3):
            sid = f"chat_{i}"
            messages = [{"role": "user", "content": f"Msg {i}"}]
            memory.save_session(session_id=sid, mode="chat", messages=messages, name=f"Session {i}")

        sessions = memory.list_sessions()
        assert len(sessions) == 3
        # Most recent first
        assert all(isinstance(s, SessionMeta) for s in sessions)

    def test_list_sessions_mode_filter(self, memory):
        memory.save_session("chat_1", "chat", [{"role": "user", "content": "Hi"}])
        memory.save_session("agent_1", "agent", [{"role": "user", "content": "Scan"}])

        chat_sessions = memory.list_sessions(mode="chat")
        assert len(chat_sessions) == 1
        assert chat_sessions[0].mode == "chat"

        agent_sessions = memory.list_sessions(mode="agent")
        assert len(agent_sessions) == 1

    def test_delete_session(self, memory):
        sid = "chat_delete_me"
        memory.save_session(sid, "chat", [{"role": "user", "content": "Hi"}])
        assert memory.delete_session(sid) is True
        assert memory.load_session(sid) is None

    def test_delete_nonexistent(self, memory):
        assert memory.delete_session("nonexistent") is False

    def test_search_sessions(self, memory):
        memory.save_session("chat_1", "chat", [{"role": "user", "content": "Hi"}], name="Nmap scan session")
        memory.save_session("chat_2", "chat", [{"role": "user", "content": "Hi"}], name="SQL injection testing")

        results = memory.search_sessions("nmap")
        assert len(results) == 1
        assert "Nmap" in results[0].name

    def test_auto_save_chat(self, memory):
        sid = memory.new_session_id("chat")
        messages = [{"role": "user", "content": "Test auto save"}]
        path = memory.auto_save_chat(sid, messages)
        assert path.exists()

    def test_auto_save_agent(self, memory):
        sid = memory.new_session_id("agent")
        messages = [{"role": "user", "content": "Scanning target"}]
        findings = [{"title": "Open port 80", "severity": "Info"}]
        path = memory.auto_save_agent(sid, messages, target="192.168.1.1", findings=findings)
        assert path.exists()

        data = memory.load_session(sid)
        assert data["target"] == "192.168.1.1"
        assert len(data["findings"]) == 1

    def test_session_meta_to_dict(self):
        meta = SessionMeta(
            id="test_1", mode="chat", name="Test",
            created=1000, updated=2000, message_count=5
        )
        d = meta.to_dict()
        assert d["id"] == "test_1"
        assert d["message_count"] == 5

    def test_load_partial_match(self, memory):
        memory.save_session("chat_12345", "chat", [{"role": "user", "content": "Hi"}])
        # Should find by partial match
        data = memory.load_session("12345")
        assert data is not None


class TestConversationSummarizer:
    def test_needs_summarization_false(self):
        summarizer = ConversationSummarizer(max_messages=5, keep_recent=3)
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(3)]
        assert summarizer.needs_summarization(messages) is False

    def test_needs_summarization_true(self):
        summarizer = ConversationSummarizer(max_messages=5, keep_recent=3)
        messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
        assert summarizer.needs_summarization(messages) is True

    def test_needs_summarization_ignores_system(self):
        summarizer = ConversationSummarizer(max_messages=5, keep_recent=3)
        messages = [{"role": "system", "content": "sys"}] + \
                   [{"role": "user", "content": f"msg {i}"} for i in range(4)]
        assert summarizer.needs_summarization(messages) is False

    def test_continue_prompt_exists(self):
        assert CONTINUE_PROMPT
        assert "continue" in CONTINUE_PROMPT.lower()

    def test_summarizer_without_engine(self):
        summarizer = ConversationSummarizer(engine=None)
        # Without an engine, summarize returns empty string
        result = summarizer.get_continue_prompt()
        assert "continue" in result.lower()
