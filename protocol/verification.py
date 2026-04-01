# protocol/verification.py
"""
Qualquer pessoa pode verificar qualquer decisão.

Este é o ponto onde Vitalik e Cloudhead convergem:
- Vitalik: "Don't trust, verify"
- Cloudhead: "Sovereign verification, no gatekeepers"

O adr-ledger torna verificação uma primitiva de primeira classe.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VerificationProof:
    """
    Prova verificável de que uma decisão foi tomada corretamente.

    Dado:
    1. A policy version (hash do repo Radicle no momento)
    2. O input (quem, o quê, contexto)
    3. O output (allow/deny)

    Qualquer pessoa pode:
    - Clonar o repo Radicle naquele commit
    - Rodar OPA com aquele input
    - Verificar que o output é idêntico
    - Confirmar que o hash chain no Algorand é íntegro
    """

    # O que verificar
    decision_hash: str              # hash da decisão
    algorand_tx_id: str             # onde está registrada

    # Inputs reprodutíveis
    policy_commit: str              # git commit (Radicle)
    policy_hash: str                # sha256 das policies naquele commit
    input_hash: str                 # sha256 do input ao OPA

    # Resultado esperado
    expected_output: bool           # allow ou deny
    expected_reasons: list[str]

    # Chain de hashes
    prev_decision_hash: str         # hash da decisão anterior
    chain_position: int             # posição no hash chain

    def verification_steps(self) -> list[str]:
        return [
            f"1. rad clone <rid> && git checkout {self.policy_commit}",
            f"2. sha256sum policies/* → deve ser {self.policy_hash}",
            f"3. opa eval -d policies/ -i input.json 'data.adr.authz.decision'",
            f"4. output.allow deve ser {self.expected_output}",
            f"5. Algorand: verificar tx {self.algorand_tx_id}",
            f"6. Hash chain: H({self.chain_position}) = sha256("
            f"   H({self.chain_position - 1}) || entry_data)",
            f"7. H({self.chain_position - 1}) = {self.prev_decision_hash}",
        ]
