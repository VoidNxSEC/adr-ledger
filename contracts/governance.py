# contracts/governance.py
"""
ARC-4 Smart Contract para governança do adr-ledger.
Registra decisões, gerencia identidades de agentes on-chain,
e enforça approval workflows via atomic group transactions.
"""

from algopy import (
    ARC4Contract,
    Account,
    Application,
    Asset,
    BoxMap,
    BoxRef,
    Global,
    GlobalState,
    LocalState,
    Txn,
    UInt64,
    Bytes,
    String,
    arc4,
    gtxn,
    itxn,
    op,
    subroutine,
)
from algopy.arc4 import abimethod, Address, Bool, DynamicBytes, StaticArray


class AgentRole(arc4.UInt8):
    """0=none, 1=reader, 2=proposer, 3=approver, 4=admin, 5=auditor"""
    pass


class ADRStatus(arc4.UInt8):
    """0=draft, 1=proposed, 2=accepted, 3=rejected, 4=deprecated, 5=superseded"""
    pass


class AuditEntry(arc4.Struct):
    agent: arc4.Address
    action: arc4.String
    resource_id: arc4.String
    decision: Bool
    timestamp: arc4.UInt64
    policy_version: arc4.String
    prev_hash: StaticArray[arc4.Byte, 32]  # hash chain


