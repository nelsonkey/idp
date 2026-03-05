"""Application configuration constants and utilities.

Provides configuration for AWS services, Bedrock model settings,
S3 bucket names, and application server parameters. Uses environment
variables with sensible defaults for local development.
"""

import os

import boto3

# AWS Configuration
AWS_REGION: str = os.environ.get("AWS_REGION", "us-east-1")

# S3 Configuration - bucket name must start with 'ntkey-'
S3_BUCKET_NAME: str = "ntkey-idp-documents"

# Bedrock Data Automation Configuration
BDA_PROFILE_ARN: str = os.environ.get("BDA_PROFILE_ARN", "")

# Bedrock Model Configuration - Sonnet 4.5 US profile
BEDROCK_MODEL_ID: str = "us.anthropic.claude-sonnet-4-5-20250514-v1:0"

# Reasoning / thinking budget for extended thinking
THINKING_BUDGET_TOKENS: int = 10000

# Max tokens for model output
MAX_TOKENS: int = 16000

# Multipart upload chunk size: 10 MB
CHUNK_SIZE: int = 10 * 1024 * 1024

# Application settings
APP_TITLE: str = "Intelligent Document Processing Agent"
APP_HOST: str = "0.0.0.0"
APP_PORT: int = 8080


def get_boto_session() -> boto3.Session:
    """Return a boto3 Session using the default credential chain.

    Supports local development with AWS session credentials configured via:
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN)
    - Shared credentials file (~/.aws/credentials)
    - AWS SSO / AWS CLI profiles (AWS_PROFILE)
    - EC2 instance profile / ECS task role

    Returns:
        boto3.Session: A configured boto3 session.
    """
    return boto3.Session(region_name=AWS_REGION)
