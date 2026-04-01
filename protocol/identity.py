# protocol/identity.py
"""
Identidade Soulbound para Agentes.

Combina:
- Radicle DID (chave pública p2p)
- Algorand address (on-chain)
- NixOS system user (OS-level)

A identidade é:
- Não-transferível (soulbound)
- Acumula reputação baseada em histórico
- Verificável em todas as camadas
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
import hashlib
import json
import time


class AgentType(Enum):
    AUTONOMOUS = "autonomous"      # age sozinho dentro de limites
    SUPERVISED = "supervised"      # age com aprovação humana
    ADVISORY = "advisory"         # só sugere, nunca age
    HYBRID = "hybrid"             # modo depende do contexto/risco


@dataclass
class SoulboundIdentity:
    """
    Identidade soulbound de um agente.
    Inspirada nos SBTs do Vitalik, mas adaptada para agentes de software.
    """

    # === Identificadores cross-layer ===
    agent_name: str                        # human-readable
    radicle_did: str                       # rad:z6Mk... (Radicle peer ID)
    algorand_address: str                  # ALGO... (on-chain)
    nixos_user: str                        # agent-<name> (OS-level)

    # === Propriedades soulbound (não-transferíveis) ===
    agent_type: AgentType
    created_at: int                        # unix timestamp
    created_by: str                        # quem registrou este agente
    purpose: str                           # por que este agente existe

    # === Reputação acumulada (calculada, não definida) ===
    reputation: "ReputationScore" = None

    # === Capabilities (o que PODE fazer, não o que FAZ) ===
    capabilities: list[str] = field(default_factory=list)

    # === Attestations (quem vouches por este agente) ===
    attestations: list["Attestation"] = field(default_factory=list)

    @property
    def soul_hash(self) -> str:
        """
        Hash único e determinístico desta identidade.
        Muda se qualquer propriedade core mudar.
        """
        core = {
            "name": self.agent_name,
            "radicle": self.radicle_did,
            "algorand": self.algorand_address,
            "type": self.agent_type.value,
            "created_at": self.created_at,
            "purpose": self.purpose,
        }
        return hashlib.sha256(
            json.dumps(core, sort_keys=True).encode()
        ).hexdigest()

    def is_valid_across_layers(self) -> dict:
        """Verifica se a identidade é consistente em todas as camadas."""
        return {
            "radicle_linked": bool(self.radicle_did),
            "algorand_linked": bool(self.algorand_address),
            "nixos_linked": bool(self.nixos_user),
            "has_attestations": len(self.attestations) > 0,
            "reputation_positive": (
                self.reputation and self.reputation.score > 0
            ),
        }


@dataclass
class ReputationScore:
    """
    Reputação calculada a partir do histórico on-chain.

    Inspirada no conceito de Vitalik de "provable reputation"
    — não é um número arbitrário, é derivada de ações verificáveis.
    """

    total_decisions: int = 0
    successful_proposals: int = 0
    rejected_proposals: int = 0
    approvals_given: int = 0
    policy_contributions: int = 0     # patches merged no Radicle
    disputes_involved: int = 0
    uptime_hours: float = 0

    @property
    def score(self) -> float:
        """
        Score não-linear.
        Contribuições positivas têm retorno decrescente (√).
        Ações negativas têm peso crescente.
        """
        positive = (
            (self.successful_proposals ** 0.5) * 10
            + (self.approvals_given ** 0.5) * 5
            + (self.policy_contributions ** 0.5) * 20  # alto peso
        )
        negative = (
            self.rejected_proposals * 2
            + self.disputes_involved * 5
        )
        return max(0, positive - negative)

    @property
    def trust_level(self) -> str:
        s = self.score
        if s == 0:
            return "unestablished"
        elif s < 10:
            return "provisional"
        elif s < 50:
            return "established"
        elif s < 100:
            return "trusted"
        else:
            return "highly_trusted"


@dataclass
class Attestation:
    """
    Attestation de outro agente ou humano.
    "Eu voucho que este agente é confiável para X."
    """
    attester: str               # soul_hash de quem atesta
    capability: str             # o que está sendo atestado
    evidence: str               # hash de evidência (tx Algorand, etc)
    timestamp: int
    expires_at: Optional[int] = None  # attestations podem expirar

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
