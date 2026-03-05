"""Tests for Strands Agent tools: upload, analyze, and web search."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestUploadDocumentToS3:
    """Tests for the S3 multipart upload tool."""

    @patch("app.tools.upload_document.get_boto_session")
    def test_small_file_uses_put_object(self, mock_get_session: MagicMock) -> None:
        """Files smaller than CHUNK_SIZE should use simple put_object."""
        mock_s3 = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3
        mock_get_session.return_value = mock_session

        # Create a small temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
            tmp.write(b"small file content")
            tmp_path = tmp.name

        try:
            from app.tools.upload_document import upload_document_to_s3

            # Call the tool function directly (unwrap the @tool decorator)
            fn = upload_document_to_s3
            if hasattr(fn, "fn"):
                fn = fn.fn
            elif hasattr(fn, "__wrapped__"):
                fn = fn.__wrapped__

            result = fn(file_path=tmp_path, file_name="test.txt")

            assert result == "s3://ntkey-idp-documents/uploads/test.txt"
            mock_s3.put_object.assert_called_once()
            call_kwargs = mock_s3.put_object.call_args
            assert call_kwargs[1]["Bucket"] == "ntkey-idp-documents" or call_kwargs.kwargs["Bucket"] == "ntkey-idp-documents"
            mock_s3.create_multipart_upload.assert_not_called()
        finally:
            os.unlink(tmp_path)

    @patch("app.tools.upload_document.CHUNK_SIZE", 10)
    @patch("app.tools.upload_document.get_boto_session")
    def test_large_file_uses_multipart_upload(self, mock_get_session: MagicMock) -> None:
        """Files larger than CHUNK_SIZE should use multipart upload."""
        mock_s3 = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3
        mock_get_session.return_value = mock_session

        mock_s3.create_multipart_upload.return_value = {"UploadId": "test-upload-id"}
        mock_s3.upload_part.return_value = {"ETag": '"etag123"'}

        # Create a file larger than the mocked CHUNK_SIZE of 10 bytes
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"A" * 25)  # 25 bytes > 10 byte chunk
            tmp_path = tmp.name

        try:
            from app.tools.upload_document import upload_document_to_s3

            fn = upload_document_to_s3
            if hasattr(fn, "fn"):
                fn = fn.fn
            elif hasattr(fn, "__wrapped__"):
                fn = fn.__wrapped__

            result = fn(file_path=tmp_path, file_name="large.pdf")

            assert result == "s3://ntkey-idp-documents/uploads/large.pdf"
            mock_s3.create_multipart_upload.assert_called_once_with(
                Bucket="ntkey-idp-documents", Key="uploads/large.pdf"
            )
            assert mock_s3.upload_part.call_count >= 2
            mock_s3.complete_multipart_upload.assert_called_once()
        finally:
            os.unlink(tmp_path)

    @patch("app.tools.upload_document.CHUNK_SIZE", 10)
    @patch("app.tools.upload_document.get_boto_session")
    def test_multipart_upload_aborts_on_error(self, mock_get_session: MagicMock) -> None:
        """On upload failure, abort_multipart_upload should be called."""
        mock_s3 = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_s3
        mock_get_session.return_value = mock_session

        mock_s3.create_multipart_upload.return_value = {"UploadId": "fail-upload-id"}
        mock_s3.upload_part.side_effect = Exception("Upload part failed")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"B" * 25)
            tmp_path = tmp.name

        try:
            from app.tools.upload_document import upload_document_to_s3

            fn = upload_document_to_s3
            if hasattr(fn, "fn"):
                fn = fn.fn
            elif hasattr(fn, "__wrapped__"):
                fn = fn.__wrapped__

            with pytest.raises(RuntimeError, match="Failed to upload"):
                fn(file_path=tmp_path, file_name="fail.pdf")

            mock_s3.abort_multipart_upload.assert_called_once_with(
                Bucket="ntkey-idp-documents",
                Key="uploads/fail.pdf",
                UploadId="fail-upload-id",
            )
        finally:
            os.unlink(tmp_path)


class TestAnalyzeDocument:
    """Tests for the Bedrock Data Automation analysis tool."""

    @patch("app.tools.analyze_document.time.sleep", return_value=None)
    @patch("app.tools.analyze_document.get_boto_session")
    def test_successful_analysis(
        self, mock_get_session: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test successful document analysis with BDA."""
        mock_bda = MagicMock()
        mock_s3 = MagicMock()
        mock_session = MagicMock()

        def client_factory(service: str) -> MagicMock:
            if service == "bedrock-data-automation-runtime":
                return mock_bda
            return mock_s3

        mock_session.client.side_effect = client_factory
        mock_get_session.return_value = mock_session

        mock_bda.invoke_data_automation_async.return_value = {
            "invocationArn": "arn:aws:bedrock:us-east-1:123456:invocation/abc"
        }
        mock_bda.get_data_automation_status.return_value = {
            "status": "Success",
            "outputConfiguration": {"s3Uri": "s3://ntkey-idp-documents/bda-output/result.json"},
        }

        analysis_result = {"summary": "Tax return analysis complete", "entities": []}
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps(analysis_result).encode("utf-8")
        mock_s3.get_object.return_value = {"Body": mock_body}

        from app.tools.analyze_document import analyze_document

        fn = analyze_document
        if hasattr(fn, "fn"):
            fn = fn.fn
        elif hasattr(fn, "__wrapped__"):
            fn = fn.__wrapped__

        result = fn(
            s3_uri="s3://ntkey-idp-documents/uploads/tax.pdf",
            analysis_prompt="Personal IRS tax submission",
        )

        assert "Document Analysis Results" in result
        assert "Personal IRS tax submission" in result
        mock_bda.invoke_data_automation_async.assert_called_once()
        mock_bda.get_data_automation_status.assert_called_once()

    @patch("app.tools.analyze_document.time.sleep", return_value=None)
    @patch("app.tools.analyze_document.get_boto_session")
    def test_analysis_timeout(
        self, mock_get_session: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test that analysis returns timeout message after max attempts."""
        mock_bda = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_bda
        mock_get_session.return_value = mock_session

        mock_bda.invoke_data_automation_async.return_value = {
            "invocationArn": "arn:aws:bedrock:us-east-1:123456:invocation/timeout"
        }
        # Always return InProgress
        mock_bda.get_data_automation_status.return_value = {"status": "InProgress"}

        from app.tools.analyze_document import analyze_document

        fn = analyze_document
        if hasattr(fn, "fn"):
            fn = fn.fn
        elif hasattr(fn, "__wrapped__"):
            fn = fn.__wrapped__

        result = fn(
            s3_uri="s3://ntkey-idp-documents/uploads/slow.pdf",
            analysis_prompt="Analyze this",
        )

        assert "timed out" in result.lower()

    @patch("app.tools.analyze_document.time.sleep", return_value=None)
    @patch("app.tools.analyze_document.get_boto_session")
    def test_analysis_service_error(
        self, mock_get_session: MagicMock, mock_sleep: MagicMock
    ) -> None:
        """Test that service errors are handled gracefully."""
        mock_bda = MagicMock()
        mock_session = MagicMock()
        mock_session.client.return_value = mock_bda
        mock_get_session.return_value = mock_session

        mock_bda.invoke_data_automation_async.return_value = {
            "invocationArn": "arn:aws:bedrock:us-east-1:123456:invocation/err"
        }
        mock_bda.get_data_automation_status.return_value = {
            "status": "ServiceError",
            "error": {"message": "Internal service error"},
        }

        from app.tools.analyze_document import analyze_document

        fn = analyze_document
        if hasattr(fn, "fn"):
            fn = fn.fn
        elif hasattr(fn, "__wrapped__"):
            fn = fn.__wrapped__

        result = fn(
            s3_uri="s3://ntkey-idp-documents/uploads/err.pdf",
            analysis_prompt="Analyze",
        )

        assert "failed" in result.lower() or "ServiceError" in result


class TestWebSearch:
    """Tests for the web search tool."""

    def test_web_search_callable(self) -> None:
        """Web search tool should be callable."""
        from app.tools.web_search import web_search

        assert callable(web_search)

    def test_web_search_returns_string(self) -> None:
        """Web search should return a string result."""
        from app.tools.web_search import web_search

        fn = web_search
        if hasattr(fn, "fn"):
            fn = fn.fn
        elif hasattr(fn, "__wrapped__"):
            fn = fn.__wrapped__

        result = fn(query="IRS tax filing deadlines", max_results=3)
        assert isinstance(result, str)
        assert "IRS tax filing deadlines" in result

    def test_web_search_default_max_results(self) -> None:
        """Web search should work with default max_results."""
        from app.tools.web_search import web_search

        fn = web_search
        if hasattr(fn, "fn"):
            fn = fn.fn
        elif hasattr(fn, "__wrapped__"):
            fn = fn.__wrapped__

        result = fn(query="test query")
        assert isinstance(result, str)
