"""
Unit tests for AgentForge agents.

Tests use mocked LLM and FAISS store so no API keys or
real network access are needed.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Researcher Agent ──────────────────────────────────────────────────────────

class TestResearcherAgent:
    """Tests for the Researcher agent."""

    @pytest.mark.asyncio
    async def test_researcher_uses_faiss_results(self, sample_state, mock_vector_store):
        """Researcher should populate retrieved_chunks from FAISS."""
        from agentforge.backend.agents.researcher_agent import ResearcherAgent

        agent = ResearcherAgent()

        with patch(
            "agentforge.backend.agents.researcher_agent.get_vector_store",
            new_callable=AsyncMock,
            return_value=mock_vector_store,
        ), patch.object(agent, "_call_llm", new_callable=AsyncMock, return_value="Key facts extracted."):
            result = await agent._execute(sample_state)

        assert "retrieved_chunks" in result
        assert result["agent_status"]["researcher"] == "completed"

    @pytest.mark.asyncio
    async def test_researcher_handles_empty_faiss(self, sample_state):
        """Researcher should not crash when FAISS returns no results."""
        from agentforge.backend.agents.researcher_agent import ResearcherAgent

        empty_store = AsyncMock()
        empty_store.similarity_search = AsyncMock(return_value=[])

        agent = ResearcherAgent()

        with patch(
            "agentforge.backend.agents.researcher_agent.get_vector_store",
            new_callable=AsyncMock,
            return_value=empty_store,
        ), patch.object(agent, "_call_llm", new_callable=AsyncMock, return_value="No context found."):
            result = await agent._execute(sample_state)

        assert result["retrieved_chunks"] == []
        assert "raw_context" in result

    @pytest.mark.asyncio
    async def test_researcher_refined_research_written_to_state(self, sample_state, mock_vector_store):
        """refined_research key must be set in result state."""
        from agentforge.backend.agents.researcher_agent import ResearcherAgent

        agent = ResearcherAgent()

        with patch(
            "agentforge.backend.agents.researcher_agent.get_vector_store",
            new_callable=AsyncMock,
            return_value=mock_vector_store,
        ), patch.object(agent, "_call_llm", new_callable=AsyncMock, return_value="Refined output."):
            result = await agent._execute(sample_state)

        assert result["refined_research"] == "Refined output."


# ── Summarizer Agent ──────────────────────────────────────────────────────────

class TestSummarizerAgent:
    @pytest.mark.asyncio
    async def test_summarizer_produces_summary(self, sample_state):
        """Summarizer should write summary to state."""
        state = {
            **sample_state,
            "refined_research": "Key facts: quantum computers use qubits.",
        }
        from agentforge.backend.agents.summarizer_agent import SummarizerAgent

        agent = SummarizerAgent()
        with patch.object(agent, "_call_llm", new_callable=AsyncMock,
                          return_value="## Key Findings\n- Quantum computers use qubits."):
            result = await agent._execute(state)

        assert "summary" in result
        assert result["agent_status"]["summarizer"] == "completed"

    @pytest.mark.asyncio
    async def test_summarizer_handles_empty_research(self, sample_state):
        """Summarizer should gracefully handle missing research context."""
        from agentforge.backend.agents.summarizer_agent import SummarizerAgent

        agent = SummarizerAgent()
        result = await agent._execute(sample_state)

        assert "summary" in result
        assert "Insufficient" in result["summary"]

    @pytest.mark.asyncio
    async def test_summarizer_passthrough_preserves_state_keys(self, sample_state):
        """All existing state keys must survive through summarizer."""
        state = {**sample_state, "refined_research": "Some research content about AI."}
        from agentforge.backend.agents.summarizer_agent import SummarizerAgent

        agent = SummarizerAgent()
        with patch.object(agent, "_call_llm", new_callable=AsyncMock, return_value="Summary text."):
            result = await agent._execute(state)

        assert result["query"] == sample_state["query"]
        assert result["session_id"] == sample_state["session_id"]


# ── Critic Agent ──────────────────────────────────────────────────────────────

class TestCriticAgent:
    @pytest.mark.asyncio
    async def test_critic_passes_high_score(self, sample_state):
        """Critic should not retry when score ≥ threshold."""
        state = {
            **sample_state,
            "summary": "Comprehensive answer about quantum computing with citations.",
        }
        from agentforge.backend.agents.critic_agent import CriticAgent

        agent = CriticAgent()
        with patch.object(agent, "_call_llm", new_callable=AsyncMock,
                          return_value='{"score": 0.85, "verdict": "pass", "reasoning": "Good answer", "gaps": [], "suggestions": []}'):
            result = await agent._execute(state)

        assert result["critic_score"] == 0.85
        assert result["should_retry"] is False

    @pytest.mark.asyncio
    async def test_critic_retries_low_score(self, sample_state):
        """Critic should flag retry when score < threshold."""
        state = {**sample_state, "summary": "Vague answer."}
        from agentforge.backend.agents.critic_agent import CriticAgent

        agent = CriticAgent()
        with patch.object(agent, "_call_llm", new_callable=AsyncMock,
                          return_value='{"score": 0.4, "verdict": "fail", "reasoning": "Too vague", "gaps": ["missing details"], "suggestions": ["add specifics"]}'):
            result = await agent._execute(state)

        assert result["critic_score"] == 0.4
        assert result["should_retry"] is True

    @pytest.mark.asyncio
    async def test_critic_forces_pass_at_max_iterations(self, sample_state):
        """Critic must not retry when max iterations is reached."""
        from agentforge.backend.core.config import settings
        state = {
            **sample_state,
            "summary": "Vague answer.",
            "iteration": settings.MAX_RESEARCH_ITERATIONS,
        }
        from agentforge.backend.agents.critic_agent import CriticAgent

        agent = CriticAgent()
        result = await agent._execute(state)

        assert result["should_retry"] is False
        assert result["critic_score"] == settings.CRITIC_PASS_THRESHOLD

    @pytest.mark.asyncio
    async def test_critic_increments_iteration(self, sample_state):
        """Critic should increment the iteration counter."""
        state = {**sample_state, "summary": "Some summary.", "iteration": 1}
        from agentforge.backend.agents.critic_agent import CriticAgent

        agent = CriticAgent()
        with patch.object(agent, "_call_llm", new_callable=AsyncMock,
                          return_value='{"score": 0.8, "verdict": "pass", "reasoning": "ok", "gaps": [], "suggestions": []}'):
            result = await agent._execute(state)

        assert result["iteration"] == 2


# ── Fact Checker Agent ────────────────────────────────────────────────────────

class TestFactCheckerAgent:
    @pytest.mark.asyncio
    async def test_fact_checker_processes_summary(self, sample_state):
        """Fact checker should produce verified_summary."""
        state = {
            **sample_state,
            "summary": "Quantum computers use qubits [Source: quantum_computing.txt].",
            "retrieved_chunks": [
                {"title": "QC", "source": "file.txt", "content": "qubits info", "score": 0.9}
            ],
            "web_snippets": [],
        }
        from agentforge.backend.agents.fact_checker_agent import FactCheckerAgent

        agent = FactCheckerAgent()
        with patch.object(agent, "_call_llm", new_callable=AsyncMock,
                          return_value="[VERIFIED] Quantum computers use qubits."):
            result = await agent._execute(state)

        assert "verified_summary" in result
        assert result["agent_status"]["fact_checker"] == "completed"

    @pytest.mark.asyncio
    async def test_fact_checker_handles_missing_summary(self, sample_state):
        """Fact checker should gracefully handle absent summary."""
        from agentforge.backend.agents.fact_checker_agent import FactCheckerAgent

        agent = FactCheckerAgent()
        result = await agent._execute(sample_state)

        assert result["verified_summary"] == "No summary available to fact-check."
        assert result["agent_status"]["fact_checker"] == "completed"


# ── Synthesizer Agent ─────────────────────────────────────────────────────────

class TestSynthesizerAgent:
    @pytest.mark.asyncio
    async def test_synthesizer_produces_final_answer(self, sample_state):
        """Synthesizer should write final_answer and sources to state."""
        state = {
            **sample_state,
            "verified_summary": "Verified content about quantum computing.",
            "critic_score": 0.85,
            "critic_feedback": {"gaps": []},
            "retrieved_chunks": [
                {"title": "QC Basics", "source": "qc.txt", "score": 0.9}
            ],
        }
        from agentforge.backend.agents.synthesizer_agent import SynthesizerAgent

        agent = SynthesizerAgent()
        with patch.object(agent, "_call_llm", new_callable=AsyncMock,
                          return_value="# Quantum Computing\n\n## Answer\nDetailed answer here."):
            result = await agent._execute(state)

        assert "final_answer" in result
        assert "sources" in result
        assert result["agent_status"]["synthesizer"] == "completed"
        assert len(result["sources"]) == 1
        assert result["sources"][0]["title"] == "QC Basics"


# ── Network Failure Handling ──────────────────────────────────────────────────

class TestNetworkFailures:
    """
    Verify that transient network errors are caught, logged, and converted
    into clean AgentExecutionError instances rather than crashing the pipeline.
    """

    @pytest.mark.asyncio
    async def test_llm_connect_error_raises_agent_execution_error(self, sample_state):
        """httpx.ConnectError from the LLM call must become AgentExecutionError."""
        import httpx
        from agentforge.backend.agents.summarizer_agent import SummarizerAgent
        from agentforge.backend.core.exceptions import AgentExecutionError

        state = {**sample_state, "refined_research": "Some research content."}
        agent = SummarizerAgent()

        with patch.object(
            agent, "_call_llm",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            with pytest.raises(AgentExecutionError) as exc_info:
                await agent.run(state)

        assert "summarizer" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_llm_timeout_raises_agent_execution_error(self, sample_state):
        """httpx.TimeoutException from the LLM call must become AgentExecutionError."""
        import httpx
        from agentforge.backend.agents.summarizer_agent import SummarizerAgent
        from agentforge.backend.core.exceptions import AgentExecutionError

        state = {**sample_state, "refined_research": "Some research content."}
        agent = SummarizerAgent()

        with patch.object(
            agent, "_call_llm",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Request timed out"),
        ):
            with pytest.raises(AgentExecutionError) as exc_info:
                await agent.run(state)

        assert "summarizer" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_llm_non_retryable_error_raises_agent_execution_error(self, sample_state):
        """Non-network errors (e.g. auth failure) wrap into AgentExecutionError immediately."""
        from agentforge.backend.agents.critic_agent import CriticAgent
        from agentforge.backend.core.exceptions import AgentExecutionError

        state = {**sample_state, "summary": "Some summary."}
        agent = CriticAgent()

        with patch.object(
            agent, "_call_llm",
            new_callable=AsyncMock,
            side_effect=ValueError("Invalid API key"),
        ):
            with pytest.raises(AgentExecutionError) as exc_info:
                await agent.run(state)

        # run() wraps the error; the original reason must appear in the message
        assert "Invalid API key" in str(exc_info.value)
        assert "critic" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_web_search_connect_error_is_non_fatal(self, sample_state, mock_vector_store):
        """A ConnectError from web search must NOT crash the researcher — it logs and continues."""
        import httpx
        from agentforge.backend.agents.researcher_agent import ResearcherAgent

        agent = ResearcherAgent()

        mock_ddg = MagicMock()
        mock_ddg.run.side_effect = httpx.ConnectError("Network unreachable")

        with patch(
            "agentforge.backend.agents.researcher_agent.get_vector_store",
            new_callable=AsyncMock,
            return_value=mock_vector_store,
        ), patch(
            "langchain_community.tools.DuckDuckGoSearchRun",
            return_value=mock_ddg,
        ), patch.object(agent, "_call_llm", new_callable=AsyncMock, return_value="Research output."):
            result = await agent._execute(sample_state)

        # Pipeline must complete — web snippets are empty but no exception raised
        assert "refined_research" in result
        assert result["web_snippets"] == []
        assert result["agent_status"]["researcher"] == "completed"

    @pytest.mark.asyncio
    async def test_web_search_generic_error_is_non_fatal(self, sample_state, mock_vector_store):
        """Any exception from DuckDuckGo must be swallowed — researcher still returns a result."""
        from agentforge.backend.agents.researcher_agent import ResearcherAgent

        agent = ResearcherAgent()

        mock_ddg = MagicMock()
        mock_ddg.run.side_effect = RuntimeError("DuckDuckGo rate limited")

        with patch(
            "agentforge.backend.agents.researcher_agent.get_vector_store",
            new_callable=AsyncMock,
            return_value=mock_vector_store,
        ), patch(
            "langchain_community.tools.DuckDuckGoSearchRun",
            return_value=mock_ddg,
        ), patch.object(agent, "_call_llm", new_callable=AsyncMock, return_value="Research output."):
            result = await agent._execute(sample_state)

        assert result["web_snippets"] == []
        assert result["agent_status"]["researcher"] == "completed"

    @pytest.mark.asyncio
    async def test_faiss_failure_falls_back_to_empty_results(self, sample_state):
        """FAISS retrieval failure must not crash researcher — falls back to empty chunks."""
        from agentforge.backend.agents.researcher_agent import ResearcherAgent

        agent = ResearcherAgent()
        failing_store = AsyncMock()
        failing_store.similarity_search = AsyncMock(
            side_effect=RuntimeError("FAISS index corrupted")
        )

        with patch(
            "agentforge.backend.agents.researcher_agent.get_vector_store",
            new_callable=AsyncMock,
            return_value=failing_store,
        ), patch.object(agent, "_call_llm", new_callable=AsyncMock, return_value="No context."):
            result = await agent._execute(sample_state)

        assert result["retrieved_chunks"] == []
        assert result["agent_status"]["researcher"] == "completed"
