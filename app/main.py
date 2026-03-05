"""NiceGUI chat application entry point.

Provides a web-based chat interface for the Intelligent Document Processing
Agent. Users can upload large documents, then interact with an AI agent that
analyzes documents using Bedrock Data Automation and answers questions.

Runs locally as a Python app connected to AWS via session credentials.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Any

from nicegui import ui

from app.agent import get_agent
from app.callback_handler import NiceGUIStreamingHandler
from app.config import APP_HOST, APP_PORT, APP_TITLE


@ui.page("/")
async def index() -> None:
    """Main chat page with document upload and streaming agent responses."""
    # Page-level state
    messages: list[dict[str, Any]] = []
    uploaded_file_info: dict[str, Any] = {}
    chat_container_ref: dict[str, Any] = {"element": None}
    input_ref: dict[str, Any] = {"element": None}

    # Dark theme header
    with ui.header().classes("bg-gray-900 text-white"):
        ui.label(APP_TITLE).classes("text-xl font-bold")

    # Main content area
    with ui.column().classes("w-full max-w-4xl mx-auto p-4 gap-4"):
        # Upload section
        ui.label("Upload a Document").classes("text-lg font-semibold")
        ui.label(
            "Upload PDF, DOCX, XLSX, CSV, TXT, or image files for analysis. "
            "Large files are automatically handled with multipart upload."
        ).classes("text-sm text-gray-500")

        async def handle_upload(e: Any) -> None:
            """Save uploaded file locally and update UI state."""
            file_name = e.name
            unique_name = f"{uuid.uuid4().hex}_{file_name}"
            file_path = f"/tmp/{unique_name}"

            with open(file_path, "wb") as f:
                f.write(e.content.read())

            uploaded_file_info["file_path"] = file_path
            uploaded_file_info["file_name"] = file_name
            uploaded_file_info["s3_uri"] = None

            # Show uploaded file badge
            with file_badge_container:
                file_badge_container.clear()
                ui.chip(
                    f"Uploaded: {file_name}",
                    icon="description",
                    color="green",
                ).classes("mt-2")
                ui.chip(
                    f"Analyze {file_name}",
                    icon="auto_fix_high",
                    color="blue",
                    on_click=lambda: set_input_text(f"Upload and analyze {file_name}"),
                ).classes("mt-2 cursor-pointer")

            ui.notify(f"File '{file_name}' uploaded successfully!", type="positive")

        upload = ui.upload(  # noqa: F841
            on_upload=handle_upload,
            auto_upload=True,
            label="Drop file here or click to upload",
        ).props(
            'accept=".pdf,.docx,.xlsx,.csv,.txt,.png,.jpg,.jpeg,.tiff" '
            'max-file-size="524288000"'
        ).classes("w-full")

        file_badge_container = ui.row().classes("gap-2")

        ui.separator()

        # Chat container
        ui.label("Chat").classes("text-lg font-semibold")
        chat_scroll = ui.scroll_area().classes("w-full border rounded-lg").style("height: 500px;")
        with chat_scroll:
            chat_column = ui.column().classes("w-full p-4 gap-2")
            chat_container_ref["element"] = chat_column

        def set_input_text(text: str) -> None:
            """Set the input field text programmatically."""
            if input_ref["element"] is not None:
                input_ref["element"].value = text

        def render_message(msg: dict[str, Any]) -> None:
            """Render a single chat message in the chat container."""
            with chat_container_ref["element"]:
                if msg["role"] == "user":
                    ui.chat_message(
                        text=msg["content"],
                        sent=True,
                        stamp=msg["timestamp"],
                    )
                else:
                    with ui.chat_message(sent=False, stamp=msg["timestamp"]):
                        # Reasoning section (collapsible)
                        if msg.get("reasoning"):
                            with ui.expansion("Thinking...", icon="psychology").classes(
                                "w-full text-xs"
                            ):
                                ui.markdown(msg["reasoning"]).classes("text-gray-400 text-xs")
                        # Main response
                        ui.markdown(msg["content"])

        async def send_message() -> None:
            """Handle sending a user message and getting agent response."""
            if input_ref["element"] is None:
                return

            user_text = input_ref["element"].value
            if not user_text or not user_text.strip():
                return

            # Clear input
            input_ref["element"].value = ""

            # Add user message
            timestamp = datetime.now().strftime("%H:%M")
            user_msg: dict[str, Any] = {
                "role": "user",
                "content": user_text.strip(),
                "timestamp": timestamp,
            }
            messages.append(user_msg)

            # Render user message
            render_message(user_msg)

            # Create placeholders for assistant response
            with chat_container_ref["element"]:
                with ui.chat_message(sent=False, stamp=timestamp) as assistant_bubble:  # noqa: F841
                    reasoning_expansion = ui.expansion(
                        "Thinking...", icon="psychology"
                    ).classes("w-full text-xs")
                    with reasoning_expansion:
                        reasoning_md = ui.markdown("")
                    response_md = ui.markdown("*Generating response...*")

            # Build prompt, including file context if a file is uploaded
            prompt = user_text.strip()
            if uploaded_file_info.get("file_name"):
                file_context = (
                    f"\n\n[User has uploaded a file: {uploaded_file_info['file_name']}. "
                    f"Local path: {uploaded_file_info.get('file_path', 'unknown')}. "
                )
                if uploaded_file_info.get("s3_uri"):
                    file_context += f"S3 URI: {uploaded_file_info['s3_uri']}]"
                else:
                    file_context += "File has not been uploaded to S3 yet.]"
                prompt += file_context

            # Create callback handler
            handler = NiceGUIStreamingHandler(
                response_container=response_md,
                reasoning_container=reasoning_md,
            )

            # Run agent in a thread to avoid blocking the UI event loop
            try:
                agent = get_agent(callback_handler=handler)

                def run_agent() -> None:
                    agent(prompt)

                await asyncio.to_thread(run_agent)

                # Update S3 URI if the agent uploaded a file
                if handler.response_text and "s3://" in handler.response_text:
                    for part in handler.response_text.split():
                        if part.startswith("s3://ntkey-"):
                            uploaded_file_info["s3_uri"] = part.rstrip(".,;)")
                            break

            except Exception as exc:
                response_md.set_content(f"**Error:** {exc}")

            # Store assistant message
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": handler.response_text or "No response generated.",
                "reasoning": handler.reasoning_text,
                "timestamp": timestamp,
            }
            messages.append(assistant_msg)

            # Scroll to bottom
            await ui.run_javascript("window.scrollTo(0, document.body.scrollHeight)")

        # Input area
        with ui.row().classes("w-full gap-2 items-center"):
            text_input = ui.input(
                placeholder="Ask about your documents or any topic...",
            ).classes("flex-grow").on("keydown.enter", send_message)
            input_ref["element"] = text_input

            ui.button(
                "Send", icon="send", on_click=send_message
            ).props("color=primary")

        # Example prompt suggestions
        ui.label("Try these prompts:").classes("text-sm text-gray-500 mt-2")
        with ui.row().classes("gap-2 flex-wrap"):
            for suggestion in [
                "Personal IRS tax submission",
                "Analyze clinical trials protocol",
                "Inspect this financial report",
                "What are the latest filing deadlines?",
            ]:
                ui.chip(
                    suggestion,
                    icon="lightbulb",
                    on_click=lambda s=suggestion: set_input_text(s),
                ).classes("cursor-pointer")


def run() -> None:
    """Start the NiceGUI application server.

    Runs locally using Python, connecting to AWS services via the default
    credential chain (environment variables, ~/.aws/credentials, instance profile).
    """
    ui.run(title=APP_TITLE, host=APP_HOST, port=APP_PORT, reload=False)


if __name__ == "__main__":
    run()
