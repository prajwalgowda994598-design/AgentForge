"""
AgentForge – Critic Agent
============================
Scores the summary 0–1 and signals whether to retry.
Compatible with LangChain ≥ 1.x.
"""

import json
import re
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from agentforge.backend.agents.base_agent import BaseAgent
from agentforge.backend.core.config import settings


_SYSTEM = """You are a rigorous research quality evaluator.
Assess the provided summary against the original query.

Your response MUST be valid JSON in this exact format:
{
  "score": <float between 0.0 and 1.0>,
  "verdict": "pass" or "fail",
  "reasoning": "<2-3 sentences explaining the score>",
  "gaps": ["<gap1>", "<gap2>"],
  "suggestions": ["<suggestion1>", "<suggestion2>"]
}

Scoring rules:
- Score >= 0.7 → verdict: "pass"
- Score <  0.7 → verdict: "fail"
- Penalise: vague answers, missing key concepts, unsupported claims
- Reward: specific facts, source citations, structured reasoning
"""


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract a JSON object from LLM output that may contain surrounding prose."""
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {
        "score": 0.5,
        "verdict": "fail",
        "reasoning": "Could not parse critic output.",
        "gaps": ["Unable to evaluate"],
        "suggestions": ["Re-run the research pipeline"],
    }


class CriticAgent(BaseAgent):
    """
    Agent 3 – Critic
    Consumes: query, summary. Produces: critic_score, critic_feedback, should_retry.
    """

    agent_name = "critic"

    async def _execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        query: str = state["query"]
        summary: str = state.get("summary", "")
        iteration: int = state.get("iteration", 0)

        # Hard stop: force pass when max iterations reached
        if iteration >= settings.MAX_RESEARCH_ITERATIONS:
            self.logger.warning("critic_forcing_pass", reason="max_iterations_reached",
                                iteration=iteration)
            return {
                **state,
                "critic_score": settings.CRITIC_PASS_THRESHOLD,
                "critic_feedback": {
                    "score": settings.CRITIC_PASS_THRESHOLD,
                    "verdict": "pass",
                    "reasoning": "Maximum iterations reached; proceeding with best available answer.",
                    "gaps": [],
                    "suggestions": [],
                },
                "should_retry": False,
                "agent_status": {**state.get("agent_status", {}), "critic": "completed"},
            }

        raw = await self._call_llm([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=(
                f"Original Query:\n{query}\n\n"
                f"Summary to Evaluate:\n{summary}"
            )),
        ])

        feedback = _extract_json(raw)
        score: float = float(feedback.get("score", 0.5))
        should_retry: bool = score < settings.CRITIC_PASS_THRESHOLD

        self.logger.info("critic_evaluation", score=score,
                         verdict=feedback.get("verdict"),
                         should_retry=should_retry, iteration=iteration)

        return {
            **state,
            "critic_score": score,
            "critic_feedback": feedback,
            "should_retry": should_retry,
            "iteration": iteration + 1,
            "agent_status": {**state.get("agent_status", {}), "critic": "completed"},
        }
