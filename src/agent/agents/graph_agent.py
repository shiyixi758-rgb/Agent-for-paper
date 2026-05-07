"""Research evolution graph sub-agent.

Builds and queries citation/influence graphs showing how research ideas evolved.
Uses build_graph_from_knowledge (preferred) for no-rate-limit graph building.
Skill prompt loaded from skills/evolution_graph/SKILL.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent.tools.paper_graph import (
    build_graph_from_knowledge,
    list_graphs,
    query_graph,
)

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from agent.state import State

_SKILL_PATH = Path(__file__).parents[4] / "skills" / "evolution_graph" / "SKILL.md"
_FALLBACK_PROMPT = (
    "You are an expert at building research paper evolution graphs. "
    "Use build_graph_from_knowledge with paper_ids and edges based on your knowledge "
    "of citation relationships. After building, use query_graph with query_type='influential' "
    "to show the most important papers. Always report the HTML path so the user can view it."
)


def _load_skill_prompt() -> str:
    if _SKILL_PATH.exists():
        return _SKILL_PATH.read_text(encoding="utf-8")
    return _FALLBACK_PROMPT


def make_graph_agent_node(llm: "BaseChatModel"):
    """Return a graph node function for the evolution graph sub-agent."""
    skill_prompt = _load_skill_prompt()
    react_agent = create_react_agent(
        llm,
        tools=[build_graph_from_knowledge, query_graph, list_graphs],
        prompt=SystemMessage(content=skill_prompt),
    )

    def graph_agent_node(state: "State") -> Command:
        """Build or query evolution graph and return to supervisor."""
        result = react_agent.invoke(state)
        return Command(goto="executor", update={"messages": result["messages"]})

    return graph_agent_node
