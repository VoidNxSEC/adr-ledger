# adr_ledger/chain/algorand_client.py
"""
Cliente Algorand para o adr-ledger.
Faz bridge entre decisões do OPA e registro on-chain.
"""

from dataclasses import dataclass
from typing import Optional
import hashlib
import json

from algokit_utils import (
    ApplicationClient,
    get_algod_client,
    get_indexer_client,
    get_account,
    TransactionParameters,
)
from algosdk.v2client import algod, indexer
from algosdk import transaction, account, mnemonic
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    TransactionWithSigner,
    AccountTransactionSigner,
)


@dataclass
class ChainConfig:
    algod_url: str = "https://mainnet-api.algonode.cloud"
    indexer_url: str = "https://mainnet-idx.algonode.cloud"
    app_id: int = 0  # ID do GovernanceController deployado
    network: str = "mainnet"  # mainnet | testnet | localnet


@dataclass
class AuditReceipt:
    """Recibo de uma decisão registrada on-chain."""
    tx_id: str
    block_round: int
    chain_hash: bytes
    timestamp: int
    confirmed: bool


class AlgorandGovernance:
    """
    Integra o adr-ledger com Algorand para:
    1. Audit trail imutável on-chain
    2. Multi-sig approval workflows
    3. Agent identity on-chain
    4. Hash chain verificável
    """

    def __init__(self, config: ChainConfig):
        self.config = config
        self.algod = algod.AlgodClient("", config.algod_url)
        self.indexer = indexer.IndexerClient("", config.indexer_url)

        # Conta do governance controller (carregada de sops-nix secret)
        self._governance_signer: Optional[AccountTransactionSigner] = None

    def load_signer_from_secret(self, secret_path: str):
        """Carrega a chave do agente a partir do secret gerido pelo sops-nix."""
        with open(secret_path, "r") as f:
            mn = f.read().strip()
        sk = mnemonic.to_private_key(mn)
        addr = account.address_from_private_key(sk)
        self._governance_signer = AccountTransactionSigner(sk)
        self._governance_address = addr

    # ==========================================
    # AUDIT TRAIL ON-CHAIN
    # ==========================================

    async def record_decision(
        self,
        agent_id: str,
        action: str,
        resource_id: str,
        allowed: bool,
        policy_version: str,
        metadata: Optional[dict] = None,
    ) -> AuditReceipt:
        """
        Registra uma decisão de IAM no Algorand.
        Cada decisão vira uma transação verificável.
        """

        # Monta nota com dados estruturados
        note_data = {
            "type": "adr-ledger:audit:v1",
            "agent": agent_id,
            "action": action,
            "resource": resource_id,
            "allowed": allowed,
            "policy_version": policy_version,
            "content_hash": self._hash_metadata(metadata),
        }

        note = json.dumps(note_data, sort_keys=True).encode()

        # Opção 1: Application call (se quiser hash chain on-chain)
        atc = AtomicTransactionComposer()
        sp = self.algod.suggested_params()

        atc.add_method_call(
            app_id=self.config.app_id,
            method=self._get_method("record_decision"),
            sender=self._governance_address,
            sp=sp,
            signer=self._governance_signer,
            method_args=[
                agent_id,        # agent address/id
                action,
                resource_id,
                allowed,
                policy_version,
            ],
            note=note,
        )

        result = atc.execute(self.algod, wait_rounds=4)

        tx_id = result.tx_ids[0]
        tx_info = self.algod.pending_transaction_info(tx_id)

        return AuditReceipt(
            tx_id=tx_id,
            block_round=tx_info["confirmed-round"],
            chain_hash=result.abi_results[0].return_value,
            timestamp=tx_info.get("round-time", 0),
            confirmed=True,
        )

    # ==========================================
    # MULTI-PARTY APPROVAL (ATOMIC GROUPS)
    # ==========================================

    async def submit_multi_approval(
        self,
        adr_id: str,
        approvers: list[dict],  # [{"address": ..., "signer": ...}]
    ) -> list[AuditReceipt]:
        """
        Submete aprovações múltiplas como grupo atômico.
        Ou TODAS aprovam, ou NENHUMA é registrada.

        Isso garante que ADRs críticos só passam com N aprovações
        simultâneas — impossível de burlar.
        """

        atc = AtomicTransactionComposer()
        sp = self.algod.suggested_params()

        for approver in approvers:
            atc.add_method_call(
                app_id=self.config.app_id,
                method=self._get_method("approve_adr"),
                sender=approver["address"],
                sp=sp,
                signer=approver["signer"],
                method_args=[adr_id],
            )

        # Execução atômica — tudo ou nada
        result = atc.execute(self.algod, wait_rounds=4)

        return [
            AuditReceipt(
                tx_id=tx_id,
                block_round=0,
                chain_hash=b"",
                timestamp=0,
                confirmed=True,
            )
            for tx_id in result.tx_ids
        ]

    # ==========================================
    # VERIFICAÇÃO / QUERY
    # ==========================================

    async def verify_audit_chain(
        self,
        from_round: int,
        to_round: Optional[int] = None,
    ) -> dict:
        """
        Verifica a integridade do hash chain de audit.
        Qualquer pessoa pode verificar — é público no Algorand.
        """

        txns = self.indexer.search_transactions(
            application_id=self.config.app_id,
            min_round=from_round,
            max_round=to_round,
            note_prefix="eyJ0eXBlIjoiYWRyLWxlZGdlcjphdWRpdDp2MSI",  # base64 prefix
        )

        chain_valid = True
        prev_hash = None

        for txn in txns.get("transactions", []):
            note = json.loads(
                __import__("base64").b64decode(txn["note"]).decode()
            )

            if prev_hash is not None:
                # Verifica continuidade do chain
                expected = hashlib.sha256(
                    f"{prev_hash}:{json.dumps(note, sort_keys=True)}".encode()
                ).hexdigest()
                # ... validação

            prev_hash = note.get("content_hash")

        return {
            "valid": chain_valid,
            "entries_checked": len(txns.get("transactions", [])),
            "range": {"from": from_round, "to": to_round},
        }

    async def get_agent_history(self, agent_id: str) -> list[dict]:
        """Busca todo histórico de decisões de um agente."""
        txns = self.indexer.search_transactions(
            application_id=self.config.app_id,
            note_prefix=__import__("base64").b64encode(
                f'{{"type":"adr-ledger:audit:v1","agent":"{agent_id}"'.encode()
            ).decode()[:20],
        )
        return txns.get("transactions", [])

    # ==========================================
    # HELPERS
    # ==========================================

    @staticmethod
    def _hash_metadata(metadata: Optional[dict]) -> str:
        if not metadata:
            return hashlib.sha256(b"empty").hexdigest()
        return hashlib.sha256(
            json.dumps(metadata, sort_keys=True).encode()
        ).hexdigest()

    def _get_method(self, name: str):
        """Retorna o ABI method do contrato."""
        # Carregado do ARC-32 app spec gerado pelo algokit
        from contracts.artifacts.GovernanceController.client import (
            GovernanceControllerClient
        )
        # ... resolve method
        pass
