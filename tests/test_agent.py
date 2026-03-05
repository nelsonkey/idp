"""Tests for Strands Agent configuration."""

from unittest.mock import MagicMock, patch


class TestGetAgent:
    """Tests for agent creation and configuration."""

    @patch("app.agent.Agent")
    @patch("app.agent.BedrockModel")
    def test_bedrock_model_uses_sonnet_4_5(
        self, mock_bedrock_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """BedrockModel must be created with Sonnet 4.5 model ID."""
        from app.agent import get_agent

        handler = MagicMock()
        get_agent(handler)

        mock_bedrock_cls.assert_called_once()
        call_kwargs = mock_bedrock_cls.call_args.kwargs
        assert "sonnet-4-5" in call_kwargs["model_id"]
        assert call_kwargs["model_id"] == "us.anthropic.claude-sonnet-4-5-20250514-v1:0"

    @patch("app.agent.Agent")
    @patch("app.agent.BedrockModel")
    def test_bedrock_model_streaming_enabled(
        self, mock_bedrock_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """BedrockModel must have streaming=True."""
        from app.agent import get_agent

        handler = MagicMock()
        get_agent(handler)

        call_kwargs = mock_bedrock_cls.call_args.kwargs
        assert call_kwargs["streaming"] is True

    @patch("app.agent.Agent")
    @patch("app.agent.BedrockModel")
    def test_bedrock_model_thinking_enabled(
        self, mock_bedrock_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """BedrockModel must have thinking/reasoning config in additional_request_fields."""
        from app.agent import get_agent

        handler = MagicMock()
        get_agent(handler)

        call_kwargs = mock_bedrock_cls.call_args.kwargs
        additional_fields = call_kwargs["additional_request_fields"]
        assert "thinking" in additional_fields
        assert additional_fields["thinking"]["type"] == "enabled"
        assert additional_fields["thinking"]["budgetTokens"] == 10000

    @patch("app.agent.Agent")
    @patch("app.agent.BedrockModel")
    def test_agent_has_three_tools(
        self, mock_bedrock_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """Agent must be created with 3 tools: upload, analyze, web_search."""
        from app.agent import get_agent

        handler = MagicMock()
        get_agent(handler)

        mock_agent_cls.assert_called_once()
        call_kwargs = mock_agent_cls.call_args.kwargs
        assert len(call_kwargs["tools"]) == 3

    @patch("app.agent.Agent")
    @patch("app.agent.BedrockModel")
    def test_agent_has_system_prompt(
        self, mock_bedrock_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """Agent must have a system prompt mentioning document processing."""
        from app.agent import get_agent

        handler = MagicMock()
        get_agent(handler)

        call_kwargs = mock_agent_cls.call_args.kwargs
        system_prompt = call_kwargs["system_prompt"]
        assert "document" in system_prompt.lower()
        assert "processing" in system_prompt.lower() or "upload" in system_prompt.lower()

    @patch("app.agent.Agent")
    @patch("app.agent.BedrockModel")
    def test_agent_callback_handler_passed(
        self, mock_bedrock_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """Agent must receive the callback handler."""
        from app.agent import get_agent

        handler = MagicMock()
        get_agent(handler)

        call_kwargs = mock_agent_cls.call_args.kwargs
        assert call_kwargs["callback_handler"] is handler

    @patch("app.agent.Agent")
    @patch("app.agent.BedrockModel")
    def test_agent_returns_agent_instance(
        self, mock_bedrock_cls: MagicMock, mock_agent_cls: MagicMock
    ) -> None:
        """get_agent must return the Agent instance."""
        from app.agent import get_agent

        handler = MagicMock()
        result = get_agent(handler)

        assert result is mock_agent_cls.return_value
