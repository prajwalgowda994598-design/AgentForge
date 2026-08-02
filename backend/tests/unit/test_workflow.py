"""
Unit tests for LangGraph workflow routing logic.
Tests the conditional edge and workflow state management.
"""

from unittest.mock import AsyncMock, patch

import pytest


class TestWorkflowRouting:
    """Tests for the LangGraph conditional edge and workflow structure."""

    def test_route_after_critic_retry(self):
        """Should route to researcher when should_retry is True."""
        from agentforge.backend.graph.workflow import route_after_critic

        state = {"should_retry": True, "critic_score": 0.4, "iteration": 1}
        result = route_after_critic(state)
        assert result == "researcher"

    def test_route_after_critic_pass(self):
        """Should route to fact_checker when should_retry is False."""
        from agentforge.backend.graph.workflow import route_after_critic

        state = {"should_retry": False, "critic_score": 0.85, "iteration": 1}
        result = route_after_critic(state)
        assert result == "fact_checker"

    def test_route_after_critic_default_no_retry(self):
        """Default (no should_retry key) should proceed to fact_checker."""
        from agentforge.backend.graph.workflow import route_after_critic

        state = {}
        result = route_after_critic(state)
        assert result == "fact_checker"

    def test_build_research_graph_compiles(self):
        """Graph should compile without errors."""
        from agentforge.backend.graph.workflow import build_research_graph

        graph = build_research_graph()
        assert graph is not None

    def test_get_research_graph_is_singleton(self):
        """get_research_graph should return the same object on repeated calls."""
        from agentforge.backend.graph import workflow

        # Reset singleton
        workflow._compiled_graph = None

        g1 = workflow.get_research_graph()
        g2 = workflow.get_research_graph()
        assert g1 is g2


class TestWorkflowState:
    """Tests for WorkflowState TypedDict and initial state construction."""

    def test_initial_state_has_required_keys(self):
        """Workflow initial state should contain all mandatory keys."""
        import uuid
        from agentforge.backend.graph.workflow import WorkflowState

        state: WorkflowState = {
            "session_id": str(uuid.uuid4()),
            "query": "Test question",
            "top_k": 5,
            "iteration": 0,
            "agent_status": {},
            "agent_timings": {},
            "retrieved_chunks": [],
            "web_snippets": [],
        }

        assert "query" in state
        assert state["iteration"] == 0
        assert state["retrieved_chunks"] == []


class TestCriticExtractJson:
    """Tests for the JSON extraction utility in the critic agent."""

    def test_extract_valid_json(self):
        from agentforge.backend.agents.critic_agent import _extract_json

        result = _extract_json('{"score": 0.8, "verdict": "pass", "reasoning": "good", "gaps": [], "suggestions": []}')
        assert result["score"] == 0.8
        assert result["verdict"] == "pass"

    def test_extract_json_from_prose(self):
        from agentforge.backend.agents.critic_agent import _extract_json

        text = 'Here is my evaluation: {"score": 0.6, "verdict": "fail", "reasoning": "needs work", "gaps": ["depth"], "suggestions": ["add more"]}'
        result = _extract_json(text)
        assert result["score"] == 0.6

    def test_extract_json_fallback(self):
        from agentforge.backend.agents.critic_agent import _extract_json

        result = _extract_json("This is not JSON at all.")
        assert "score" in result
        assert result["verdict"] == "fail"  # safe default
