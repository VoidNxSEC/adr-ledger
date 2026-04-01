# adr_ledger/policies/radicle_sync.py
"""
Sincroniza policies do Radicle para o OPA.

Fluxo:
1. Policy change é proposto como Radicle Patch
2. Reviewers aprovam (on Radicle, descentralizado)
3. Merge dispara sync para OPA bundle
4. Decisão de aceitar o merge é registrada no Algorand
"""

import subprocess
import json
import shutil
import hashlib
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class RadicleConfig:
    rad_home: str = "/var/lib/adr-ledger/radicle"
    policy_rid: str = ""  # Radicle project ID (rad:z...)
    policy_branch: str = "main"
    opa_bundle_dir: str = "/var/lib/adr-ledger/policies/bundle"
    seed_nodes: list[str] = None

    def __post_init__(self):
        if self.seed_nodes is None:
            self.seed_nodes = [
                "z6MksFqXN3Yhqk8pTJdUGLwATkRfQvwZoVhvAS2W4gXt...",
                # peers do time de governança
            ]


class RadiclePolicySync:
    """
    Gerencia o ciclo de vida das policies via Radicle.

    Radicle é usado porque:
    - Sem dependência de GitHub/GitLab (soberano)
    - Patches são assinados criptograficamente
    - Histórico é imutável (git + p2p replication)
    - Review descentralizado
    """

    def __init__(self, config: RadicleConfig, algorand_client=None):
        self.config = config
        self.algorand = algorand_client
        self._env = {"RAD_HOME": config.rad_home}

    # ==========================================
    # INIT & SETUP
    # ==========================================

    def init_policy_repo(self):
        """Inicializa o repositório de policies no Radicle."""

        repo_path = Path(self.config.rad_home) / "policy-repo"
        repo_path.mkdir(parents=True, exist_ok=True)

        # Estrutura do repo de policies
        structure = {
            "adr/authz.rego": "package adr.authz\n# ...",
            "adr/lifecycle.rego": "package adr.lifecycle\n# ...",
            "adr/ratelimit.rego": "package adr.ratelimit\n# ...",
            "data/roles.json": json.dumps(self._default_roles(), indent=2),
            "data/agent_config.json": json.dumps(self._default_agent_config(), indent=2),
            ".manifest": json.dumps({
                "roots": ["adr", "data"],
                "revision": "",
            }),
            "GOVERNANCE.md": self._governance_readme(),
        }

        for path, content in structure.items():
            file_path = repo_path / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        # Git init + Radicle init
        self._run(["git", "init"], cwd=repo_path)
        self._run(["git", "add", "."], cwd=repo_path)
        self._run(
            ["git", "commit", "-m", "feat: initial policy structure"],
            cwd=repo_path,
        )
        result = self._run(
            ["rad", "init",
             "--name", "adr-ledger-policies",
             "--description", "IAM policies for adr-ledger agent governance",
             "--default-branch", "main",
             "--public"],
            cwd=repo_path,
        )

        print(f"Policy repo initialized: {result.stdout}")
        return result.stdout.strip()  # retorna o RID

    # ==========================================
    # POLICY PROPOSAL VIA RADICLE PATCHES
    # ==========================================

    def propose_policy_change(
        self,
        agent_id: str,
        description: str,
        changes: dict[str, str],  # {filepath: new_content}
    ) -> str:
        """
        Propõe uma mudança de policy via Radicle Patch.
        Equivalente a um PR, mas descentralizado.
        """

        repo_path = Path(self.config.rad_home) / "policy-repo"

        # Cria branch para a mudança
        branch_name = f"policy/{agent_id}/{self._short_hash(description)}"
        self._run(["git", "checkout", "-b", branch_name], cwd=repo_path)

        # Aplica mudanças
        for filepath, content in changes.items():
            file_path = repo_path / filepath
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        self._run(["git", "add", "."], cwd=repo_path)
        self._run(
            ["git", "commit", "-m", f"policy: {description}\n\nProposed-by: {agent_id}"],
            cwd=repo_path,
        )

        # Cria Radicle Patch (equivalente a PR)
        result = self._run(
            ["rad", "patch", "open",
             "--title", f"Policy Change: {description}",
             "--description", f"Proposed by agent {agent_id}"],
            cwd=repo_path,
        )

        patch_id = result.stdout.strip()

        # Volta pra main
        self._run(["git", "checkout", "main"], cwd=repo_path)

        return patch_id

    def review_patch(
        self,
        patch_id: str,
        reviewer_id: str,
        verdict: str,  # "accept" | "reject"
        comment: str = "",
    ):
        """Review de uma policy change no Radicle."""

        repo_path = Path(self.config.rad_home) / "policy-repo"

        if verdict == "accept":
            self._run(
                ["rad", "patch", "review", patch_id,
                 "--accept",
                 "--message", f"Approved by {reviewer_id}: {comment}"],
                cwd=repo_path,
            )
        else:
            self._run(
                ["rad", "patch", "review", patch_id,
                 "--reject",
                 "--message", f"Rejected by {reviewer_id}: {comment}"],
                cwd=repo_path,
            )

    def merge_and_deploy(self, patch_id: str) -> dict:
        """
        Merge uma policy aprovada e deploya para OPA.
        Registra o evento no Algorand.
        """

        repo_path = Path(self.config.rad_home) / "policy-repo"

        # Merge do patch
        self._run(
            ["rad", "patch", "merge", patch_id],
            cwd=repo_path,
        )

        # Calcula hash do novo estado das policies
        policy_hash = self._hash_policy_dir(repo_path)

        # Sync para OPA bundle directory
        self._sync_to_opa_bundle(repo_path)

        # Registra no Algorand
        receipt = None
        if self.algorand:
            import asyncio
            receipt = asyncio.run(
                self.algorand.record_decision(
                    agent_id="governance-system",
                    action="policy_deploy",
                    resource_id=f"patch:{patch_id}",
                    allowed=True,
                    policy_version=policy_hash,
                    metadata={
                        "patch_id": patch_id,
                        "policy_hash": policy_hash,
                        "source": "radicle",
                    },
                )
            )

        return {
            "patch_id": patch_id,
            "policy_hash": policy_hash,
            "algorand_tx": receipt.tx_id if receipt else None,
            "deployed": True,
        }

    # ==========================================
    # OPA BUNDLE SYNC
    # ==========================================

    def _sync_to_opa_bundle(self, repo_path: Path):
        """Copia policies do repo Radicle para o OPA bundle dir."""

        bundle_dir = Path(self.config.opa_bundle_dir)

        # Limpa bundle anterior
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        bundle_dir.mkdir(parents=True)

        # Copia .rego files
        for rego_file in repo_path.rglob("*.rego"):
            rel_path = rego_file.relative_to(repo_path)
            dest = bundle_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rego_file, dest)

        # Copia data files
        for json_file in (repo_path / "data").rglob("*.json"):
            rel_path = json_file.relative_to(repo_path)
            dest = bundle_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(json_file, dest)

        # Gera .manifest para OPA
        manifest = {
            "revision": self._get_git_rev(repo_path),
            "roots": ["adr", "data"],
        }
        (bundle_dir / ".manifest").write_text(json.dumps(manifest))

        print(f"OPA bundle synced: {manifest['revision']}")

    # ==========================================
    # REPLICATION & SEEDING
    # ==========================================

    def seed_to_network(self):
        """Replica policies para a rede Radicle (p2p)."""
        repo_path = Path(self.config.rad_home) / "policy-repo"

        for seed in self.config.seed_nodes:
            self._run(
                ["rad", "seed", self.config.policy_rid,
                 "--seed", seed],
                cwd=repo_path,
            )

    def fetch_latest(self):
        """Puxa últimas mudanças da rede."""
        repo_path = Path(self.config.rad_home) / "policy-repo"
        self._run(["rad", "sync", "--fetch"], cwd=repo_path)

    # ==========================================
    # GOVERNANCE METADATA
    # ==========================================

    def _default_roles(self) -> dict:
        return {
            "roles": {
                "reader":   {"actions": ["read", "list", "search"]},
                "proposer": {"actions": ["read", "list", "search", "propose", "draft"]},
                "approver": {"actions": ["read", "list", "search", "approve", "reject"]},
                "admin":    {"actions": ["*"]},
                "auditor":  {"actions": ["read", "list", "search", "audit", "export"]},
            }
        }

    def _default_agent_config(self) -> dict:
        return {
            "agents": {},
            "defaults": {
                "rate_limit_per_hour": 20,
                "operation_window": {"start": 6, "end": 22},
                "require_mfa_for": ["approve", "supersede", "deprecate"],
            },
        }

    def _governance_readme(self) -> str:
        return """# ADR-Ledger Policy Governance

## How to propose a policy change

1. Create a Radicle patch with your changes
2. At least 2 approvers must review
3. On merge, policies auto-deploy to OPA
4. Every deployment is recorded on Algorand

## Policy Structure

- `adr/*.rego` — OPA policy files
- `data/*.json` — Policy data (roles, configs)
- `.manifest` — OPA bundle manifest

## Verification

All policy deployments have an Algorand transaction ID.
Anyone can verify the audit trail on-chain.
"""

    # ==========================================
    # UTILS
    # ==========================================

    def _run(self, cmd: list[str], cwd: Path = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd, cwd=cwd, env={**self._env},
            capture_output=True, text=True, check=True,
        )

    @staticmethod
    def _get_git_rev(repo_path: Path) -> str:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path, capture_output=True, text=True,
        )
        return result.stdout.strip()

    @staticmethod
    def _hash_policy_dir(repo_path: Path) -> str:
        hasher = hashlib.sha256()
        for f in sorted(repo_path.rglob("*.rego")):
            hasher.update(f.read_bytes())
        for f in sorted(repo_path.rglob("*.json")):
            hasher.update(f.read_bytes())
        return hasher.hexdigest()

    @staticmethod
    def _short_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()[:8]
