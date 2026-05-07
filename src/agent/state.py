"""Shared state for the AgentForPaper multi-agent graph."""

from langgraph.graph import MessagesState


class State(MessagesState):
    """Conversation state shared across all agents.

    Inherits ``messages`` (Annotated[list, add_messages]) from MessagesState.
    ``user_profile`` holds the content of USER.md, loaded at session start
    by the profile_agent and referenced by every other agent for personalisation.
    """

    user_profile: str = ""
