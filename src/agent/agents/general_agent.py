"""General conversation agent.

Handles greetings, off-topic questions, and anything that does not
require paper search, analysis, or graph operations.
No tools needed — responds directly with the LLM.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Literal

from langchain_core.messages import AIMessage, SystemMessage
from langgraph.types import Command

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from agent.state import State

_SOUL_PATH = Path(__file__).parents[4] / "workspace" / "SOUL.md"
_SOUL_FALLBACK = (
    "You are AgentForPaper, a personal AI research assistant specialising in "
    "academic papers. Be friendly and helpful. Match the user's language."
)


def _load_soul() -> str:
    if _SOUL_PATH.exists():
        return _SOUL_PATH.read_text(encoding="utf-8")
    return _SOUL_FALLBACK


def make_general_agent_node(llm: "BaseChatModel"):
    """Return a node function that handles general conversation directly."""
    soul = _load_soul()

    def general_agent_node(state: "State") -> "Command[Literal['executor']]":
        """Respond to greetings and off-topic queries without using tools."""
        messages = [SystemMessage(content=soul)] + list(state["messages"])
        response: AIMessage = llm.invoke(messages)
        # Return to executor — executor will see current_step >= len(plan) and end.
        return Command(goto="executor", update={"messages": [response]})

    return general_agent_node
