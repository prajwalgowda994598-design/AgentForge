"""
AgentForge – Fact Checker Agent
==================================
Verifies claims against sources and annotates citations.
Compatible with LangChain ≥ 1.x.
"""

from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from agentforge.backend.agents.base_agent import BaseAgent


_SYSTEM = """You are a meticulous fact-checking agent.

Your task:
1. Read the summary and identify every factual claim.
2. For each claim, check whether it is supported by the provided source material.
3. Label each claim: [VERIFIED], [UNVERIFIED], or [CONTRADICTED].
4. Remove or clearly flag [CONTRADICTED] claims.
5. Add inline citations in the format [Source: <title>] after verified claims.

Output a corrected, citation-annotated version of the summary.
Include a "Fact-Check Report" section at the bottom.

Rules:
- Do not introduce new information not present in the sources.
- Keep [UNVERIFIED] claims but clearly mark them.
- Be precise; do not remove correct information.
"""


def _build_source_block(chunks: List[Dict[str, Any]], snippets: List[str]) -> str:
    parts = ["## Available Sources\n"]
    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[{i}] **{chunk.get('title', f'Document {i}')}** "
            f"({chunk.get('source', '')})\n"
            f"{chunk.get('content', '')[:500]}\n"
        )
    for j, snippet in enumerate(snippets, 1):
        parts.append(f"[W{j}] Web: {snippet[:300]}\n")
    return "\n".join(parts)


class FactCheckerAgent(BaseAgent):
    """
    Agent 4 – Fact Checker
    Consumes: summary, retrieved_chunks, web_snippets.
    Produces: verified_summary.
    """

    agent_name = "fact_checker"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query: str = state["query"]
        summary: str = state.get("summary", "")
        chunks: List[Dict[str, Any]] = state.get("retrieved_chunks", [])
        snippets: List[str] = state.get("web_snippets", [])

        if not summary:
            return {
                **state,
                "verified_summary": "No summary available to fact-check.",
                "agent_status": {**state.get("agent_status", {}), "fact_checker": "completed"},
            }

        source_block = _build_source_block(chunks, snippets)

        verified = await self._call_llm([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=(
                f"Original Query: {query}\n\n"
                f"{source_block}\n\n"
                f"## Summary to Verify\n{summary}"
            )),
        ])

        self.logger.info("fact_check_complete", summary_length=len(summary),
                         verified_length=len(verified))

        return {
            **state,
            "verified_summary": verified,
            "agent_status": {**state.get("agent_status", {}), "fact_checker": "completed"},
        }
