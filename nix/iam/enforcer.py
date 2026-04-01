# adr_ledger/iam/enforcer.py
"""
Middleware de enforcement que conecta o adr-ledger ao OPA.
Cada ação de agente passa por aqui antes de executar.
"""

import httpx
import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class Action(Enum):
    READ = "read"
    LIST = "list"
    PROPOSE = "propose"
    APPROVE = "approve"
    REJECT = "reject"
    WITHDRAW = "withdraw"
    SUPERSEDE = "supersede"
    DEPRECATE = "deprecate"


@dataclass
class AgentIdentity:
    id: str
    roles: list[str]
    type: str  # "human" | "automated" | "hybrid"
    capabilities: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class PolicyDecision:
    allow: bool
    reasons: list[str]
    audit_id: str
    evaluated_at: datetime
    policy_version: str


class IAMEnforcer:
    """
    Ponto central de decisão IAM.
    Toda ação no adr-ledger passa por enforce().
    """

    def __init__(self, opa_url: str = "http://localhost:8181"):
        self.opa_url = opa_url
        self._decision_cache: dict[str, PolicyDecision] = {}
        self._action_log: list[dict] = []

    async def enforce(
        self,
        agent: AgentIdentity,
        action: Action,
        resource: dict,
        context: Optional[dict] = None,
    ) -> PolicyDecision:
        """
        Avalia a política antes de permitir qualquer ação.
        NUNCA bypassa — fail-closed por design.
        """

        input_payload = {
            "agent": {
                "id": agent.id,
                "roles": agent.roles,
                "type": agent.type,
                "capabilities": agent.capabilities,
                "actions_last_hour": await self._get_recent_actions(agent.id),
            },
            "action": action.value,
            "resource": resource,
            "context": context or {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        try:
            decision = await self._query_opa(input_payload)
        except Exception as e:
            # FAIL-CLOSED: se OPA não responde, nega por padrão
            return PolicyDecision(
                allow=False,
                reasons=[f"policy_engine_unavailable: {e}"],
                audit_id=self._generate_audit_id(input_payload),
                evaluated_at=datetime.utcnow(),
                policy_version="unknown",
            )

        # Log de auditoria imutável
        await self._append_audit_log(input_payload, decision)

        return decision

    async def _query_opa(self, input_data: dict) -> PolicyDecision:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{self.opa_url}/v1/data/adr/authz/decision",
                json={"input": input_data},
            )
            resp.raise_for_status()
            result = resp.json()["result"]

            return PolicyDecision(
                allow=result["allow"] and not result["deny"],
                reasons=result.get("reasons", []),
                audit_id=result["audit"].get("id", ""),
                evaluated_at=datetime.utcnow(),
                policy_version=resp.headers.get("x-opa-bundle-revision", "unknown"),
            )

    async def _get_recent_actions(self, agent_id: str) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(hours=1)
        return [
            a for a in self._action_log
            if a["agent_id"] == agent_id
            and datetime.fromisoformat(a["timestamp"]) > cutoff
        ]

    async def _append_audit_log(self, input_data: dict, decision: PolicyDecision):
        entry = {
            "agent_id": input_data["agent"]["id"],
            "action": input_data["action"],
            "resource_id": input_data["resource"].get("id"),
            "allowed": decision.allow,
            "reasons": decision.reasons,
            "timestamp": datetime.utcnow().isoformat(),
            "audit_id": decision.audit_id,
        }
        self._action_log.append(entry)
        # TODO: persistir no ledger imutável (append-only)

    @staticmethod
    def _generate_audit_id(payload: dict) -> str:
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()[:16]


# === USO NO ADR-LEDGER ===

enforcer = IAMEnforcer()

async def propose_adr(agent: AgentIdentity, adr_data: dict):
    """Exemplo: agente propondo um novo ADR."""

    decision = await enforcer.enforce(
        agent=agent,
        action=Action.PROPOSE,
        resource={"type": "adr", "impact": adr_data.get("impact", "low")},
        context={"source": "api", "session": "..."},
    )

    if not decision.allow:
        raise PermissionError(
            f"Ação negada para {agent.id}: {decision.reasons} "
            f"(audit: {decision.audit_id})"
        )

    # Prossegue com a criação do ADR...
    return create_adr(adr_data, proposed_by=agent.id)
