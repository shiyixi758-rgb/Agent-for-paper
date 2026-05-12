"""AgentForPaper — Supervisor multi-agent graph.

Uses the official langgraph-supervisor library.

Architecture:
    START → date_injector → supervisor_subgraph → END

    supervisor_subgraph (Tool-Calling Supervisor):
      ├── transfer_to_paper_search_expert  → paper_search_expert (ReAct)
      ├── transfer_to_paper_analyze_expert → paper_analyze_expert (ReAct)
      ├── transfer_to_graph_expert         → graph_expert (ReAct)
      └── transfer_to_profile_expert       → profile_expert (ReAct)

date_injector: Injects the current date at runtime so the LLM correctly
interprets relative time expressions like "近两个月" or "latest papers".
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from langgraph_supervisor import create_supervisor

from agent.state import InputState
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


# ── Skill / soul loaders ───────────────────────────────────────────────────────

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


# ── Date injector node ────────────────────────────────────────────────────────
# Injects the real-time current date so relative expressions ("近两个月",
# "latest", "recent 2025") are interpreted correctly on every request.

def date_injector(state: MessagesState) -> Command[Literal["supervisor"]]:
    """Prepend the current date as a SystemMessage before routing to supervisor."""
    today = datetime.now().strftime("%Y-%m-%d")
    content = (
        f"[System] Today is {today}. "
        "For ALL time-relative expressions in the user's request "
        "('recent', 'latest', 'last 2 months', 'past year', "
        "'zui xin', 'jin liang ge yue', etc.), "
        "use THIS date as 'now'. Do NOT rely on your training data cutoff."
    )
    # Stable id prevents multiple date messages accumulating across turns.
    date_msg = SystemMessage(content=content, id="__date_context__")
    return Command(goto="supervisor", update={"messages": [date_msg]})


# ── Supervisor prompt ──────────────────────────────────────────────────────────

_SUPERVISOR_INSTRUCTIONS = """
You coordinate a team of specialist research agents. Delegate tasks using the
transfer tools — never answer paper-related questions yourself.

Delegation rules:
- paper_search_expert : find / recommend / discover papers on a topic.
- paper_analyze_expert: deep-dive analysis of a specific paper (by title or ID).
- graph_expert        : build or query a citation / influence evolution graph.
- profile_expert      : ONLY when the user explicitly asks to view or update
                        their research profile or reading list.

For greetings or off-topic questions, respond directly without delegating.
After a specialist agent responds, decide if more steps are needed or summarise
and finish. Do NOT call the same agent twice in a row.
"""


# ── Build graph ────────────────────────────────────────────────────────────────

def build_graph():
    """Compile and return the AgentForPaper graph with date injection."""
    llm = _get_llm()

    # paper_search_expert: also has read_user_profile so it can personalise
    # results without an explicit supervisor → profile round-trip.
    paper_search_agent = create_react_agent(
        llm,
        tools=[arxiv_search, arxiv_fetch, web_search, read_user_profile],
        name="paper_search_expert",
        prompt=SystemMessage(content=_skill("paper_search")),
    )

    # paper_analyze_expert: same — loads profile to connect paper to user context.
    paper_analyze_agent = create_react_agent(
        llm,
        tools=[arxiv_fetch, arxiv_search, web_search,
               write_analysis, read_analysis, read_user_profile],
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

    supervisor_workflow = create_supervisor(
        agents=[paper_search_agent, paper_analyze_agent, graph_agent, profile_agent],
        model=_get_llm(temperature=0.0),
        prompt=_soul() + "\n\n" + _SUPERVISOR_INSTRUCTIONS,
        output_mode="last_message",
        add_handoff_messages=True,
    )
    supervisor_subgraph = supervisor_workflow.compile(name="supervisor")

    # Outer wrapper: date_injector → supervisor_subgraph
    outer = StateGraph(MessagesState, input=InputState)
    outer.add_node("date_injector", date_injector)
    outer.add_node("supervisor", supervisor_subgraph)
    outer.add_edge(START, "date_injector")
    # date_injector returns Command(goto="supervisor"), no explicit edge needed
    outer.add_edge("supervisor", END)

    return outer.compile(name="AgentForPaper")


# Top-level ``graph`` object referenced by langgraph.json
graph = build_graph()
