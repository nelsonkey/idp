"""Bedrock Data Automation document analysis tool.

Uses the Amazon Bedrock Data Automation Runtime API to analyze documents
stored in S3. Invokes async analysis and polls for completion, then
retrieves and returns the analysis results.
"""

import json
import time

from strands import tool

from app.config import BDA_PROFILE_ARN, S3_BUCKET_NAME, get_boto_session


@tool
def analyze_document(s3_uri: str, analysis_prompt: str) -> str:
    """Analyze a document stored in S3 using Amazon Bedrock Data Automation.

    This tool invokes Bedrock Data Automation to extract insights, summaries,
    and structured data from the uploaded document. Use the analysis_prompt to
    specify the kind of analysis the user wants, such as:
    - 'Personal IRS tax submission' to extract tax form data
    - 'Analyze clinical trials protocol' to summarize trial details
    - 'Inspect this financial report' to extract financial metrics
    - 'Extract key terms from this legal contract'

    Args:
        s3_uri: The S3 URI of the document to analyze (e.g. s3://ntkey-idp-documents/uploads/file.pdf).
        analysis_prompt: Description of what kind of analysis the user wants performed on the document.

    Returns:
        A formatted string containing the analysis results from Bedrock Data Automation.
    """
    session = get_boto_session()
    bda_client = session.client("bedrock-data-automation-runtime")
    s3_client = session.client("s3")

    output_s3_uri = f"s3://{S3_BUCKET_NAME}/bda-output/"

    # Start async data automation job
    invoke_response = bda_client.invoke_data_automation_async(
        inputConfiguration={"s3Uri": s3_uri},
        outputConfiguration={"s3Uri": output_s3_uri},
        dataAutomationProfileArn=BDA_PROFILE_ARN,
    )
    invocation_arn = invoke_response["invocationArn"]

    # Poll for completion (max 60 attempts, 5 seconds apart = 5 minutes)
    max_attempts = 60
    poll_interval = 5
    status_response: dict = {}

    for _ in range(max_attempts):
        status_response = bda_client.get_data_automation_status(invocationArn=invocation_arn)
        status = status_response.get("status", "")

        if status == "Success":
            break
        elif status in ("ServiceError", "ClientError"):
            error_msg = status_response.get("error", {}).get("message", "Unknown error")
            return f"Document analysis failed with status '{status}': {error_msg}"

        time.sleep(poll_interval)
    else:
        return (
            f"Document analysis timed out after {max_attempts * poll_interval} seconds. "
            f"Invocation ARN: {invocation_arn}"
        )

    # Retrieve analysis results from S3
    result_s3_uri = status_response.get("outputConfiguration", {}).get("s3Uri", "")
    if not result_s3_uri:
        return "Analysis completed but no output URI was returned."

    # Parse s3://bucket/key format
    uri_without_scheme = result_s3_uri.replace("s3://", "")
    bucket = uri_without_scheme.split("/", 1)[0]
    key = uri_without_scheme.split("/", 1)[1] if "/" in uri_without_scheme else ""

    try:
        obj_response = s3_client.get_object(Bucket=bucket, Key=key)
        result_body = obj_response["Body"].read().decode("utf-8")
        result_data = json.loads(result_body)

        # Format results for readability
        formatted = json.dumps(result_data, indent=2, default=str)
        return (
            f"## Document Analysis Results\n\n"
            f"**Analysis Topic:** {analysis_prompt}\n\n"
            f"**Source:** {s3_uri}\n\n"
            f"```json\n{formatted}\n```"
        )
    except json.JSONDecodeError:
        return f"Analysis completed. Raw output:\n\n{result_body}"
    except Exception as exc:
        return f"Analysis completed but failed to retrieve results: {exc}"
