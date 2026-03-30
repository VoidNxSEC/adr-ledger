# ADR Ledger Architecture

> Architectural governance system for intelligent systems.

---

## The Problem

Four AI agents operate on the same architectural knowledge base:

- **CEREBRO** (RAG) — answers questions about architecture
- **SPECTRE** (NLP) — analyzes patterns in decisions
- **PHANTOM** (ML) — classifies and sanitizes documents
- **NEUTRON** (Infra) — enforces compliance in deployments

Without a centralized source of truth, each agent operates with potentially outdated or inconsistent information. Decisions get fragmented across Notion, Slack threads, and the memory of whoever was in the room.

## The Solution

A Git repository that treats architectural decisions as structured data. YAML frontmatter for machines, Markdown for humans. Everything versioned, signed, and auditable.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ADR LEDGER                                 │
│                     (Source of Truth)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐    │
│  │   ADR    │────▶│  Parser  │────▶│   Nix    │────▶│ Artifacts│    │
│  │   .md    │     │  Python  │     │  Build   │     │   JSON   │    │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘    │
│       │                                                    │        │
│       ▼                                                    ▼        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                  GIT COMMIT (Immutable)                     │    │
│  │  - GPG Signed · Timestamped · Auditable · Revertible        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────┐
        │               AGENTS CONSUME                 │
        ├──────────────────────────────────────────────┤
        │ CEREBRO (RAG) · SPECTRE (NLP) · PHANTOM (ML) │
        │              │                               │
        │              ▼                               │
        │     NEUTRON (Infrastructure)                 │
        │              │                               │
        │              ▼                               │
        │      NixOS Config (Declarative)              │
        └──────────────────────────────────────────────┘
```

---

## Design Principles

### 1. Immutability

Each ADR is a record. We do not edit past decisions — we create new ones that supersede the old ones.

```yaml
# ADR-0001.md
status: accepted
---
# 6 months later
status: superseded
superseded_by: "ADR-0042"
```

Reason: Complete audit trail, understanding of architectural evolution, compliance (LGPD, SOC2, ISO27001), and the ability to answer "why did we decide X in 2024?".

### 2. Parseability

ADRs are YAML frontmatter + Markdown. Humans read Markdown. Machines read YAML.

```yaml
---
id: "ADR-0005"
title: "NixOS as Declarative Base"
status: accepted
classification: critical

governance:
  requires_approval_from: [architect, security_lead]
  compliance_tags: [INFRASTRUCTURE, SECURITY]

scope:
  projects: [NEUTRON, GLOBAL]
  layers: [infrastructure]

knowledge_extraction:
  keywords: [NixOS, declarative, reproducible]
  concepts: [Infrastructure as Code, Immutability]
  questions_answered:
    - "Why NixOS?"
    - "How to guarantee reproducibility?"
---
```

The Parser transforms ADRs into:
- `knowledge_base.json` → CEREBRO (RAG retrieval)
- `spectre_corpus.json` → SPECTRE (pattern analysis)
- `phantom_training.json` → PHANTOM (ML features)
- `graph.json` → Decision relationship graph

### 3. Automation

Git hooks + Nix eliminate friction in the workflow.

**Pre-commit:** Validates YAML schema, checks compliance triggers, blocks if invalid.

**Post-commit:** Regenerates knowledge_base.json, notifies agents, updates graph.

**Nix rebuild:**
```nix
# NEUTRON imports the ADR Ledger
inputs.adr-ledger.url = "path:/infra/adr-ledger";

# Extracts compliance rules
complianceRules = adr-ledger.lib.getComplianceADRs knowledgeBase;

# Enforces declaratively
boot.initrd.luks.devices =
  if (hasRule complianceRules "disk-encryption")
  then { root = { device = "/dev/sda2"; }; }
  else {};
```

---

## Complete Workflow

### Phase 1: Proposal

```bash
nix develop  # devShell with auto-installed git hooks

adr new \
  -t "Migrate from PostgreSQL to FoundationDB" \
  -p CEREBRO -p PHANTOM \
  -c major

# Generates: adr/proposed/ADR-0042.md
```

### Phase 2: Review

Governance as code (`.governance/governance.yaml`):
```yaml
approval_matrix:
  major:
    required_approvers: 1
    required_roles: [architect]
    timeout_days: 5
```

Automatic compliance triggers:
```yaml
compliance:
  data:
    trigger_keywords: [migration, database, schema]
    required_reviewer_role: security_lead
```

### Phase 3: Approval

```bash
# After code review in the PR
adr accept ADR-0042
# → Moves to adr/accepted/
# → Updates status
# → Runs adr sync
```

### Phase 4: Synchronization

```bash
# Auto-executed by post-commit hook
adr sync

# Generates:
# - knowledge/knowledge_base.json
# - knowledge/graph.json
# - knowledge/spectre_corpus.json
# - knowledge/phantom_training.json
```

### Phase 5: Agent Ingestion

**CEREBRO** detects change, re-chunks modified ADRs, generates embeddings (text-embedding-3-large), updates vector store (pgvector), invalidates cache.

**SPECTRE** analyzes sentiment of the corpus — high negativity score may indicate forced decision or tech debt.

**PHANTOM** retrains classifier with features extracted from ADRs (context_length, num_risks, etc).

**NEUTRON** enforces compliance declaratively via NixOS modules:
```nix
{ config, lib, pkgs, adr-ledger, ... }:
let
  kb = adr-ledger.lib.loadKnowledgeBase
    "${adr-ledger}/knowledge/knowledge_base.json";
  infraADRs = adr-ledger.lib.filterByProject kb "NEUTRON";
  diskEncryptionRequired =
    builtins.any (adr:
      builtins.elem "disk-encryption" adr.knowledge_extraction.keywords
    ) infraADRs;
