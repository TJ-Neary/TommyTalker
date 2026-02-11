"""
Tests for app-context-aware LLM rewriting.
"""

import pytest
from unittest.mock import patch, MagicMock

from tommy_talker.utils.app_context import AppContext, AppProfile, TextInputFormat


class TestAppContextPrompts:
    """Test that all format types have appropriate prompts."""

    @pytest.fixture
    def llm_client_class(self):
        """Import LLMClient bypassing chromadb."""
        import sys, types
        if 'chromadb' not in sys.modules:
            mock_chromadb = types.ModuleType('chromadb')
            mock_chromadb.Client = type('Client', (), {})
            sys.modules['chromadb'] = mock_chromadb
        from tommy_talker.engine.llm_client import LLMClient
        return LLMClient

    def test_code_prompt_exists(self, llm_client_class):
        assert "code" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_chat_message_prompt_exists(self, llm_client_class):
        assert "chat_message" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_email_prompt_exists(self, llm_client_class):
        assert "email" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_terminal_command_prompt_exists(self, llm_client_class):
        assert "terminal_command" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_markdown_prompt_exists(self, llm_client_class):
        assert "markdown" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_search_query_prompt_exists(self, llm_client_class):
        assert "search_query" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_document_text_prompt_exists(self, llm_client_class):
        assert "document_text" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_spreadsheet_formula_prompt_exists(self, llm_client_class):
        assert "spreadsheet_formula" in llm_client_class.APP_CONTEXT_PROMPTS

    def test_all_prompts_are_strings(self, llm_client_class):
        """Every prompt value is a non-empty string."""
        for key, prompt in llm_client_class.APP_CONTEXT_PROMPTS.items():
            assert isinstance(prompt, str), f"Prompt for {key} is not a string"
            assert len(prompt) > 20, f"Prompt for {key} seems too short"


class TestRewriteForContext:
    """Test rewrite_for_context method routing."""

    @pytest.fixture
    def llm_client(self):
        """Create LLMClient instance (Ollama won't be available in CI)."""
        import sys, types
        if 'chromadb' not in sys.modules:
            mock_chromadb = types.ModuleType('chromadb')
            mock_chromadb.Client = type('Client', (), {})
            sys.modules['chromadb'] = mock_chromadb
        from tommy_talker.engine.llm_client import LLMClient
        return LLMClient(tier=2)

    def _make_context(self, fmt: TextInputFormat, app_name: str = "TestApp",
                      category: str = "Testing") -> AppContext:
        profile = AppProfile(
            name=app_name,
            bundle_id="com.test.app",
            category=category,
            text_input_format=fmt,
        )
        return AppContext(
            app_name=app_name,
            bundle_id="com.test.app",
            profile=profile,
            text_input_format=fmt,
        )

    def test_code_context_uses_code_prompt(self, llm_client):
        """Code format uses the code-specific prompt."""
        ctx = self._make_context(TextInputFormat.CODE, "VS Code", "Developer Tools")

        with patch.object(llm_client, '_rewrite_local') as mock:
            mock.return_value = None
            llm_client.rewrite_for_context("test text", ctx)
            call_args = mock.call_args
            system_prompt = call_args[0][1]
            assert "code" in system_prompt.lower()
            assert "VS Code" in system_prompt

    def test_chat_context_uses_chat_prompt(self, llm_client):
        """Chat format uses the chat-specific prompt."""
        ctx = self._make_context(TextInputFormat.CHAT_MESSAGE, "Slack", "Communication")

        with patch.object(llm_client, '_rewrite_local') as mock:
            mock.return_value = None
            llm_client.rewrite_for_context("test text", ctx)
            system_prompt = mock.call_args[0][1]
            assert "chat" in system_prompt.lower() or "message" in system_prompt.lower()
            assert "Slack" in system_prompt

    def test_email_context_uses_email_prompt(self, llm_client):
        """Email format uses the email-specific prompt."""
        ctx = self._make_context(TextInputFormat.EMAIL, "Mail", "Email")

        with patch.object(llm_client, '_rewrite_local') as mock:
            mock.return_value = None
            llm_client.rewrite_for_context("test text", ctx)
            system_prompt = mock.call_args[0][1]
            assert "email" in system_prompt.lower()

    def test_unknown_format_falls_back_to_professional(self, llm_client):
        """Formats without specific prompts fall back to rewrite_professional."""
        ctx = self._make_context(TextInputFormat.RICH_TEXT)

        with patch.object(llm_client, 'rewrite_professional') as mock:
            mock.return_value = None
            llm_client.rewrite_for_context("test text", ctx)
            mock.assert_called_once_with("test text")

    def test_style_guide_appended(self, llm_client):
        """Style guide is appended to context-aware prompt."""
        llm_client.style_guide = "Always use Oxford commas."
        ctx = self._make_context(TextInputFormat.CODE)

        with patch.object(llm_client, '_rewrite_local') as mock:
            mock.return_value = None
            llm_client.rewrite_for_context("test text", ctx)
            system_prompt = mock.call_args[0][1]
            assert "Oxford commas" in system_prompt

    def test_app_name_in_context_hint(self, llm_client):
        """App name appears in the context hint."""
        ctx = self._make_context(TextInputFormat.TERMINAL_COMMAND, "iTerm2", "Terminal")

        with patch.object(llm_client, '_rewrite_local') as mock:
            mock.return_value = None
            llm_client.rewrite_for_context("run ls", ctx)
            system_prompt = mock.call_args[0][1]
            assert "iTerm2" in system_prompt
            assert "Terminal" in system_prompt
