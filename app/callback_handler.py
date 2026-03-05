"""NiceGUI streaming callback handler for Strands Agent.

Routes agent streaming events to NiceGUI UI elements: reasoning/thinking
text goes to a collapsible reasoning section, response data goes to the
main response markdown area, and tool usage events show indicators.
"""

from typing import Any, Callable


class NiceGUIStreamingHandler:
    """Callback handler that streams Strands Agent output to NiceGUI elements.

    Accumulates reasoning text and response data, updating the corresponding
    NiceGUI UI containers in real-time as the agent generates output.

    Args:
        response_container: A NiceGUI element to display the main response markdown.
        reasoning_container: A NiceGUI element to display reasoning/thinking text.
        on_update: Optional callback invoked after each UI update for triggering refreshes.
    """

    def __init__(
        self,
        response_container: Any,
        reasoning_container: Any,
        on_update: Callable[[], None] | None = None,
    ) -> None:
        self.response_container = response_container
        self.reasoning_container = reasoning_container
        self.on_update = on_update
        self._response_text: str = ""
        self._reasoning_text: str = ""
        self._tool_uses: list[str] = []

    def reset(self) -> None:
        """Clear all accumulated text and tool usage records."""
        self._response_text = ""
        self._reasoning_text = ""
        self._tool_uses = []

    def __call__(self, **kwargs: Any) -> None:
        """Handle a streaming event from the Strands Agent.

        Dispatches based on event type:
        - reasoningText: Append to reasoning accumulator, update reasoning container.
        - data: Append to response accumulator, update response container.
        - event with toolUse: Record and display tool usage indicator.
        - complete: Finalize the display.

        Args:
            **kwargs: Event data from the Strands Agent callback system.
                Expected keys: reasoningText (str), data (str), complete (bool),
                event (dict with contentBlockStart.start.toolUse).
        """
        # Handle reasoning / thinking text
        reasoning_text = kwargs.get("reasoningText")
        if reasoning_text:
            self._reasoning_text += reasoning_text
            if self.reasoning_container is not None:
                self.reasoning_container.set_content(self._reasoning_text)

        # Handle main response data
        data = kwargs.get("data")
        if data:
            self._response_text += data
            if self.response_container is not None:
                self.response_container.set_content(self._response_text)

        # Handle tool use events
        event = kwargs.get("event", {})
        if isinstance(event, dict):
            tool_use = (
                event.get("contentBlockStart", {})
                .get("start", {})
                .get("toolUse")
            )
            if tool_use:
                tool_name = tool_use.get("name", "unknown")
                self._tool_uses.append(tool_name)

        # Handle completion
        if kwargs.get("complete"):
            # Final update to ensure all content is displayed
            if self.response_container is not None:
                self.response_container.set_content(self._response_text)
            if self.reasoning_container is not None and self._reasoning_text:
                self.reasoning_container.set_content(self._reasoning_text)

        # Trigger optional UI refresh callback
        if self.on_update is not None:
            self.on_update()

    @property
    def response_text(self) -> str:
        """Return the accumulated response text."""
        return self._response_text

    @property
    def reasoning_text(self) -> str:
        """Return the accumulated reasoning text."""
        return self._reasoning_text

    @property
    def tool_uses(self) -> list[str]:
        """Return the list of tool names that were invoked."""
        return list(self._tool_uses)
