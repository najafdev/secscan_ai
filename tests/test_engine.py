"""Tests for HackBot AI Engine."""

import pytest
from unittest.mock import patch, MagicMock

from hackbot.core.engine import (
    AIEngine,
    Conversation,
    Message,
    create_conversation,
    SYSTEM_PROMPT_CHAT,
    SYSTEM_PROMPT_AGENT,
    SYSTEM_PROMPT_PLAN,
)
from hackbot.config import AIConfig


def test_message_creation():
    """Test Message dataclass."""
    msg = Message(role="user", content="test question")
    assert msg.role == "user"
    assert msg.content == "test question"
    assert msg.timestamp > 0

    api = msg.to_api()
    assert api["role"] == "user"
    assert api["content"] == "test question"


def test_conversation_creation():
    """Test Conversation basics."""
    conv = Conversation()
    conv.add("system", "You are a bot")
    conv.add("user", "Hello")
    conv.add("assistant", "Hi there")

    assert len(conv.messages) == 3
    api = conv.to_api_messages()
    assert len(api) == 3
    assert api[0]["role"] == "system"


def test_conversation_clear():
    """Test that clear preserves system messages."""
    conv = Conversation()
    conv.add("system", "System prompt")
    conv.add("user", "Hello")
    conv.add("assistant", "Hi")

    conv.clear()
    assert len(conv.messages) == 1
    assert conv.messages[0].role == "system"


def test_create_conversation_chat():
    """Test chat mode conversation creation."""
    conv = create_conversation("chat")
    assert conv.mode == "chat"
    assert len(conv.messages) == 1
    assert conv.messages[0].role == "system"
    assert "HackBot" in conv.messages[0].content


def test_create_conversation_agent():
    """Test agent mode conversation creation."""
    conv = create_conversation("agent", target="192.168.1.1")
    assert conv.mode == "agent"
    assert conv.target == "192.168.1.1"
    assert "192.168.1.1" in conv.messages[0].content


def test_create_conversation_plan():
    """Test plan mode conversation creation."""
    conv = create_conversation("plan")
    assert conv.mode == "plan"


def test_ai_engine_not_configured():
    """Test engine reports unconfigured state."""
    cfg = AIConfig(api_key="")
    engine = AIEngine(cfg)
    assert not engine.is_configured()


def test_ai_engine_configured():
    """Test engine reports configured state."""
    cfg = AIConfig(api_key="test-key")
    engine = AIEngine(cfg)
    assert engine.is_configured()


def test_system_prompts_exist():
    """Test system prompts are non-empty."""
    assert len(SYSTEM_PROMPT_CHAT) > 100
    assert len(SYSTEM_PROMPT_AGENT) > 100
    assert len(SYSTEM_PROMPT_PLAN) > 100


def test_agent_prompt_documents_install_action():
    """Test that the agent system prompt documents the install action."""
    assert '"action": "install"' in SYSTEM_PROMPT_AGENT
    assert "Tool not found" in SYSTEM_PROMPT_AGENT


# ── API Key Validation Tests ────────────────────────────────────────────────


class TestValidateApiKey:
    """Tests for AIEngine.validate_api_key()."""

    def test_validate_no_key(self):
        """Should fail when no API key is set."""
        cfg = AIConfig(api_key="")
        engine = AIEngine(cfg)
        result = engine.validate_api_key()
        assert not result["valid"]
        assert "No API key" in result["message"]
        assert result["error"] == "missing_key"

    def test_validate_ollama_skips(self):
        """Ollama provider should always return valid (keyless)."""
        cfg = AIConfig(provider="ollama", api_key="")
        engine = AIEngine(cfg)
        result = engine.validate_api_key()
        assert result["valid"]
        assert "ollama" in result["message"]

    def test_validate_local_skips(self):
        """Local provider should always return valid (keyless)."""
        cfg = AIConfig(provider="local", api_key="")
        engine = AIEngine(cfg)
        result = engine.validate_api_key()
        assert result["valid"]
        assert "local" in result["message"]

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_success(self, mock_openai_cls):
        """Should return valid on successful API call."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.model = "gpt-4o"
        mock_client.chat.completions.create.return_value = mock_response

        cfg = AIConfig(api_key="test-key-123", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert result["valid"]
        assert "valid" in result["message"].lower()
        assert "openai" in result["message"]

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_auth_error_401(self, mock_openai_cls):
        """Should detect 401 unauthorized errors."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Error code: 401 - Unauthorized"
        )

        cfg = AIConfig(api_key="bad-key", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert not result["valid"]
        assert "Invalid API key" in result["message"] or "authentication" in result["message"].lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_invalid_key_error(self, mock_openai_cls):
        """Should detect invalid key errors."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Invalid API key provided"
        )

        cfg = AIConfig(api_key="bad-key", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert not result["valid"]
        assert "Invalid" in result["message"] or "authentication" in result["message"].lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_forbidden_403(self, mock_openai_cls):
        """Should detect 403 permission errors."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Error code: 403 Forbidden"
        )

        cfg = AIConfig(api_key="limited-key", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert not result["valid"]
        assert "permission" in result["message"].lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_model_not_found(self, mock_openai_cls):
        """Should detect model not found errors."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Error code: 404 - Model not found"
        )

        cfg = AIConfig(api_key="good-key", provider="openai", model="nonexistent-model")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert not result["valid"]
        assert "not found" in result["message"].lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_rate_limited(self, mock_openai_cls):
        """Rate-limited should still report valid (key works, just quota hit)."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Error code: 429 - Rate limit exceeded"
        )

        cfg = AIConfig(api_key="good-key", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert result["valid"]
        assert "rate" in result["message"].lower() or "quota" in result["message"].lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_timeout(self, mock_openai_cls):
        """Should detect timeout errors."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Request timed out"
        )

        cfg = AIConfig(api_key="good-key", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert not result["valid"]
        assert "timed out" in result["message"].lower() or "timeout" in result["message"].lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_connection_error(self, mock_openai_cls):
        """Should detect connection errors."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Connection refused"
        )

        cfg = AIConfig(api_key="good-key", provider="anthropic", model="claude-sonnet-4-20250514")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert not result["valid"]
        assert "connection" in result["message"].lower() or "connect" in result["message"].lower()

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_generic_error(self, mock_openai_cls):
        """Should handle unknown errors gracefully."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception(
            "Something unexpected happened"
        )

        cfg = AIConfig(api_key="good-key", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        result = engine.validate_api_key()
        assert not result["valid"]
        assert "validation failed" in result["message"].lower()
        assert "error" in result

    @patch("hackbot.core.engine.OpenAI")
    def test_validate_calls_with_minimal_tokens(self, mock_openai_cls):
        """Validation should use max_tokens=1 to minimize cost."""
        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_response = MagicMock()
        mock_response.model = "gpt-4o"
        mock_client.chat.completions.create.return_value = mock_response

        cfg = AIConfig(api_key="test-key", provider="openai", model="gpt-4o")
        engine = AIEngine(cfg)

        engine.validate_api_key()

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs[1]["max_tokens"] == 1
        assert call_kwargs[1]["model"] == "gpt-4o"
