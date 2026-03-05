"""Tests for application configuration."""

import re
from unittest.mock import patch

from app import config


class TestConfigConstants:
    """Test that all configuration constants are properly defined."""

    def test_s3_bucket_name_starts_with_ntkey(self) -> None:
        """S3 bucket name must start with 'ntkey-' per project requirements."""
        assert config.S3_BUCKET_NAME.startswith("ntkey-")
        assert config.S3_BUCKET_NAME == "ntkey-idp-documents"

    def test_bedrock_model_id_contains_sonnet(self) -> None:
        """Model ID must reference Sonnet 4.5."""
        assert "sonnet" in config.BEDROCK_MODEL_ID.lower()
        assert config.BEDROCK_MODEL_ID == "us.anthropic.claude-sonnet-4-5-20250514-v1:0"

    def test_aws_region_is_valid(self) -> None:
        """AWS region should match the standard region format."""
        pattern = r"^[a-z]{2}-[a-z]+-\d+$"
        assert re.match(pattern, config.AWS_REGION), f"Invalid region: {config.AWS_REGION}"

    def test_chunk_size_positive(self) -> None:
        """Chunk size for multipart upload must be positive."""
        assert config.CHUNK_SIZE > 0
        assert config.CHUNK_SIZE == 10 * 1024 * 1024  # 10 MB

    def test_thinking_budget_tokens_positive(self) -> None:
        """Thinking budget tokens must be positive for reasoning mode."""
        assert config.THINKING_BUDGET_TOKENS > 0
        assert config.THINKING_BUDGET_TOKENS == 10000

    def test_max_tokens_positive(self) -> None:
        """Max tokens must be positive."""
        assert config.MAX_TOKENS > 0

    def test_app_title_defined(self) -> None:
        """App title should be a non-empty string."""
        assert isinstance(config.APP_TITLE, str)
        assert len(config.APP_TITLE) > 0

    def test_app_host_and_port(self) -> None:
        """Host and port should be valid."""
        assert config.APP_HOST == "0.0.0.0"
        assert isinstance(config.APP_PORT, int)
        assert 1 <= config.APP_PORT <= 65535

    @patch("app.config.boto3.Session")
    def test_get_boto_session_returns_session(self, mock_session_cls: object) -> None:
        """get_boto_session should return a boto3.Session instance."""
        session = config.get_boto_session()
        assert session is not None

    def test_bda_profile_arn_is_string(self) -> None:
        """BDA profile ARN should be a string (can be empty as placeholder)."""
        assert isinstance(config.BDA_PROFILE_ARN, str)
