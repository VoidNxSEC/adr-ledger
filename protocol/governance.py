# protocol/governance.py
"""
Mecanismos de governança para policy changes.

Implementa ideias do Vitalik sobre:
- Quadratic voting (raiz quadrada do peso)
- Conviction voting (preferência acumula ao longo do tempo)
- Time-weighted governance (quem está há mais tempo tem mais contexto)
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import math
import time


class VoteType(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    REQUEST_CHANGES = "request_changes"


@dataclass
class GovernanceProposal:
    """Uma proposta de mudança de policy."""

    proposal_id: str
    radicle_patch_id: str           # patch no Radicle
    proposer: str                   # soul_hash do proposer
    title: str
    description: str
    impact_level: str               # low | medium | high | critical
    created_at: int
    voting_deadline: int            # quando a votação fecha

    votes: list["Vote"] = field(default_factory=list)
    status: str = "open"           # open | passed | rejected | expired

    # === THRESHOLDS DINÂMICOS ===
    # Quanto maior o impacto, mais aprovação precisa

    @property
    def required_threshold(self) -> float:
        thresholds = {
            "low": 0.5,
            "medium": 0.6,
            "high": 0.75,
            "critical": 0.9,     # quase unanimidade
        }
        return thresholds.get(self.impact_level, 0.6)

    @property
    def quadratic_score(self) -> float:
        """
        Quadratic voting: o peso de cada voto é √(reputation).

        Por quê quadratic?
        - Previne que um único agente com alta reputação domine
        - Dá voz a agentes mais novos
        - Incentiva participação ampla, não concentrada
        """
        approve_weight = sum(
            math.sqrt(max(1, v.voter_reputation))
            for v in self.votes if v.vote_type == VoteType.APPROVE
        )
        total_weight = sum(
            math.sqrt(max(1, v.voter_reputation))
            for v in self.votes if v.vote_type != VoteType.ABSTAIN
        )

        if total_weight == 0:
            return 0.0

        return approve_weight / total_weight

    @property
    def conviction_score(self) -> float:
        """
        Conviction voting: votos acumulam peso ao longo do tempo.

        Inspirado no trabalho do BlockScience e citado pelo Vitalik
        como mecanismo que evita decisões apressadas.

        conviction(t) = conviction(t-1) * decay + tokens_staked
        """
        now = time.time()
        decay = 0.9  # 10% decay por período
        total_conviction = 0.0

        for vote in self.votes:
            if vote.vote_type == VoteType.APPROVE:
                # Quanto mais tempo o voto está registrado, mais peso
                time_staked = (now - vote.timestamp) / 3600  # horas
                periods = int(time_staked)
                conviction = 0.0
                weight = math.sqrt(max(1, vote.voter_reputation))

                for _ in range(periods):
                    conviction = conviction * decay + weight

                total_conviction += conviction

        return total_conviction

    def evaluate(self) -> dict:
        """Avalia se a proposta passa."""
        q_score = self.quadratic_score
        c_score = self.conviction_score
        threshold = self.required_threshold

        # Para proposals de alto impacto, exigir AMBOS os mecanismos
        if self.impact_level in ("high", "critical"):
            passed = (
                q_score >= threshold
                and c_score > 10.0  # conviction mínima
                and len(self.votes) >= 3  # quorum mínimo
            )
        else:
            passed = q_score >= threshold and len(self.votes) >= 2

        return {
            "passed": passed,
            "quadratic_score": q_score,
            "conviction_score": c_score,
            "threshold": threshold,
            "vote_count": len(self.votes),
            "impact": self.impact_level,
        }


@dataclass
class Vote:
    voter: str               # soul_hash
    vote_type: VoteType
    voter_reputation: float  # reputation score no momento do voto
    timestamp: int
    rationale: str = ""      # por que votou assim
    algorand_tx: str = ""    # tx que registra o voto on-chain
