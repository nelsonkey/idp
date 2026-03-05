"""Strands Agent configuration with Bedrock Sonnet 4.5 and reasoning.

Creates and configures the Strands Agent with Amazon Bedrock Sonnet 4.5 US
profile as the LLM, extended thinking/reasoning enabled, and three tools:
document upload, document analysis, and web search.
"""

from typing import Any

from strands import Agent
from strands.models.bedrock import BedrockModel

from app import config
from app.tools.analyze_document import analyze_document
from app.tools.upload_document import upload_document_to_s3
from app.tools.web_search import web_search

SYSTEM_PROMPT = """\
You are an Intelligent Document Processing (IDP) assistant. You help users \
upload large documents to S3, analyze them using Amazon Bedrock Data Automation, \
and answer specific questions about the documents or related topics using web search.

Your capabilities:
1) Upload documents to S3 using multipart upload for large files
2) Analyze documents using Bedrock Data Automation to extract insights, summaries, \
and structured data
3) Search the web to answer specific questions that require external knowledge

Workflow:
- When a user uploads a document, use the upload_document_to_s3 tool to store it in S3.
- When a user asks to analyze a document, use the analyze_document tool with the S3 URI \
and the user's analysis prompt (area of interest).
- When a user asks factual questions or needs external context, use the web_search tool.

Example analysis prompts users might ask:
- Personal IRS tax submission analysis
- Analyze clinical trials protocol
- Inspect this financial report
- Extract key terms from this legal contract

Always explain your reasoning and provide detailed analysis results. When analyzing \
documents, clearly describe what you found and organize the information in a readable format.
"""


def get_agent(callback_handler: Any) -> Agent:
    """Create and return a configured Strands Agent.

    Sets up the BedrockModel with Sonnet 4.5 US profile, streaming enabled,
    and extended thinking/reasoning. Registers all three tools and applies
    the system prompt for IDP assistance.

    Args:
        callback_handler: A callable that receives streaming events with kwargs
            including reasoningText, data, complete, and event.

    Returns:
        A fully configured Strands Agent ready for invocation.
    """
    bedrock_model = BedrockModel(
        model_id=config.BEDROCK_MODEL_ID,
        streaming=True,
        max_tokens=config.MAX_TOKENS,
        region_name=config.AWS_REGION,
        additional_request_fields={
            "thinking": {
                "type": "enabled",
                "budgetTokens": config.THINKING_BUDGET_TOKENS,
            }
        },
    )

    agent = Agent(
        model=bedrock_model,
        tools=[upload_document_to_s3, analyze_document, web_search],
        callback_handler=callback_handler,
        system_prompt=SYSTEM_PROMPT,
    )

    return agent