class GovernanceController(ARC4Contract):
    """
    Contrato principal de governança do adr-ledger.

    Responsabilidades:
    - Registro de agentes com roles on-chain
    - Audit trail imutável com hash chain
    - Multi-sig approval para ADRs críticos
    - Rate limiting on-chain
    """

    def __init__(self) -> None:
        # === GLOBAL STATE ===
        self.admin = GlobalState(Account)
        self.total_agents = GlobalState(UInt64, default=UInt64(0))
        self.total_decisions = GlobalState(UInt64, default=UInt64(0))
        self.audit_chain_head = GlobalState(Bytes, default=Bytes(b"\x00" * 32))
        self.min_approvals_critical = GlobalState(UInt64, default=UInt64(2))
        self.paused = GlobalState(Bool, default=Bool(False))

        # === BOX STORAGE ===
        # Mapeia agent_address → role
        self.agent_roles = BoxMap(Account, AgentRole, key_prefix=b"ar_")
        # Mapeia agent_address → actions_count nesta epoch
        self.agent_action_counts = BoxMap(Account, arc4.UInt64, key_prefix=b"ac_")
        # Mapeia adr_id → approval_count
        self.adr_approvals = BoxMap(Bytes, arc4.UInt64, key_prefix=b"aa_")
        # Mapeia adr_id → status
        self.adr_status = BoxMap(Bytes, ADRStatus, key_prefix=b"as_")

    # ==========================================
    # AGENT IDENTITY MANAGEMENT
    # ==========================================

    @abimethod
    def register_agent(
        self,
        agent: Account,
        role: AgentRole,
    ) -> None:
        """Registra um agente com role específico. Só admin."""
        assert Txn.sender == self.admin, "only_admin"
        assert not self.paused, "contract_paused"

        self.agent_roles[agent] = role
        self.agent_action_counts[agent] = arc4.UInt64(0)
        self.total_agents.value = self.total_agents.value + UInt64(1)

    @abimethod
    def revoke_agent(self, agent: Account) -> None:
        """Remove um agente. Só admin."""
        assert Txn.sender == self.admin, "only_admin"
        del self.agent_roles[agent]
        del self.agent_action_counts[agent]

    @abimethod
    def rotate_role(
        self,
        agent: Account,
        new_role: AgentRole,
    ) -> None:
        """Rotaciona role de um agente. Só admin."""
        assert Txn.sender == self.admin, "only_admin"
        assert agent in self.agent_roles, "agent_not_found"
        self.agent_roles[agent] = new_role

    # ==========================================
    # AUDIT TRAIL — HASH CHAIN ON-CHAIN
    # ==========================================

    @abimethod
    def record_decision(
        self,
        agent: Account,
        action: arc4.String,
        resource_id: arc4.String,
        decision: Bool,
        policy_version: arc4.String,
    ) -> StaticArray[arc4.Byte, 32]:
        """
        Registra uma decisão de policy no ledger.
        Retorna o hash da entrada (para referência off-chain).

        Forma um hash chain: H(n) = hash(H(n-1) || entry_data)
        """
        assert Txn.sender == self.admin or self._is_governance_agent(Txn.sender), \
            "unauthorized_recorder"

        # Monta dados para hash
        entry_data = op.concat(
            agent.bytes,
            action.bytes,
            resource_id.bytes,
            op.itob(Global.latest_timestamp),
            self.audit_chain_head.value,  # prev hash
        )

        # Hash chain
        new_hash = op.sha256(entry_data)
        self.audit_chain_head.value = new_hash

        self.total_decisions.value = self.total_decisions.value + UInt64(1)

        # Incrementa contador de ações do agente (rate limiting)
        if agent in self.agent_action_counts:
            current = self.agent_action_counts[agent]
            self.agent_action_counts[agent] = arc4.UInt64(
                current.native + UInt64(1)
            )

        # Emite log via inner transaction (indexável off-chain)
        itxn.Payment(
            receiver=Global.current_application_address,
            amount=UInt64(0),
            note=op.concat(b"AUDIT|", new_hash),
        ).submit()

        return StaticArray[arc4.Byte, 32].from_bytes(new_hash)

    # ==========================================
    # MULTI-SIG APPROVAL WORKFLOW
    # ==========================================

    @abimethod
    def propose_adr(
        self,
        adr_id: arc4.String,
        impact: arc4.String,
        content_hash: StaticArray[arc4.Byte, 32],
    ) -> None:
        """Propõe um ADR. Requer role proposer ou admin."""
        assert self._has_role(Txn.sender, AgentRole(2)) or \
               self._has_role(Txn.sender, AgentRole(4)), "not_proposer"

        adr_key = adr_id.bytes
        self.adr_status[adr_key] = ADRStatus(1)  # proposed
        self.adr_approvals[adr_key] = arc4.UInt64(0)

    @abimethod
    def approve_adr(self, adr_id: arc4.String) -> Bool:
        """
        Aprova um ADR. Retorna True se threshold atingido.
        Usa group transactions para multi-party approval.
        """
        assert self._has_role(Txn.sender, AgentRole(3)) or \
               self._has_role(Txn.sender, AgentRole(4)), "not_approver"

        adr_key = adr_id.bytes
        assert adr_key in self.adr_status, "adr_not_found"

        current_status = self.adr_status[adr_key]
        assert current_status == ADRStatus(1), "not_in_proposed_state"

        # Incrementa aprovações
        current_approvals = self.adr_approvals[adr_key]
        new_count = current_approvals.native + UInt64(1)
        self.adr_approvals[adr_key] = arc4.UInt64(new_count)

        # Verifica threshold
        if new_count >= self.min_approvals_critical.value:
            self.adr_status[adr_key] = ADRStatus(2)  # accepted
            return Bool(True)

        return Bool(False)

    # ==========================================
    # RATE LIMITING ON-CHAIN
    # ==========================================

    @abimethod
    def check_rate_limit(
        self,
        agent: Account,
        max_actions: arc4.UInt64,
    ) -> Bool:
        """Verifica se agente está dentro do rate limit."""
        if agent not in self.agent_action_counts:
            return Bool(True)

        current = self.agent_action_counts[agent]
        return Bool(current.native < max_actions.native)

    @abimethod
    def reset_epoch(self) -> None:
        """Reset dos contadores. Chamado periodicamente pelo admin."""
        assert Txn.sender == self.admin, "only_admin"
        # Reset seria feito via iteração off-chain + chamadas individuais
        # ou via novo box prefix por epoch

    # ==========================================
    # HELPERS
    # ==========================================

    @subroutine
    def _has_role(self, account: Account, role: AgentRole) -> bool:
        if account not in self.agent_roles:
            return False
        return self.agent_roles[account] == role

    @subroutine
    def _is_governance_agent(self, account: Account) -> bool:
        return self._has_role(account, AgentRole(4))  # admin

    # ==========================================
    # CIRCUIT BREAKER
    # ==========================================

    @abimethod
    def pause(self) -> None:
        """Emergency pause. Só admin."""
        assert Txn.sender == self.admin, "only_admin"
        self.paused.value = Bool(True)

    @abimethod
    def unpause(self) -> None:
        assert Txn.sender == self.admin, "only_admin"
        self.paused.value = Bool(False)
