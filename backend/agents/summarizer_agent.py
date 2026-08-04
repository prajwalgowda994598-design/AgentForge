"""
AgentForge – Summarizer Agent
================================
Condenses research into structured Markdown notes.
Compatible with LangChain ≥ 1.x.
"""

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from agentforge.backend.agents.base_agent import BaseAgent


_SYSTEM = """You are an expert research summarizer.
Produce a clean, structured summary in this format:

## Key Findings
- Bullet points of the most important facts

## Main Themes
- High-level themes or patterns observed

## Entities Mentioned
- Named entities: people, organisations, concepts, dates

## Confidence
State your confidence level (High / Medium / Low) and briefly explain why.

Rules:
- Be factual and concise; remove duplicates
- Preserve source references in parentheses
- Never add information not present in the input
"""


class SummarizerAgent(BaseAgent):
    """Agent 2 – Summarizer. Consumes: refined_research. Produces: summary."""

    agent_name = "summarizer"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query: str = state["query"]
        research: str = state.get("refined_research", state.get("raw_context", ""))

        if not research or research.strip() == "No relevant context found.":
            summary = "Insufficient research material available to produce a summary."
        else:
            summary = await self._call_llm([
                SystemMessage(content=_SYSTEM),
                HumanMessage(content=f"Original Query: {query}\n\nResearch Notes:\n{research}"),
            ])

        self.logger.info("summary_generated", length=len(summary),
                         query_preview=query[:60])

        return {
            **state,
            "summary": summary,
            "agent_status": {**state.get("agent_status", {}), "summarizer": "completed"},
        }
