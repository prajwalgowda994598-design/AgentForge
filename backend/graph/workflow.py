"""
AgentForge – LangGraph Workflow Orchestrator
=============================================
Defines the multi-agent graph using LangGraph StateGraph.

Graph topology:
  START
    │
    ▼
  researcher  ◄──────────────────────────────────┐
    │                                             │ (retry if score < threshold)
    ▼                                             │
  summarizer                                      │
    │                                             │
    ▼                                             │
  critic ──── should_retry? ──── YES ─────────────┘
    │
    NO
    ▼
  fact_checker
    │
    ▼
  synthesizer
    │
    ▼
  END

Each node calls its corresponding agent's run() method.
The conditional edge after "critic" routes based on state["should_retry"].

The WorkflowState TypedDict defines all state keys passed between nodes.
"""

import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

from agentforge.backend.agents.critic_agent import CriticAgent
from agentforge.backend.agents.fact_checker_agent import FactCheckerAgent
from agentforge.backend.agents.researcher_agent import ResearcherAgent
from agentforge.backend.agents.summarizer_agent import SummarizerAgent
from agentforge.backend.agents.synthesizer_agent import SynthesizerAgent
from agentforge.backend.core.logging import get_logger

logger = get_logger(__name__)


# ── State Schema ───────────────────────────────────────────────────────────────

class WorkflowState(TypedDict, total=False):
    """
    Shared state dict passed between all agents in the graph.
    total=False means all keys are optional so partial updates are safe.
    """
    # Input
    session_id: str
    query: str
    top_k: int
    user_id: Optional[str]

    # Research stage
    retrieved_chunks: List[Dict[str, Any]]
    web_snippets: List[str]
    raw_context: str
    refined_research: str

    # Summary stage
    summary: str

    # Critic stage
    critic_score: float
    critic_feedback: Dict[str, Any]
    should_retry: bool
    iteration: int

    # Fact-check stage
    verified_summary: str

    # Synthesis stage
    final_answer: str
    sources: List[Dict[str, Any]]

    # Metadata
    agent_status: Dict[str, str]
    agent_timings: Dict[str, int]
    error: Optional[str]

    # Status callbacks (not serialised — runtime only)
    status_callback: Optional[Callable]


# ── Conditional Edge ───────────────────────────────────────────────────────────

def route_after_critic(state: WorkflowState) -> Literal["researcher", "fact_checker"]:
    """
    LangGraph conditional edge:
    If critic says retry → go back to researcher.
    Otherwise → move to fact_checker.
    """
    if state.get("should_retry", False):
        logger.info(
            "workflow_routing_retry",
            score=state.get("critic_score"),
            iteration=state.get("iteration"),
        )
        return "researcher"
    return "fact_checker"


# ── Node Wrappers ──────────────────────────────────────────────────────────────

def _make_node(agent_class, status_name: str):
    """
    Factory that creates a LangGraph node function for a given agent class.

    Agent is instantiated lazily on first invocation so the server can start
    without a valid API key configured — the error only surfaces when a query
    is actually submitted.
    """
    _agent_cache: list = []   # single-element cache; list so closure can mutate it

    async def node_fn(state: WorkflowState) -> WorkflowState:
        # Build the agent on first call (lazy) so startup never touches the LLM key
        if not _agent_cache:
            _agent_cache.append(agent_class())

        agent = _agent_cache[0]

        # Fire live status update if callback is registered
        callback = state.get("status_callback")
        if callback:
            try:
                await callback(
                    session_id=state.get("session_id", ""),
                    agent_name=status_name,
                    status="running",
                )
            except Exception:
                pass  # never let callback failures break the graph

        result = await agent.run(state)

        if callback:
            try:
                await callback(
                    session_id=state.get("session_id", ""),
                    agent_name=status_name,
                    status="completed",
                )
            except Exception:
                pass

        return result

    node_fn.__name__ = status_name
    return node_fn


# ── Graph Builder ──────────────────────────────────────────────────────────────

def build_research_graph() -> StateGraph:
    """
    Construct and compile the research workflow graph.
    Returns a compiled LangGraph that can be invoked or streamed.
    """
    graph = StateGraph(WorkflowState)

    # Register agent nodes
    graph.add_node("researcher",   _make_node(ResearcherAgent,  "researcher"))
    graph.add_node("summarizer",   _make_node(SummarizerAgent,  "summarizer"))
    graph.add_node("critic",       _make_node(CriticAgent,      "critic"))
    graph.add_node("fact_checker", _make_node(FactCheckerAgent, "fact_checker"))
    graph.add_node("synthesizer",  _make_node(SynthesizerAgent, "synthesizer"))

    # Linear edges
    graph.add_edge(START,          "researcher")
    graph.add_edge("researcher",   "summarizer")
    graph.add_edge("summarizer",   "critic")

    # Conditional edge — critic decides to retry or proceed
    graph.add_conditional_edges(
        "critic",
        route_after_critic,
        {
            "researcher":   "researcher",   # retry path
            "fact_checker": "fact_checker", # pass path
        },
    )

    graph.add_edge("fact_checker", "synthesizer")
    graph.add_edge("synthesizer",  END)

    return graph.compile()


# Module-level compiled graph singleton
_compiled_graph = None


def get_research_graph():
    """Return the compiled LangGraph (lazy-initialised singleton)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_research_graph()
        logger.info("langgraph_workflow_compiled")
    return _compiled_graph


# ── Public Workflow Runner ─────────────────────────────────────────────────────

async def run_research_workflow(
    query: str,
    session_id: Optional[str] = None,
    top_k: int = 5,
    user_id: Optional[str] = None,
    status_callback: Optional[Callable] = None,
) -> WorkflowState:
    """
    Execute the full multi-agent research pipeline.

    Args:
        query:           The user's research question.
        session_id:      UUID string for this session (auto-generated if None).
        top_k:           Number of FAISS results to retrieve.
        user_id:         Authenticated user identifier.
        status_callback: Async callable(session_id, agent_name, status) for WS.

    Returns:
        The final WorkflowState after all agents have run.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    initial_state: WorkflowState = {
        "session_id": session_id,
        "query": query,
        "top_k": top_k,
        "user_id": user_id,
        "iteration": 0,
        "agent_status": {},
        "agent_timings": {},
        "retrieved_chunks": [],
        "web_snippets": [],
        "status_callback": status_callback,
    }

    logger.info("workflow_started", session_id=session_id, query_preview=query[:80])

    graph = get_research_graph()
    final_state: WorkflowState = await graph.ainvoke(initial_state)

    logger.info(
        "workflow_completed",
        session_id=session_id,
        critic_score=final_state.get("critic_score"),
        iterations=final_state.get("iteration"),
    )

    return final_state
