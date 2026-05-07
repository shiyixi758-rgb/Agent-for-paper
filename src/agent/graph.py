"""AgentForPaper — Supervisor multi-agent graph.

Uses the official langgraph-supervisor library.
The supervisor dispatches to specialist agents via tool calling (not structured
output routing), which is significantly more stable and battle-tested.

Architecture:
    Supervisor (tool-calling LLM)
      ├── transfer_to_paper_search_expert  → paper_search_expert (ReAct)
      ├── transfer_to_paper_analyze_expert → paper_analyze_expert (ReAct)
      ├── transfer_to_graph_expert         → graph_expert (ReAct)
      └── transfer_to_profile_expert       → profile_expert (ReAct)

Error isolation: Each ReAct agent catches tool errors internally and returns
them as messages, so a failing tool never crashes the supervisor.
"""

from __future__ import annotations

import os
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph_supervisor import create_supervisor

from agent.tools.arxiv import arxiv_fetch, arxiv_search
from agent.tools.file_ops import (
    read_analysis,
    read_user_profile,
    write_analysis,
    write_user_profile,
)
from agent.tools.paper_graph import build_graph_from_knowledge, list_graphs, query_graph
from agent.tools.web_search import web_search

# ── LLM ───────────────────────────────────────────────────────────────────────

def _get_llm(temperature: float = 0.2) -> ChatOpenAI:
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key or api_key == "your-dashscope-api-key-here":
        raise EnvironmentError(
            "DASHSCOPE_API_KEY is not set. Add it to your .env file."
        )
    return ChatOpenAI(
        model="qwen-plus",
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=temperature,
    )


# ── Skill prompt loader ────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).parents[3]


def _skill(name: str) -> str:
    path = _REPO_ROOT / "skills" / name / "SKILL.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are a specialist agent for {name}. Be helpful and precise."


def _soul() -> str:
    path = _REPO_ROOT / "workspace" / "SOUL.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return (
        "You are AgentForPaper, a personal AI research assistant specialising in "
        "academic papers. Match the user's language (Chinese or English)."
    )


# ── Supervisor prompt ──────────────────────────────────────────────────────────

_SUPERVISOR_INSTRUCTIONS = """
You coordinate a team of specialist research agents. Delegate tasks using the
transfer tools — never answer paper-related questions yourself.

Delegation rules:
- paper_search_expert : find / recommend papers on a topic
- paper_analyze_expert: deep-dive analysis of a specific paper
- graph_expert        : build or query a citation evolution graph
- profile_expert      : load or update the user's research profile (USER.md)
                        → call this FIRST on the initial turn before paper tasks

For greetings or off-topic questions, respond directly without delegating.
After a specialist agent responds, decide if more steps are needed or summarise
and finish. Do NOT call the same agent twice in a row.
"""


# ── Build graph ────────────────────────────────────────────────────────────────

def build_graph():
    """Compile and return the AgentForPaper supervisor graph."""
    llm = _get_llm()

    paper_search_agent = create_react_agent(
        llm,
        tools=[arxiv_search, arxiv_fetch, web_search],
        name="paper_search_expert",
        prompt=SystemMessage(content=_skill("paper_search")),
    )

    paper_analyze_agent = create_react_agent(
        llm,
        tools=[arxiv_fetch, arxiv_search, web_search, write_analysis, read_analysis],
        name="paper_analyze_expert",
        prompt=SystemMessage(content=_skill("paper_analyze")),
    )

    graph_agent = create_react_agent(
        llm,
        tools=[build_graph_from_knowledge, query_graph, list_graphs],
        name="graph_expert",
        prompt=SystemMessage(content=_skill("evolution_graph")),
    )

    profile_agent = create_react_agent(
        llm,
        tools=[read_user_profile, write_user_profile],
        name="profile_expert",
        prompt=SystemMessage(content=_skill("user_profile")),
    )

    workflow = create_supervisor(
        agents=[paper_search_agent, paper_analyze_agent, graph_agent, profile_agent],
        model=_get_llm(temperature=0.0),  # deterministic routing
        prompt=_soul() + "\n\n" + _SUPERVISOR_INSTRUCTIONS,
        output_mode="last_message",  # keep history clean: return only final response
        add_handoff_messages=True,   # show handoff steps in Studio for debugging
    )

    return workflow.compile(name="AgentForPaper")


# Top-level ``graph`` object referenced by langgraph.json
graph = build_graph()
