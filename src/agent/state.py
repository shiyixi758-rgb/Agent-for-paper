"""Shared state for the AgentForPaper multi-agent graph."""

from langgraph.graph import MessagesState


class InputState(MessagesState):
    """External input schema — only ``messages`` is required from the caller.

    LangGraph Studio and the API use this schema for the input form.
    """
