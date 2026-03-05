# Intelligent Document Processing Agent

A NiceGUI-based chat application powered by the Strands Agents SDK with Amazon Bedrock Sonnet 4.5 (US profile). Supports streaming responses with extended thinking/reasoning, large document upload to S3 via multipart upload, document analysis using Amazon Bedrock Data Automation, and web search for answering specific questions.

## Architecture

```
NiceGUI Chat UI (localhost:8080)
       |
       v
Strands Agent (Bedrock Sonnet 4.5, streaming + reasoning)
       |
       +---> upload_document_to_s3  (S3 multipart upload to ntkey-idp-documents)
       +---> analyze_document       (Bedrock Data Automation Runtime)
       +---> web_search             (Web search for factual questions)
```

## Features

- **Chat-based interface** with streaming responses and reasoning/thinking displayed in collapsible sections
- **Amazon Bedrock Sonnet 4.5** (US profile) as the LLM with extended thinking enabled
- **Large document upload** to S3 with multipart upload support (bucket: ntkey-idp-documents)
- **Document analysis** using Amazon Bedrock Data Automation for extracting insights, summaries, and structured data
- **Web search** tool for answering specific factual questions beyond document analysis
- **Example prompts**: "Personal IRS tax submission", "Analyze clinical trials protocol", "Inspect this financial report"

## Prerequisites

- Python 3.10+
- AWS account with Bedrock access (Sonnet 4.5 model enabled)
- AWS CLI configured with credentials (`aws configure` or environment variables)
- Existing GxPEC2-role with admin access (do NOT create new roles)

## Installation

```bash
pip install -e .
```

For development:

```bash
pip install -e ".[dev]"
```

## Configuration

Set these environment variables (or use defaults):

| Variable | Default | Description |
|----------|---------|-------------|
| `AWS_REGION` | `us-east-1` | AWS region for Bedrock and S3 |
| `AWS_PROFILE` | (default) | AWS CLI profile to use |
| `BDA_PROFILE_ARN` | (empty) | Bedrock Data Automation profile ARN |

AWS credentials are loaded via the default credential chain:
- Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`)
- Shared credentials file (`~/.aws/credentials`)
- AWS SSO / AWS CLI profiles
- EC2 instance profile / ECS task role

## Usage

```bash
# Run the application
python -m app.main

# Or use the entry point
idp-agent
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

### Workflow

1. **Upload a document** - drag and drop or click to upload PDF, DOCX, XLSX, CSV, TXT, or image files
2. **Enter a prompt** - describe the area of interest for analysis
3. **View results** - the agent uploads to S3, runs Bedrock Data Automation, and streams back analysis results with reasoning

## CDK Deployment

```bash
cd cdk
pip install -r requirements.txt
cdk deploy
```

## Running Tests

```bash
pytest tests/ -v
```

## Project Structure

```
idp/
  app/
    __init__.py
    config.py              # Configuration constants and boto3 session
    main.py                # NiceGUI application entry point
    agent.py               # Strands Agent with Bedrock Sonnet 4.5
    callback_handler.py    # Streaming callback for NiceGUI UI
    tools/
      __init__.py
      upload_document.py   # S3 multipart upload tool
      analyze_document.py  # Bedrock Data Automation tool
      web_search.py        # Web search tool
  tests/
    __init__.py
    test_config.py
    test_tools.py
    test_agent.py
  cdk/                     # AWS CDK infrastructure (FEAT-002)
  pyproject.toml
  README.md
```
