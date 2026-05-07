"""AgentForPaper — LangGraph multi-agent supervisor graph.

Architecture:
    START → supervisor → [paper_search | paper_analyze | graph_agent | profile] → supervisor
                      ↘ END  (when supervisor decides the task is complete)

The supervisor reads SOUL.md as its system prompt and uses structured output
(RouteDecision) to decide which sub-agent to delegate to next.
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
        temperature=0.3,
    )


# ── Supervisor routing ─────────────────────────────────────────────────────────

_SOUL_PATH = Path(__file__).parents[3] / "workspace" / "SOUL.md"
_SOUL_FALLBACK = (
    "You are AgentForPaper, a personal AI research assistant specialising in "
    "academic papers. Help researchers find, understand, and connect papers.\n"
    "Always cite sources. Match the user's language (Chinese or English)."
)

_ROUTE_INSTRUCTIONS = """
You are the supervisor of a multi-agent research assistant.
Based on the conversation, decide which specialist agent should handle the next step:

- general: User is greeting, chatting, asking about you, or the request is NOT about papers.
           Also use this when the last agent already gave a complete answer and the user
           says something like "谢谢" or "好的".
- paper_search: User wants to FIND or DISCOVER papers on a topic.
- paper_analyze: User wants to UNDERSTAND or deep-dive a specific paper (by title or arXiv ID).
- graph_agent: User wants to BUILD or QUERY a citation/influence graph.
- profile: User explicitly asks to update/view their research profile or reading list.
- FINISH: A sub-agent just responded and the conversation is clearly complete.
          Use this ONLY after a sub-agent has already answered — never on the first turn.

Respond ONLY with a RouteDecision JSON object.
"""


class RouteDecision(BaseModel):
    """Routing decision from the supervisor."""

    next: Literal["general", "paper_search", "paper_analyze", "graph_agent", "profile", "FINISH"]
    reasoning: str


def _load_soul() -> str:
    if _SOUL_PATH.exists():
        return _SOUL_PATH.read_text(encoding="utf-8")
    return _SOUL_FALLBACK


def make_supervisor_node(llm: ChatOpenAI):
    """Return the supervisor node function."""
    soul = _load_soul()
    system_prompt = soul + "\n\n" + _ROUTE_INSTRUCTIONS
    router_llm = llm.with_structured_output(RouteDecision)

    def supervisor(
        state: State,
    ) -> Command[Literal["general", "paper_search", "paper_analyze", "graph_agent", "profile", "__end__"]]:
        """Route to the appropriate sub-agent or finish."""
        messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
        decision: RouteDecision = router_llm.invoke(messages)

        if decision.next == "FINISH":
            return Command(goto=END)

        return Command(goto=decision.next)

    return supervisor


# ── Build the graph ────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """Compile and return the AgentForPaper supervisor graph."""
    llm = _get_llm()

    supervisor_node      = make_supervisor_node(llm)
    general_node         = make_general_agent_node(llm)
    paper_search_node    = make_paper_search_node(llm)
    paper_analyze_node   = make_paper_analyze_node(llm)
    graph_agent_node     = make_graph_agent_node(llm)
    profile_agent_node   = make_profile_agent_node(llm)

    builder = StateGraph(State, input=InputState)

    builder.add_node("supervisor",     supervisor_node)
    builder.add_node("general",        general_node)
    builder.add_node("paper_search",   paper_search_node)
    builder.add_node("paper_analyze",  paper_analyze_node)
    builder.add_node("graph_agent",    graph_agent_node)
    builder.add_node("profile",        profile_agent_node)

    builder.add_edge(START, "supervisor")

    # Sub-agents route back to supervisor via Command(goto="supervisor") — no
    # explicit edges needed; LangGraph follows the Command.goto at runtime.

    return builder.compile(name="AgentForPaper").with_config(
        {"recursion_limit": 20}  # max 20 node hops per request (prevents runaway loops)
    )


# Top-level ``graph`` object referenced by langgraph.json
graph = build_graph()
