"""AgentForPaper — Plan-and-Execute multi-agent graph.

Architecture:
    START → planner → executor ──► agent_node → executor ──► agent_node → ... → END
                                   (picks plan[current_step])

The planner runs ONCE per user turn and produces an ordered list of agents.
The executor mechanically walks through the list — no LLM judgment needed
for termination. When current_step >= len(plan), the graph ends.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel

from agent.agents.general_agent import make_general_agent_node
from agent.agents.graph_agent import make_graph_agent_node
from agent.agents.paper_analyze import make_paper_analyze_node
from agent.agents.paper_search import make_paper_search_node
from agent.agents.profile_agent import make_profile_agent_node
from agent.state import InputState, State

# ── LLM configuration (Qwen via DashScope, OpenAI-compatible) ─────────────────

def _get_llm() -> ChatOpenAI:
    api_key = os.environ.get("DASHSCOPE_API_KEY", "")
    if not api_key or api_key == "your-dashscope-api-key-here":
        raise EnvironmentError(
            "DASHSCOPE_API_KEY is not set. "
            "Add it to your .env file: DASHSCOPE_API_KEY=sk-..."
        )
    return ChatOpenAI(
        model="qwen-plus",
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=0.2,
    )


# ── Planner ────────────────────────────────────────────────────────────────────

_SOUL_PATH = Path(__file__).parents[3] / "workspace" / "SOUL.md"
_SOUL_FALLBACK = (
    "You are AgentForPaper, a personal AI research assistant specialising in "
    "academic papers. Be friendly and helpful. Match the user's language."
)

_PLAN_INSTRUCTIONS = """
You are the planner for a multi-agent research assistant.
Given the user's latest request, produce an ORDERED list of specialist agents to call.

Available agents:
- general      : greetings, small talk, questions about you, anything NOT paper-related.
- profile      : load or update the user's research profile (USER.md).
                 Include as FIRST step when user_profile is empty AND the task is paper-related.
- paper_search : find / discover / recommend papers on a topic.
- paper_analyze: deep-dive analysis of a specific paper (by title or arXiv ID).
- graph_agent  : build or query a citation/influence evolution graph.

Rules:
- Respond ONLY with an ExecutionPlan JSON object.
- Keep the plan minimal — only include steps that are genuinely needed.
- For a simple greeting, plan = ["general"].
- For "find papers on X", plan = ["paper_search"]  (or ["profile","paper_search"] if profile empty).
- For "analyse paper X", plan = ["paper_analyze"].
- For "find and analyse", plan = ["paper_search", "paper_analyze"].
- For "build evolution graph", plan = ["graph_agent"].
- Never repeat the same agent twice in one plan.
"""


class ExecutionPlan(BaseModel):
    """Ordered execution plan produced by the planner."""

    steps: list[Literal["general", "profile", "paper_search", "paper_analyze", "graph_agent"]]
    reasoning: str


def _load_soul() -> str:
    if _SOUL_PATH.exists():
        return _SOUL_PATH.read_text(encoding="utf-8")
    return _SOUL_FALLBACK


def make_planner_node(llm: ChatOpenAI):
    """Return the planner node — runs once per user turn to set plan + current_step=0."""
    soul = _load_soul()
    system_prompt = soul + "\n\n" + _PLAN_INSTRUCTIONS
    plan_llm = llm.with_structured_output(ExecutionPlan)

    def planner(state: State) -> Command[Literal["executor"]]:
        """Produce an execution plan then hand off to the executor."""
        # Pass user_profile status in system prompt so planner knows whether to prepend "profile"
        profile_hint = (
            "[User profile is already loaded — do NOT include 'profile' in plan unless user explicitly asks to update it.]"
            if state.get("user_profile")
            else "[User profile is NOT loaded yet — prepend 'profile' to plan if task is paper-related.]"
        )
        messages = [
            SystemMessage(content=system_prompt + "\n" + profile_hint),
        ] + list(state["messages"])

        plan: ExecutionPlan = plan_llm.invoke(messages)

        return Command(
            goto="executor",
            update={
                "plan": plan.steps,
                "current_step": 0,
            },
        )

    return planner


# ── Executor ───────────────────────────────────────────────────────────────────

_AGENT_NAMES = Literal["general", "profile", "paper_search", "paper_analyze", "graph_agent"]


def executor(state: State) -> Command:
    """Pick the next agent from the plan, or end if all steps are done."""
    plan = state.get("plan", [])
    step = state.get("current_step", 0)

    if step >= len(plan):
        return Command(goto=END)

    next_agent = plan[step]
    return Command(
        goto=next_agent,
        update={"current_step": step + 1},
    )


# ── Build the graph ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Compile and return the AgentForPaper plan-and-execute graph."""
    llm = _get_llm()

    planner_node        = make_planner_node(llm)
    general_node        = make_general_agent_node(llm)
    paper_search_node   = make_paper_search_node(llm)
    paper_analyze_node  = make_paper_analyze_node(llm)
    graph_agent_node    = make_graph_agent_node(llm)
    profile_agent_node  = make_profile_agent_node(llm)

    builder = StateGraph(State, input=InputState)

    builder.add_node("planner",       planner_node)
    builder.add_node("executor",      executor)
    builder.add_node("general",       general_node)
    builder.add_node("paper_search",  paper_search_node)
    builder.add_node("paper_analyze", paper_analyze_node)
    builder.add_node("graph_agent",   graph_agent_node)
    builder.add_node("profile",       profile_agent_node)

    builder.add_edge(START, "planner")
    # executor → agent edges are handled by Command(goto=...) at runtime

    return builder.compile(name="AgentForPaper").with_config(
        {"recursion_limit": 25}
    )


# Top-level ``graph`` object referenced by langgraph.json
graph = build_graph()
