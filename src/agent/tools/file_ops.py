"""File operation tools for AgentForPaper.

Reads and writes user profile (USER.md) and paper analysis files
in the local workspace directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.tools import tool

_DEFAULT_USER_MD = """\
# User Research Profile

## Research Interests
(Not set yet — tell me your research directions and I'll fill this in.)

## Current Focus
(Not set)

## Preferred Venues
(Not set)

## Already Read Papers
(None recorded yet)

## Preferences
- Response language: Chinese (default) / English
- Detail level: brief summaries / in-depth analysis
- Recommendation style: latest papers first / foundational first
(Not set — defaults used)
"""


def _workspace() -> Path:
    base = Path(os.getenv("WORKSPACE_DIR", Path.home() / ".agentforpaper"))
    base.mkdir(parents=True, exist_ok=True)
    return base


@tool
def read_user_profile() -> str:
    """Read the user's research profile from USER.md.

    Returns the full contents of USER.md, which contains the user's research
    interests, already-read papers, preferred venues, and preferences.
    Always call this at the start of a session to personalise responses.
    """
    profile_path = _workspace() / "USER.md"
    if not profile_path.exists():
        profile_path.write_text(_DEFAULT_USER_MD, encoding="utf-8")
    return profile_path.read_text(encoding="utf-8")


@tool
def write_user_profile(content: str) -> str:
    """Overwrite the user's research profile (USER.md) with new content.

    Args:
        content: Full new content for USER.md (must preserve Markdown structure).

    Returns:
        Confirmation message.
    """
    profile_path = _workspace() / "USER.md"
    profile_path.write_text(content, encoding="utf-8")
    return f"User profile saved to {profile_path}"


@tool
def write_analysis(arxiv_id: str, content: str) -> str:
    """Save a paper analysis to a local Markdown file.

    Args:
        arxiv_id: arXiv ID used as the filename, e.g. '2412.03603'.
                  If the paper has no arXiv ID, use a slug like 'hunyuan-video-2024'.
        content: Full Markdown content of the analysis.

    Returns:
        Path where the analysis was saved.
    """
    papers_dir = _workspace() / "papers"
    papers_dir.mkdir(parents=True, exist_ok=True)
    slug = arxiv_id.lower().removeprefix("arxiv:").strip().replace("/", "-")
    out_path = papers_dir / f"{slug}.md"
    out_path.write_text(content, encoding="utf-8")
    return f"Analysis saved to {out_path}"


@tool
def read_analysis(arxiv_id: str) -> str:
    """Read a previously saved paper analysis.

    Args:
        arxiv_id: arXiv ID or slug used when the analysis was saved.

    Returns:
        Contents of the saved analysis file, or a not-found message.
    """
    papers_dir = _workspace() / "papers"
    slug = arxiv_id.lower().removeprefix("arxiv:").strip().replace("/", "-")
    out_path = papers_dir / f"{slug}.md"
    if not out_path.exists():
        return f"No saved analysis for '{arxiv_id}'. Use the paper_analyze agent to create one."
    return out_path.read_text(encoding="utf-8")
