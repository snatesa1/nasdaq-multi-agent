"""
Abstract base class for all agents in the hierarchical system.
Enforces a consistent interface: every agent produces an AgentResult.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentResult:
    """
    Standardized output from any agent.

    Attributes:
        agent_name: Identifier of the producing agent (e.g. 'MacroAgent').
        score: Composite score 0.0 → 1.0 (higher = more bullish).
                None for agents that produce narrative-only output (e.g. News).
        confidence: How confident the agent is in its score (0.0 → 1.0).
        rationale: Human-readable explanation of the score.
        data: Arbitrary structured payload (charts, tables, raw metrics).
        sub_results: Optional nested results (e.g. per-stock within a sector).
    """
    agent_name: str
    score: Optional[float] = None
    confidence: float = 0.5
    rationale: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    sub_results: List["AgentResult"] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "agent": self.agent_name,
            "score": self.score,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "data": self.data,
            "sub_results": [r.to_dict() for r in self.sub_results],
        }


class BaseAgent(ABC):
    """
    Abstract base class for every agent in the hierarchy.
    Subclasses must implement `analyze()`.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent display name (e.g. 'MacroAgent')."""
        ...

    @abstractmethod
    async def analyze(self, **kwargs) -> AgentResult:
        """
        Run analysis and return a standardized AgentResult.
        kwargs vary by agent (symbol, data, context, etc).
        """
        ...

    def _log_start(self, context: str = ""):
        import logging
        logging.getLogger(self.name).info(f"🚀 {self.name} starting analysis {context}")

    def _log_done(self, result: AgentResult):
        import logging
        score_str = f"score={result.score:.2f}" if result.score is not None else "narrative"
        logging.getLogger(self.name).info(
            f"✅ {self.name} done — {score_str}, confidence={result.confidence:.2f}"
        )
