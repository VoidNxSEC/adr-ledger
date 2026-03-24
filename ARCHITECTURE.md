# Arquitetura do ADR Ledger

> Sistema de governança arquitetural para sistemas inteligentes.

---

## O Problema

Quatro agentes de IA operam sobre a mesma base de conhecimento arquitetural:

- **CEREBRO** (RAG) — responde perguntas sobre arquitetura
- **SPECTRE** (NLP) — analisa padrões em decisões
- **PHANTOM** (ML) — classifica e sanitiza documentos
- **NEUTRON** (Infra) — enforça compliance em deployments

Sem uma fonte de verdade centralizada, cada agente opera com informação potencialmente desatualizada ou inconsistente. Decisões se fragmentam entre Notion, Slack threads e memória de quem estava na sala.

## A Solução

Um repositório Git que trata decisões arquiteturais como dados estruturados. YAML frontmatter para máquinas, Markdown para humanos. Tudo versionado, assinado e auditável.

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ADR LEDGER                                  │
│                     (Source of Truth)                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐   │
│  │   ADR    │────▶│  Parser  │────▶│   Nix    │────▶│ Artifacts│   │
│  │   .md    │     │  Python  │     │  Build   │     │   JSON   │   │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘   │
│       │                                                    │         │
│       ▼                                                    ▼         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  GIT COMMIT (Immutable)                      │   │
│  │  - GPG Signed · Timestamped · Auditable · Revertible        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌──────────────────────────────────────────────┐
        │          AGENTES CONSOMEM                     │
        ├──────────────────────────────────────────────┤
        │  CEREBRO (RAG) · SPECTRE (NLP) · PHANTOM (ML)│
        │              │                                │
        │              ▼                                │
        │     NEUTRON (Infrastructure)                  │
        │              │                                │
        │              ▼                                │
        │      NixOS Config (Declarative)               │
        └──────────────────────────────────────────────┘
```

---

## Princípios de Design

### 1. Imutabilidade

Cada ADR é um registro. Não editamos decisões passadas — criamos novas que supersede as antigas.

```yaml
# ADR-0001.md
status: accepted
---
# Depois de 6 meses
status: superseded
superseded_by: "ADR-0042"
```

Motivo: audit trail completo, compreensão de evolução arquitetural, compliance (LGPD, SOC2, ISO27001), e a capacidade de responder "por que decidimos X em 2024?".

### 2. Parseabilidade

ADRs são YAML frontmatter + Markdown. Humanos leem Markdown. Máquinas leem YAML.

```yaml
---
id: "ADR-0005"
title: "NixOS como Base Declarativa"
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
    - "Por que NixOS?"
    - "Como garantir reproducibilidade?"
---
```

O Parser transforma ADRs em:
- `knowledge_base.json` → CEREBRO (RAG retrieval)
- `spectre_corpus.json` → SPECTRE (análise de padrões)
- `phantom_training.json` → PHANTOM (features de ML)
- `graph.json` → Grafo de relações entre decisões

### 3. Automação

Git hooks + Nix eliminam friction no workflow.

**Pre-commit:** valida YAML schema, checa compliance triggers, bloqueia se inválido.

**Post-commit:** regenera knowledge_base.json, notifica agentes, atualiza graph.

**Nix rebuild:**
```nix
# NEUTRON importa o ADR Ledger
inputs.adr-ledger.url = "path:/infra/adr-ledger";

# Extrai compliance rules
complianceRules = adr-ledger.lib.getComplianceADRs knowledgeBase;

# Enforça declarativamente
boot.initrd.luks.devices =
  if (hasRule complianceRules "disk-encryption")
  then { root = { device = "/dev/sda2"; }; }
  else {};
```

---

## Workflow Completo

### Fase 1: Proposta

```bash
nix develop  # devShell com git hooks auto-instalados

adr new \
  -t "Migrar de PostgreSQL para FoundationDB" \
  -p CEREBRO -p PHANTOM \
  -c major

# Gera: adr/proposed/ADR-0042.md
```

### Fase 2: Revisão

Governança em código (`.governance/governance.yaml`):
```yaml
approval_matrix:
  major:
    required_approvers: 1
    required_roles: [architect]
    timeout_days: 5
```

Compliance triggers automáticos:
```yaml
compliance:
  data:
    trigger_keywords: [migration, database, schema]
    required_reviewer_role: security_lead
