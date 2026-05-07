"""Shared state for the AgentForPaper multi-agent graph."""

from typing import Annotated

from langgraph.graph import MessagesState


class InputState(MessagesState):
    """External input schema — only ``messages`` is required from the caller.

    LangGraph Studio and the API use this schema for the input form,
    so internal orchestration fields are hidden from the user.
    """


class State(InputState):
    """Full internal state shared across all agent nodes.

    ``user_profile``  — user's research profile (USER.md content).
    ``plan``          — ordered list of agent names to execute, set once by planner.
    ``current_step``  — index into ``plan``; executor increments after each agent.
    """

    user_profile: str = ""
    plan: list[str] = []
    current_step: int = 0
