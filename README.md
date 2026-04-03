# ADR Ledger — Architectural Decision Record Ledger

[!\[License\](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[!\[Status\](https://img.shields.io/badge/status-beta-brightgreen.svg)]()
[!\[Release\](https://img.shields.io/badge/release-v0.1.0-brightgreen.svg)](https://github.com/marcosfpina/adr-ledger/releases/tag/v0.1.0)
[!\[Python\](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[!\[Nix\](https://img.shields.io/badge/nix-flakes-5277C3.svg)](https://nixos.org/)

Computable registry of architectural decisions. Each ADR is versioned in Git, cryptographically signed, validated against a strict schema, evaluated by OPA policy, and exported as JSON for AI agent consumption and programmatic governance enforcement.

> **Beta** — The project has reached Beta. The cryptographic blockchain layer, advanced CLI, OPA policy validation, Temporal Anchoring (OpenTimestamps), Bitcoin-compatible secp256k1 receipts, SBOM governance, and 80+ MCP tools are operational in the Nix environment. Cross-platform non-Nix support is currently in progress.

## Why it exists

Architectural decisions tend to scatter — Notion, Slack, the memory of whoever was in the room. When someone asks "why NixOS?", the answer is reconstructed from fragments, if at all.



This project can enhance the quality from the model languages training and promisse a better experience for organizations and individual developers.



ADR Ledger treats decisions as structured data: YAML frontmatter for machines, Markdown for humans, Git as an audit trail, and cryptographic chains for immutability. Five autonomous agents consume this knowledge:

| Agent          | Function                            | Consumes                |
| -------------- | ----------------------------------- | ----------------------- |
| **CEREBRO**    | RAG Retrieval & Knowledge Vault     | `knowledge_base.json`   |
| **SPECTRE**    | Pattern & Sentiment Analysis (NLP)  | `spectre_corpus.json`   |
| **PHANTOM**    | ML Classification & Sanitization    | `phantom_training.json` |
| **NEUTRON**    | Declarative Infra & Compliance      | ADR compliance tags     |
| **IntelSense** | Security Ops & Intelligence (OSINT) | Security tagged ADRs    |

The result: decisions that are traceable, versioned, cryptographically verifiable, and queryable by both humans and machines.

---

## Architecture

```bash
adr-ledger/
├── .schema/                    # JSON Schema for strict validation
│   ├── adr.schema.json
│   └── stf.schema.json
├── .governance/                # Governance as code (roles, approval matrix)
│   └── governance.yaml
├── .parsers/                   # AST Parser (Python 3.13)
│   └── adr_parser.py
├── .chain/                     # Cryptographic Governance Layer
│   ├── chain_manager.py        # Private blockchain engine
│   ├── merkle_tree.py          # Merkle inclusion proofs
│   ├── sbom_manager.py         # Supply chain & dependency drift governance
│   ├── temporal.py             # OpenTimestamps anchoring
│   ├── pre_sign.py             # Multi-sig management
│   └── economics.py            # Decision quality metrics
├── adr/                        # ADRs by lifecycle status
│   ├── proposed/
│   ├── accepted/
│   ├── superseded/
│   └── rejected/
├── knowledge/                  # Artifacts for Agent Ingestion
│   ├── knowledge_base.json    → CEREBRO & NEUTRON
│   ├── spectre_corpus.json    → SPECTRE
│   ├── phantom_training.json  → PHANTOM
│   └── graph.json             # Entity-Relationship Knowledge Graph
└── scripts/
    └── adr                    # Advanced Operational CLI
    
    # TODO: add new tree improvements, new directories need to be here.
```

## SecureLLM-MCP Integration

ADR Ledger is the foundational knowledge layer for the **SecureLLM-MCP** ecosystem. It provides over **80+ native MCP tools** enabling autonomous agents to interact with the system architecture deeply and securely:

- **Provider & API Management:** LLM connectivity testing, TLS generation.
- **Emergency Framework:** CPU/Memory/SWAP rescue operations, thermal protection.
- **Laptop Defense Framework:** Thermal forensics, rebuild safety checks.
- **Code Analysis:** Deep AST debugging, complexity metrics, dead code detection.
- **Browser Automation:** Web research, scraping, form interaction.
- **Secure Execution:** Ephemeral Nix sandboxes for safe command execution.

Agents can natively query the ADR Ledger, validate new proposals against existing `knowledge_base.json`, and enforce rules during CI/CD.

---

## Quick Start

### NixOS / Nix (Recommended)

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
nix develop          # enters devShell, provisions Python, hooks, and deps
adr list
adr list --delivery-status completed
adr new -t "My Decision" -p CEREBRO -c major
adr validate
adr policy-check
adr bitcoin list
adr sync
```

### Linux (non-Nix)

Requires: `bash`, `python3.13`, `pyyaml`, `pynacl`, `jsonschema`, `git`, `opa`, `openssl`.

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger

# Install Python deps
pip install pyyaml pynacl jsonschema

# Install CLI and git hooks
bash scripts/install.sh

# Usage
adr list
adr new -t "Adopt Redis" -p SPECTRE -c major
bash scripts/opa-validate.sh
./scripts/phantom-scan-check.sh .
adr sync
```

---

## Validation Pipeline

The default validator is now layered:

1. `scripts/validate_adr.py` merges YAML frontmatter with Markdown sections and validates against `.schema/adr.schema.json`.
2. `scripts/opa-validate.sh` evaluates each ADR through `policies/adr/validation.rego`.
3. `.chain/bitcoin_attestation.py` verifies local secp256k1 snapshot receipts under `.chain/bitcoin/receipts/`.

The main entrypoints are:

```bash
adr validate
adr policy-check
adr bitcoin verify-all
```

Implementation details and tradeoffs are documented in [docs/VALIDATION.md](docs/VALIDATION.md).

---

## Workflow

### Scenario 1: New Decision & Cryptographic Pre-Signing

```bash
# Propose a new architecture change
$ adr new -t "Add Redis for API Caching" -p SPECTRE -c critical

# Critical ADRs require multi-sig (e.g., Architect + Security Lead)
$ adr pre-sign ADR-0042
# Generates a pending signature block in .chain/pending_signatures/

# After all required approvals, accept the ADR into the ledger
$ adr accept ADR-0042

# Sync agents, rebuild the Merkle tree, and check SBOM drift
$ adr sync
```

### Scenario 2: Temporal Anchoring (OpenTimestamps)

```bash
# Anchor the current blockchain state to the Bitcoin blockchain for immutable proof
$ adr anchor
# Output: Creating OpenTimestamps proof for chain height 42...
```

### Scenario 3: Policy Validation (OPA)

```bash
# Evaluate ADRs against the local governance policy bundle
$ adr policy-check
# Output: hard denies fail the command, soft warnings are printed per ADR.
```

### Scenario 4: Bitcoin-compatible Snapshot Receipt

```bash
# Generate local secp256k1 key material for attestations
$ adr bitcoin keygen --name kernelcore

# Sign the latest snapshot receipt
$ adr bitcoin attest --signer kernelcore

# Verify every receipt currently stored
$ adr bitcoin verify-all
```

### Scenario 5: Supply Chain Governance (SBOM)

```bash
# Check if current flake.lock dependencies drift from the accepted ADRs
$ adr sbom
# Output: Validating CycloneDX 1.6 SBOM... No drift detected.
```

---

## CLI Reference

```bash
# Core Operations
adr new       # Create new ADR
adr list      # List ADRs by status/project
adr show      # Show ADR details
adr accept    # Accept proposed ADR (triggers blockchain state transition)
adr supersede # Mark as superseded and link bidirectional graph
adr search    # Semantic and full-text search
adr validate  # Validate schema, OPA policy, and cryptographic health report
adr policy-check  # Evaluate OPA/Rego governance policy only
adr sync      # Sync knowledge base, generate JSON artifacts

# Export & Visualization
adr export    # Export as JSON/JSONL (RAG-optimized streaming)
adr graph     # Generate Mermaid graph
adr viz       # Generate visual knowledge graph (dot/svg/html)
adr-phantom-scan  # Run Phantom-backed leak scan with allowlist enforcement

# Cryptographic Governance (.chain)
adr sbom         # Supply chain SBOM & dependency inventory
adr anchor       # Temporal anchoring (OpenTimestamps proofs)
adr pre-sign     # Pre-sign an ADR (Multi-sig setup)
adr pending-sigs # Manage and view pending signatures
adr bitcoin      # Bitcoin-compatible secp256k1 attestation helpers
```

---

## Governance as Code

Governance is automated, not a manual process. Defined in `.governance/governance.yaml`:

### Compliance Automation

The system uses Git hooks (Pre-commit/Post-commit) to enforce:

- **Approval Matrix**: `critical` requires 2 signatures (Architect + Security Lead).
- **Compliance Triggers**: ADRs modifying `data` layers automatically require the `LGPD` tag.
- **Supply Chain Drift**: `post-commit` verifies if new Nix flake inputs map to an accepted ADR.
- **Integrity**: Validates the private blockchain Merkle root against tampered markdown files.

```yaml
compliance:
  lgpd:
    trigger_keywords: ["PII", "personal data", "user data"]
    required_tags: ["LGPD"]
    required_sections: ["data_retention"]
    required_reviewer_role: "security_lead"

chain:
  require_signatures: true
  merkle_tree:
    enabled: true
  supply_chain:
    drift_detection:
      enabled: true
      check_on_commit: true
```

---

## ADR Schema

Each ADR is validated against `.schema/adr.schema.json`:

```yaml
---
id: "ADR-0042"
title: "Decision Title"
status: accepted  # proposed | accepted | rejected | deprecated | superseded
date: "2026-02-15"

authors:
  - name: "Pina"
    role: "Security Engineer"

governance:
  classification: "major"  # critical | major | minor | patch
  compliance_tags: ["SECURITY", "INFRA"]

scope:
  projects: [IntelSense, NEUTRON, INTELAGENT]
  layers: [infrastructure, security, application]
  environments: [production]

delivery:
  status: completed  # planned | in_progress | completed | blocked | deferred | cancelled
  completed_at: "2026-04-01"
  evidence:
    - "crates/core/tests/phantom_worker.rs"
    - "docs/release-checklist.md"

knowledge_extraction:
  keywords: ["OSINT", "spider-nix"]
  concepts: ["Threat Intelligence"]
  questions_answered:
    - "How do we gather external threat feeds?"
---

## Context
...
```

---

## Roadmap

### v0.1.0 — Beta Release (Current)

- JSON Schema, AST Parser, Advanced CLI
- Pre-commit & Post-commit Git hooks integration
- JSON/JSONL streaming export with deep filtering
- Cryptographic private blockchain layer (Provenance + Immutability)
- Ed25519 Cryptographic signing & Multi-sig (`pre-sign`)
- Temporal Anchoring via OpenTimestamps
- Supply Chain drift detection (SBOM Governance)
- 80+ MCP tools for SecureLLM-MCP Integration
- CI/CD (GitHub Actions + Phantom secret scan wrapper)

### Phase 3: Security & Ecosystem Integration

- `NixOS module` — `services.adr-ledger.enable = true`
- Integration with GitHub Teams as the source of truth for IAM roles
- Standalone Binary Packaging (Linux x86\_64, `.deb`, `.rpm`)
- Package submission to official `nixpkgs` (`unstable` channel)
- `nix-darwin` + Home Manager for declarative macOS

### Phase 4: Full Automation

- Automatic ADR generation from Git commits (Detection Engine)
- Predictive impact analysis using `SPECTRE`
- Decentralized multi-repo federation (ADR-0049)

---

## Contributing

Areas of interest:

- **Parsers**: Support for other formats (MADR, Y-statements)
- **Validators**: New compliance frameworks (HIPAA, PCI-DSS)
- **Visualizations**: Advanced interactive graph layouts

## License

Apache 2.0 — see [LICENSE](LICENSE).

---

Additional documentation:

- [Architecture](ARCHITECTURE.md) — Design principles and detailed vision
- [Daemon Integration](docs/DAEMON.md) — NixOS modules, agent users, and SecureLLM-MCP backend model
- [Export Guide](docs/EXPORT_GUIDE.md) — Complete export documentation
- [Release Roadmap](docs/RELEASE_ROADMAP.md) — Publication plan for the next public release
- [Platforms](docs/PLATFORMS.md) — Setup on NixOS, Linux, macOS, and Windows
- [Contributing](CONTRIBUTING.md) — Setup and contribution guide
