"""Paper search sub-agent.

Finds latest and foundational papers on any research topic.
Uses arXiv API + web search. Skill prompt loaded from skills/paper_search/SKILL.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent.tools.arxiv import arxiv_fetch, arxiv_search
from agent.tools.web_search import web_search

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from agent.state import State

_SKILL_PATH = Path(__file__).parents[4] / "skills" / "paper_search" / "SKILL.md"
_FALLBACK_PROMPT = (
    "You are a research paper search expert. "
    "Find relevant papers using arxiv_search and web_search. "
    "Always include verified arXiv links. "
    "Distinguish 'latest' from 'foundational' papers clearly."
)


def _load_skill_prompt() -> str:
    if _SKILL_PATH.exists():
        return _SKILL_PATH.read_text(encoding="utf-8")
    return _FALLBACK_PROMPT


def make_paper_search_node(llm: "BaseChatModel"):
    """Return a graph node function for the paper search sub-agent."""
    skill_prompt = _load_skill_prompt()
    react_agent = create_react_agent(
        llm,
        tools=[arxiv_search, arxiv_fetch, web_search],
        prompt=SystemMessage(content=skill_prompt),
    )

    def paper_search_node(state: "State") -> Command:
        """Execute paper search and return to supervisor."""
        # Inject user profile as context if available
        input_state = dict(state)
        if state.get("user_profile"):
            profile_note = SystemMessage(
                content=f"[User profile context]\n{state['user_profile']}"
            )
            input_state["messages"] = [profile_note] + list(state["messages"])

        result = react_agent.invoke(input_state)
        return Command(goto="supervisor", update={"messages": result["messages"]})

    return paper_search_node