```

### Fase 3: Aprovação

```bash
# Após code review no PR
adr accept ADR-0042
# → Move para adr/accepted/
# → Atualiza status
# → Roda adr sync
```

### Fase 4: Sincronização

```bash
# Auto-executado por post-commit hook
adr sync

# Gera:
# - knowledge/knowledge_base.json
# - knowledge/graph.json
# - knowledge/spectre_corpus.json
# - knowledge/phantom_training.json
```

### Fase 5: Ingestão pelos Agentes

**CEREBRO** detecta mudança, re-chunks ADRs modificados, gera embeddings (text-embedding-3-large), atualiza vector store (pgvector), invalida cache.

**SPECTRE** analisa sentiment do corpus — negativity score alto pode indicar decisão forçada ou tech debt.

**PHANTOM** retreina classificador com features extraídas dos ADRs (context_length, num_risks, etc).

**NEUTRON** enforça compliance declarativamente via NixOS modules:
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

## Propriedades do Sistema

### Source of Truth única

```
"Por que usamos NixOS?"
    → git log --grep ADR-0005
    → ADR-0005.md (decisão documentada)
    → knowledge_base.json (knowledge graph)
    → CEREBRO responde com citações e fontes
```

Sem ambiguidade. Fonte rastreável.

### Governança Git-native

Governança não é processo separado — é código versionado no mesmo repo.

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

Git hooks enforçam automaticamente: schema validation, required approvers, compliance sections, status transitions válidos.

### Nix: Declarative Everything

```nix
{
  packages = {
    adr-parser = ...;      # Parser Python empacotado
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

Qualquer sistema importa via flake input:
```nix
inputs.adr-ledger.url = "path:/infra/adr-ledger";
```

### Zero friction

```bash
nix develop        # Ambiente completo, hooks instalados
adr new -t "..." -p CEREBRO -c minor  # Template gerado
git commit         # Pre-commit valida, post-commit sincroniza
```

Sem configuração manual. Sem "esqueci de rodar o parser".

### Auditabilidade

```bash
git log --follow adr/accepted/ADR-0005.md    # Quando
git log --grep="ADR-0005" --format="%an %s"  # Quem aprovou
git diff ADR-0005.md ADR-0042.md             # Por que mudou

# Compliance audit
cat knowledge/knowledge_base.json | \
  jq '.decisions[] | select(.governance.compliance_tags | contains(["LGPD"]))'
```

---

## Visão de Futuro: Closed Loop

ADR → Code → Deploy → Monitoring → ADR

```
1. DECISÃO
   ADR-0050: "Use gRPC for inter-service comms"
       ↓
2. IMPLEMENTAÇÃO
   PHANTOM valida: "Está usando gRPC conforme ADR-0050?"
   Se não: bloqueia merge
       ↓
3. DEPLOYMENT
   NEUTRON checa compliance, enforça TLS obrigatório
       ↓
4. MONITORING
   SPECTRE analisa: "Latency 30% maior que esperado"
   Cria issue: "ADR-0050 assumptions may be wrong"
       ↓
5. EVOLUÇÃO
   Propõe ADR-0067: "Optimize gRPC with compression"
   supersedes: ADR-0050
   rationale: "Production data shows..."
```

### Recursos planejados

**ADR-as-Policy**: Nix enforça ADRs como políticas de deploy, bloqueando violações e monitorando compliance.

**AI-Suggested ADRs**: CEREBRO detecta padrões anômalos e sugere ADRs automaticamente.

**Compliance Dashboards**: `adr compliance-report --format html` com status por framework.

**ADR Diffing**: `adr diff ADR-0005@v1 ADR-0005@v3` com mudanças em scope, risks e consequences.

---

## Stack Técnico

```
┌──────────────────────────────────────────────────────────┐
│                    ADR LEDGER STACK                       │
├──────────────────────────────────────────────────────────┤
│                                                           │
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
│                                                           │
├──────────────────────────────────────────────────────────┤
│                   AGENTES                                 │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  CEREBRO:        pgvector + text-embedding-3-large       │
│  SPECTRE:        spaCy + Transformers (NLP)              │
│  PHANTOM:        scikit-learn (classification)           │
│  NEUTRON:        NixOS (declarative infra)               │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## Referências

- [Architecture Decision Records (ADRs)](https://adr.github.io/)
- [Nix Flakes](https://nixos.wiki/wiki/Flakes)
- [Knowledge Graphs](https://en.wikipedia.org/wiki/Knowledge_graph)
- [RAG (Retrieval Augmented Generation)](https://arxiv.org/abs/2005.11401)

## Licença

MIT
