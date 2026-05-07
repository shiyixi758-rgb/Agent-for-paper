"""Shared state for the AgentForPaper multi-agent graph."""

from langgraph.graph import MessagesState


class InputState(MessagesState):
    """External input schema — only ``messages`` is required from the caller.

    LangGraph Studio and the API use this schema for the input form,
    so ``user_profile`` is hidden from the user and managed internally.
    """


class State(InputState):
    """Full internal state shared across all agent nodes.

    ``user_profile`` is populated automatically by profile_agent on the
    first turn and persisted in the thread checkpoint thereafter.
    """

    user_profile: str = ""
