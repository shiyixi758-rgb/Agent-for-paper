"""Paper analysis sub-agent.

Deep-dives into a single paper: problem, method, results, limitations.
Saves the analysis to a local Markdown file. Skill prompt from SKILL.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent.tools.arxiv import arxiv_fetch, arxiv_search
from agent.tools.file_ops import read_analysis, write_analysis
from agent.tools.web_search import web_search

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from agent.state import State

_SKILL_PATH = Path(__file__).parents[4] / "skills" / "paper_analyze" / "SKILL.md"
_FALLBACK_PROMPT = (
    "You are an expert at deep paper analysis. "
    "Given a paper (by arXiv ID or title), fetch it with arxiv_fetch, "
    "produce a structured analysis covering: Problem & Motivation, Key Method, "
    "Main Contributions, Experiments & Results, Limitations & Future Work, "
    "and My Assessment. Save the result with write_analysis."
)


def _load_skill_prompt() -> str:
    if _SKILL_PATH.exists():
        return _SKILL_PATH.read_text(encoding="utf-8")
    return _FALLBACK_PROMPT


def make_paper_analyze_node(llm: "BaseChatModel"):
    """Return a graph node function for the paper analysis sub-agent."""
    skill_prompt = _load_skill_prompt()
    react_agent = create_react_agent(
        llm,
        tools=[arxiv_fetch, arxiv_search, web_search, write_analysis, read_analysis],
        prompt=SystemMessage(content=skill_prompt),
    )

    def paper_analyze_node(state: "State") -> Command:
        """Execute paper analysis and return to supervisor."""
        input_state = dict(state)
        if state.get("user_profile"):
            profile_note = SystemMessage(
                content=f"[User profile context]\n{state['user_profile']}"
            )
            input_state["messages"] = [profile_note] + list(state["messages"])

        result = react_agent.invoke(input_state)
        return Command(goto="executor", update={"messages": result["messages"]})

    return paper_analyze_node
