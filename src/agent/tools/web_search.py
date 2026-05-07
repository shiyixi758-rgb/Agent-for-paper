"""Web search tool for AgentForPaper.

Uses DuckDuckGo (no API key required) via langchain-community.
"""

from __future__ import annotations

from langchain_community.tools import DuckDuckGoSearchRun

web_search = DuckDuckGoSearchRun(
    name="web_search",
    description=(
        "Search the web for recent papers, conference proceedings, or research news. "
        "Useful for finding papers on arXiv, OpenReview, or top-venue websites. "
        "Input: a search query string. "
        "Example: 'video generation diffusion model CVPR 2024 arxiv'"
    ),
)
