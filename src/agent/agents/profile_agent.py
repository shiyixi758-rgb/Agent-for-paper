"""User profile sub-agent.

Reads and updates USER.md: research interests, read papers, preferences.
Skill prompt loaded from skills/user_profile/SKILL.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from langchain_core.messages import SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent.tools.file_ops import read_user_profile, write_user_profile

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from agent.state import State

_SKILL_PATH = Path(__file__).parents[4] / "skills" / "user_profile" / "SKILL.md"
_FALLBACK_PROMPT = (
    "You manage the user's research profile stored in USER.md. "
    "Use read_user_profile to load it at session start. "
    "Use write_user_profile to update it when the user mentions new interests, "
    "reads a new paper, or updates preferences. Always confirm before writing."
)


def _load_skill_prompt() -> str:
    if _SKILL_PATH.exists():
        return _SKILL_PATH.read_text(encoding="utf-8")
    return _FALLBACK_PROMPT


def make_profile_agent_node(llm: "BaseChatModel"):
    """Return a graph node function for the profile management sub-agent."""
    skill_prompt = _load_skill_prompt()
    react_agent = create_react_agent(
        llm,
        tools=[read_user_profile, write_user_profile],
        prompt=SystemMessage(content=skill_prompt),
    )

    def profile_agent_node(state: "State") -> Command:
        """Read or update user profile and return to supervisor.

        Also propagates the loaded profile into state so other agents can see it.
        """
        result = react_agent.invoke(state)
        # Extract profile text from the last tool result if available
        new_profile = state.get("user_profile", "")
        for msg in reversed(result["messages"]):
            if hasattr(msg, "content") and "Research Interests" in (msg.content or ""):
                new_profile = msg.content
                break
        return Command(
            goto="supervisor",
            update={"messages": result["messages"], "user_profile": new_profile},
        )

    return profile_agent_node
