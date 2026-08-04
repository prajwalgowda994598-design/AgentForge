"""
AgentForge – Synthesizer Agent
=================================
Generates the final polished Markdown answer.
Compatible with LangChain ≥ 1.x.
"""

from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from agentforge.backend.agents.base_agent import BaseAgent


_SYSTEM = """You are an expert research synthesis agent.
Combine all validated information into a single, clear, professionally written
answer in Markdown format.

Structure your output as:
# <Concise title answering the query>

## Answer
<Comprehensive, flowing prose answer. 3-6 paragraphs.>

## Key Points
- Bullet summary of the most important takeaways

## Sources & Citations
- List all cited sources with titles and any URLs available

## Confidence Assessment
<One paragraph assessing reliability based on the critic score.>

Rules:
- Write for an intelligent non-specialist audience
- Use clear, precise language; preserve [Source: ...] citations inline
- Do not add information beyond what is provided
- The answer should be self-contained and complete
"""


class SynthesizerAgent(BaseAgent):
    """
    Agent 5 – Synthesizer
    Consumes: verified_summary, critic_score, critic_feedback, query.
    Produces: final_answer.
    """

    agent_name = "synthesizer"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query: str = state["query"]
        verified: str = state.get("verified_summary", state.get("summary", ""))
        score: float = state.get("critic_score", 0.0)
        feedback: Dict = state.get("critic_feedback", {})
        chunks = state.get("retrieved_chunks", [])

        sources = []
        for c in chunks:
            t, s = c.get("title", ""), c.get("source", "")
            if t or s:
                sources.append({"title": t, "source": s, "score": c.get("score", 0)})

        sources_block = "\n".join(
            f"- {s['title']} ({s['source']})" for s in sources
        ) or "No explicit sources available."

        gaps = feedback.get("gaps", [])
        gaps_note = f"\nKnown gaps: {'; '.join(gaps)}" if gaps else ""

        final_answer = await self._call_llm([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=(
                f"User Query: {query}\n\n"
                f"Verified Research Summary:\n{verified}\n\n"
                f"Quality Score: {score:.2f}/1.0{gaps_note}\n\n"
                f"Available Sources:\n{sources_block}"
            )),
        ])

        self.logger.info("synthesis_complete", answer_length=len(final_answer),
                         critic_score=score)

        return {
            **state,
            "final_answer": final_answer,
            "sources": sources,
            "agent_status": {**state.get("agent_status", {}), "synthesizer": "completed"},
        }
