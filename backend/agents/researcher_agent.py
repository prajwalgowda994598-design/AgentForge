"""
AgentForge – Researcher Agent
================================
Searches FAISS + web, extracts key facts using the LLM.
Compatible with LangChain ≥ 1.x (uses ainvoke directly).
"""

from typing import Any, Dict, List

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from agentforge.backend.agents.base_agent import BaseAgent, _RETRYABLE_EXCEPTIONS
from agentforge.backend.core.config import settings
from agentforge.backend.core.exceptions import AgentExecutionError
from agentforge.backend.vectorstore.faiss_store import get_vector_store


class ResearcherAgent(BaseAgent):
    """
    Agent 1 – Researcher
    Writes: retrieved_chunks, web_snippets, raw_context, refined_research
    """

    agent_name = "researcher"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query: str = state["query"]
        top_k: int = state.get("top_k", settings.FAISS_TOP_K)
        iteration: int = state.get("iteration", 0)

        # ── 1. FAISS retrieval ─────────────────────────────────────────────────
        try:
            vs = await get_vector_store()
            faiss_results = await vs.similarity_search(query, k=top_k)
        except Exception as exc:
            self.logger.warning(
                "faiss_retrieval_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            faiss_results = []
        self.logger.info("faiss_retrieved", count=len(faiss_results),
                         query_preview=query[:60])

        # ── 2. Web search (first iteration or sparse FAISS) ───────────────────
        web_snippets: List[str] = []
        if faiss_results:
            avg_score = sum(r.get("score", 0) for r in faiss_results) / len(faiss_results)
        else:
            avg_score = 0.0

        if iteration == 0 or avg_score < 0.5:
            try:
                import asyncio, concurrent.futures
                from langchain_community.tools import DuckDuckGoSearchRun
                _search_fn = DuckDuckGoSearchRun().run
                loop = asyncio.get_event_loop()
                web_result = await loop.run_in_executor(None, _search_fn, query)
                if web_result:
                    web_snippets = [s.strip() for s in web_result.split("\n\n") if s.strip()][:5]
                    self.logger.info("web_search_complete", snippets=len(web_snippets))
            except _RETRYABLE_EXCEPTIONS as exc:
                # Transient network failure — log clearly, continue without web results.
                self.logger.warning(
                    "web_search_network_error",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
            except Exception as exc:
                # Any other failure (rate limit, parse error, etc.) — non-fatal.
                self.logger.warning(
                    "web_search_failed",
                    error_type=type(exc).__name__,
                    error=str(exc),
                )

        # ── 3. Assemble context block ──────────────────────────────────────────
        context_parts: List[str] = []
        if faiss_results:
            context_parts.append("## Retrieved Documents\n")
            for i, chunk in enumerate(faiss_results, 1):
                context_parts.append(
                    f"[{i}] **{chunk.get('title','Unknown')}** "
                    f"(score={chunk.get('score',0):.3f})\n"
                    f"Source: {chunk.get('source','')}\n"
                    f"{chunk.get('content','')}\n"
                )
        if web_snippets:
            context_parts.append("\n## Web Search Results\n")
            for i, snippet in enumerate(web_snippets, 1):
                context_parts.append(f"[W{i}] {snippet}\n")

        raw_context = "\n".join(context_parts) if context_parts else "No relevant context found."

        # ── 4. LLM refinement ─────────────────────────────────────────────────
        refined = await self._call_llm([
            SystemMessage(content=(
                "You are a precise research assistant. "
                "Given the context below, extract and organise the most relevant facts "
                "that directly answer the user query. "
                "Output clean bullet points. Include source references where available. "
                "Do NOT hallucinate; only state what is in the context."
            )),
            HumanMessage(content=f"Query: {query}\n\nContext:\n{raw_context}"),
        ])

        return {
            **state,
            "retrieved_chunks": faiss_results,
            "web_snippets": web_snippets,
            "raw_context": raw_context,
            "refined_research": refined,
            "agent_status": {**state.get("agent_status", {}), "researcher": "completed"},
        }