in {
  assertions = [
    {
      assertion = diskEncryptionRequired -> config.boot.initrd.luks.devices != {};
      message = "ADR-0005 requires encrypted disks in production";
    }
  ];
}
```

---

## System Properties

### Single Source of Truth

```
"Why do we use NixOS?"
    → git log --grep ADR-0005
    → ADR-0005.md (documented decision)
    → knowledge_base.json (knowledge graph)
    → CEREBRO responds with citations and sources
```

No ambiguity. Traceable source.

### Git-native Governance

Governance is not a separate process — it is versioned code in the same repo.

```yaml
# .governance/governance.yaml
approval_matrix:
  critical:
    required_approvers: 2
    required_roles: [architect, security_lead]
    timeout_days: 7

lifecycle:
  states:
    proposed:
      allowed_transitions: [accepted, rejected]
      max_duration_days: 14
```

Git hooks automatically enforce: schema validation, required approvers, compliance sections, valid status transitions.

### Nix: Declarative Everything

```nix
{
  packages = {
    adr-parser = ...;      # Packaged Python parser
    adr-cli = ...;         # CLI wrapper
    adr-hooks = ...;       # Git hooks installer
  };

  devShells.default = pkgs.mkShell {
    buildInputs = [ python3 pyyaml yamllint jq ];
    shellHook = ''
      adr-install-hooks
    '';
  };

  checks = {
    schema-valid = ...;
    governance-valid = ...;
    parser-tests = ...;
  };

  lib = {
    loadKnowledgeBase = ...;
    filterByProject = ...;
    getComplianceADRs = ...;
  };

  nixosModules.adr-ledger = ...;
}
```

Any system imports via flake input:
```nix
inputs.adr-ledger.url = "path:/infra/adr-ledger";
```

### Zero friction

```bash
nix develop        # Full environment, hooks installed
adr new -t "..." -p CEREBRO -c minor  # Template generated
git commit         # Pre-commit validates, post-commit syncs
```

No manual configuration. No "I forgot to run the parser".

### Auditability

```bash
git log --follow adr/accepted/ADR-0005.md    # When
git log --grep="ADR-0005" --format="%an %s"  # Who approved
git diff ADR-0005.md ADR-0042.md             # Why it changed

# Compliance audit
cat knowledge/knowledge_base.json | \
  jq '.decisions[] | select(.governance.compliance_tags | contains(["LGPD"]))'
```

---

## Future Vision: Closed Loop

ADR → Code → Deploy → Monitoring → ADR

```
1. DECISION
   ADR-0050: "Use gRPC for inter-service comms"
       ↓
2. IMPLEMENTATION
   PHANTOM validates: "Is it using gRPC per ADR-0050?"
   If not: blocks merge
       ↓
3. DEPLOYMENT
   NEUTRON checks compliance, enforces mandatory TLS
       ↓
4. MONITORING
   SPECTRE analyzes: "Latency 30% higher than expected"
   Creates issue: "ADR-0050 assumptions may be wrong"
       ↓
5. EVOLUTION
   Proposes ADR-0067: "Optimize gRPC with compression"
   supersedes: ADR-0050
   rationale: "Production data shows..."
```

### Planned Features

**ADR-as-Policy**: Nix enforces ADRs as deploy policies, blocking violations and monitoring compliance.

**AI-Suggested ADRs**: CEREBRO detects anomalous patterns and suggests ADRs automatically.

**Compliance Dashboards**: `adr compliance-report --format html` with status per framework.

**ADR Diffing**: `adr diff ADR-0005@v1 ADR-0005@v3` showing changes in scope, risks, and consequences.

---

## Technical Stack

```
┌──────────────────────────────────────────────────────────┐
│                    ADR LEDGER STACK                      │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  Storage:        Git (version control + audit)           │
│  Format:         YAML frontmatter + Markdown             │
│  Validation:     JSON Schema + yamllint                  │
│  Parser:         Python 3 (AST transformation)           │
│  Build:          Nix flakes (reproducible)               │
│  CI:             nix flake check                         │
│  Hooks:          Pre-commit (validate) + Post (sync)     │
│  Distribution:   Nix packages (adr-parser, adr-cli)      │
│  Integration:    NixOS modules + lib functions           │
│  Chain:          Private blockchain (provenance layer)   │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                      AGENTS                              │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  CEREBRO:        pgvector + text-embedding-3-large       │
│  SPECTRE:        spaCy + Transformers (NLP)              │
│  PHANTOM:        scikit-learn (classification)           │
│  NEUTRON:        NixOS (declarative infra)               │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## References

- [Architecture Decision Records (ADRs)](https://adr.github.io/)
- [Nix Flakes](https://nixos.wiki/wiki/Flakes)
- [Knowledge Graphs](https://en.wikipedia.org/wiki/Knowledge_graph)
- [RAG (Retrieval Augmented Generation)](https://arxiv.org/abs/2005.11401)

## License

Apache 2.0
