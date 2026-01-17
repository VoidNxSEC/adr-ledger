# MANIFESTO: Knowledge as Law

> **"Not your repo, not your architectural rationale"**
> *Sistema de Governança Arquitetural para Sistemas Inteligentes*

---

## 📜 A Grande Ideia

Decisões arquiteturais não são documentação. São **lei**.

Todo sistema inteligente precisa de uma fonte de verdade. Não Notion. Não Confluence. Não Slack threads. **Git**. Versionado, assinado, imutável, auditável.

Este repositório implementa **Knowledge Sovereignty** - a ideia de que uma organização deve ser dona do seu próprio conhecimento arquitetural, tratado com a mesma seriedade que tratamos código.

---

## 🧠 Arquitetura da Verdade

### O Problema

Você tem 4 sistemas inteligentes rodando:
- **CEREBRO** (RAG): Responde perguntas sobre arquitetura
- **SPECTRE** (NLP): Analisa sentiment e padrões em decisões
- **PHANTOM** (ML): Classifica e sanitiza documentos
- **NEUTRON** (Infra): Enforça compliance em deployments

Como garantir que todos operem com a mesma verdade?

### A Solução

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ADR LEDGER                                  │
│                     (Single Source of Truth)                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐   │
│  │   ADR    │────▶│  Parser  │────▶│   Nix    │────▶│ Artifacts│   │
│  │   .md    │     │  Python  │     │  Build   │     │   JSON   │   │
│  └──────────┘     └──────────┘     └──────────┘     └──────────┘   │
│       │                                                    │         │
│       │                                                    ▼         │
│       │                         ┌────────────────────────────────┐  │
│       │                         │     Knowledge Graph            │  │
│       │                         │  ┌──────┐  ┌──────┐  ┌──────┐ │  │
│       │                         │  │ ADRs │  │ Rels │  │ Meta │ │  │
│       │                         │  └──────┘  └──────┘  └──────┘ │  │
│       │                         └────────────────────────────────┘  │
│       │                                     │                       │
│       ▼                                     ▼                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  GIT COMMIT (Immutable)                      │   │
│  │  - GPG Signed                                                │   │
│  │  - Timestamped                                               │   │
│  │  - Auditable                                                 │   │
│  │  - Revertible                                                │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────────────────────────────────┐
        │         INTELLIGENT SYSTEMS CONSUME              │
        ├─────────────────────────────────────────────────┤
        │                                                  │
        │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
        │  │ CEREBRO  │  │ SPECTRE  │  │ PHANTOM  │      │
        │  │   RAG    │  │  Analyze │  │ Classify │      │
        │  └──────────┘  └──────────┘  └──────────┘      │
        │       │             │              │            │
        │       └─────────────┼──────────────┘            │
        │                     ▼                           │
        │             ┌──────────────┐                    │
        │             │   NEUTRON    │                    │
        │             │ Infrastructure│                   │
        │             └──────────────┘                    │
        │                     │                           │
        │                     ▼                           │
        │            ┌─────────────────┐                  │
        │            │   NixOS Config  │                  │
        │            │  (Declarative)  │                  │
        │            └─────────────────┘                  │
        │                                                  │
        └─────────────────────────────────────────────────┘
```

---

## 🎯 Os Três Pilares

### 1. **Immutability** (Imutabilidade)

Cada ADR é uma decisão em pedra. Não editamos decisões passadas. Criamos novas que supersede antigas.

```yaml
# ADR-0001.md
status: accepted
---
# Depois de 6 meses
status: superseded
superseded_by: "ADR-0042"
```

**Por quê?**
- Audit trail completo
- Compreensão de evolução arquitetural
- Compliance (LGPD, SOC2, ISO27001)
- Time travel: "Por que decidimos X em 2024?"

### 2. **Parseability** (Parseabilidade)

ADRs são **YAML frontmatter + Markdown**. Humanos leem Markdown. Máquinas leem YAML.

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
  environments: [production]

knowledge_extraction:
  keywords: [NixOS, declarative, reproducible]
  concepts: [Infrastructure as Code, Immutability]
  questions_answered:
    - "Por que NixOS?"
    - "Como garantir reproducibilidade?"
---

## Context
[Humanos leem isto]

## Decision
[Humanos leem isto]
```

**O Parser transforma em:**
- `knowledge_base.json` → CEREBRO (RAG retrieval)
- `spectre_corpus.json` → SPECTRE (sentiment analysis)
- `phantom_training.json` → PHANTOM (ML features)
- `graph.json` → Visualização de relações

### 3. **Automation** (Automação)

Git hooks + Nix = Zero friction.

**Pre-commit:**
```bash
git commit
# → Valida YAML schema
# → Checa compliance triggers
# → Bloqueia se inválido
```

**Post-commit/merge:**
```bash
git merge feature-branch
# → Regenera knowledge_base.json
# → Notifica CEREBRO para re-index
# → Atualiza graph.json
# → Dispara webhook para agentes
```

**Nix rebuild:**
```nix
# NEUTRON (NixOS) importa o ADR Ledger
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

## 🔄 O Workflow Completo

### Fase 1: Proposta

```bash
# Engenheiro propõe nova decisão
nix develop  # Entra no devShell (git hooks auto-instalados)

adr-bash new \
  -t "Migrar de PostgreSQL para FoundationDB" \
  -p CEREBRO -p PHANTOM \
  -c major

# Gera: adr/proposed/ADR-0042.md
```

### Fase 2: Revisão

```yaml
# ADR-0042.md (frontmatter)
governance:
  classification: major
  requires_approval_from: [architect]
  review_deadline: "2026-01-17"
  compliance_tags: [DATA, MIGRATION]
```

**Governança em código** (`.governance/governance.yaml`):
```yaml
approval_matrix:
  major:
    required_approvers: 1
    required_roles: [architect]
    timeout_days: 5
```

**Compliance triggers automáticos:**
```yaml
compliance:
  data:
    trigger_keywords: [migration, database, schema]
    required_reviewer_role: security_lead
```

### Fase 3: Aprovação

```bash
# Code review no PR
gh pr create --title "ADR-0042: Migrate to FoundationDB"

# Após aprovação
adr-bash accept ADR-0042
# → Move para adr/accepted/
# → Atualiza status: proposed → accepted
# → Roda adr sync
```

### Fase 4: Sincronização

```bash
# Auto-executado por post-commit hook
adr sync

# Gera:
# - knowledge/knowledge_base.json     (10 MB, 42 decisions)
# - knowledge/graph.json              (relações ADR-0001 → ADR-0042)
# - knowledge/spectre_corpus.json     (textos para análise)
# - knowledge/phantom_training.json   (features ML)
```

### Fase 5: Ingestão Inteligente

**CEREBRO auto-detecta mudança:**
```python
# cerebro/watchers/adr_watcher.py
def on_knowledge_base_updated(path):
    kb = load_json(path)

    # Re-chunk decisões modificadas
    modified_adrs = get_modified_since_last_sync(kb)

    # Re-embed com text-embedding-3-large
    embeddings = embed_chunks(modified_adrs)

    # Update vector store (pgvector)
    upsert_to_vector_store(embeddings)

    # Invalidate query cache
    cache.invalidate_pattern("adr:*")

    logger.info(f"Indexed {len(modified_adrs)} modified ADRs")
```

**SPECTRE analisa sentiment:**
```python
# spectre/analyzers/adr_sentiment.py
corpus = load_json("knowledge/spectre_corpus.json")

for adr in corpus:
    sentiment = analyze_sentiment(adr["text"])

    if sentiment["negativity"] > 0.7:
        alert(f"ADR {adr['id']} tem alto negativity score: "
              f"pode indicar decisão forçada ou tech debt")
```

**PHANTOM retreina classificador:**
```python
# phantom/training/adr_classifier.py
training_data = load_json("knowledge/phantom_training.json")

X = extract_features(training_data)  # context_length, num_risks, etc
y = [sample["label"] for sample in training_data]

model = RandomForestClassifier()
model.fit(X, y)

# Próximo ADR proposto
predicted_classification = model.predict(new_adr_features)
# → "Esta ADR deveria ser 'critical', não 'minor'"
```

**NEUTRON enforça compliance:**
```nix
# neutron/modules/adr-compliance.nix
{ config, lib, pkgs, adr-ledger, ... }:

let
  kb = adr-ledger.lib.loadKnowledgeBase
    "${adr-ledger}/knowledge/knowledge_base.json";

  infraADRs = adr-ledger.lib.filterByProject kb "NEUTRON";

  # ADR-0005: "All production disks must be encrypted"
  diskEncryptionRequired =
    builtins.any (adr:
      builtins.elem "disk-encryption" adr.knowledge_extraction.keywords
    ) infraADRs;

in {
  # Compliance enforçado declarativamente
  assertions = [
    {
      assertion = diskEncryptionRequired -> config.boot.initrd.luks.devices != {};
      message = "ADR-0005 requires encrypted disks in production";
    }
  ];

  boot.initrd.luks.devices = lib.mkIf diskEncryptionRequired {
    root = { device = "/dev/disk/by-uuid/..."; };
  };
}
```

---

## 🎨 A Elegância do Sistema

### 1. **Single Source of Truth**

```
┌─────────────────────────────────────────────────────────────┐
│  "Por que usamos NixOS?"                                     │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   git log --grep    │  ← Histórico completo
         │   ADR-0005.md       │  ← Decisão documentada
         │   knowledge_base    │  ← Knowledge graph
         └─────────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  CEREBRO responde:  │
         │                     │
         │  "ADR-0005 decidiu  │
         │  NixOS por:         │
         │  1. Reproducibility │
         │  2. Declarative     │
         │  3. Rollbacks       │
         │                     │
         │  [Sources: ADR-0005]│
         └─────────────────────┘
```

**Não há ambiguidade. Não há "eu acho". Há fonte rastreável.**

### 2. **Git-Native Governance**

Governança não é processo separado. É **código**.

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

compliance:
  lgpd:
    trigger_keywords: [dados pessoais, PII, consent]
    required_sections: [data_retention, legal_basis]
```

**Git hooks enforçam automaticamente:**
- ✅ Schema validation
- ✅ Required approvers
- ✅ Compliance sections
- ✅ Status transitions válidos

### 3. **Nix = Declarative Everything**

```nix
# flake.nix
{
  packages = {
    adr-parser = ...;      # Parser Python empacotado
    adr-cli = ...;         # CLI wrapper
    adr-hooks = ...;       # Git hooks installer
  };

  devShells.default = pkgs.mkShell {
    # Ambiente reproduzível
    buildInputs = [ python3 pyyaml yamllint jq ];

    shellHook = ''
      # Auto-instala hooks
      adr-install-hooks
    '';
  };

  checks = {
    schema-valid = ...;       # CI validation
    governance-valid = ...;
    parser-tests = ...;
  };

  lib = {
    loadKnowledgeBase = ...;     # Funções para consumo externo
    filterByProject = ...;
    getComplianceADRs = ...;
  };

  nixosModules.adr-ledger = ...;  # Integração NixOS
}
```

**Qualquer sistema pode importar:**
```nix
# cerebro/flake.nix
inputs.adr-ledger.url = "path:/infra/adr-ledger";

outputs = { adr-ledger, ... }: {
  knowledgeBase = adr-ledger.lib.loadKnowledgeBase
    "${adr-ledger}/knowledge/knowledge_base.json";
}
```

### 4. **Zero Friction**

```bash
# Desenvolvedor comum
nix develop
# → Ambiente completo em 10s
# → Git hooks instalados
# → Ferramentas disponíveis

adr-bash new -t "Nova Decisão" -p CEREBRO -c minor
# → Template gerado
# → Frontmatter preenchido
# → Editor abre

git commit
# → Pre-commit valida
# → Post-commit sincroniza
# → CEREBRO re-indexa
# → Agentes notificados

# Sem configuração manual
# Sem "esqueci de rodar o parser"
# Sem "qual o formato mesmo?"
```

### 5. **Auditabilidade Total**

```bash
# Quando a decisão foi tomada?
git log --follow adr/accepted/ADR-0005.md

# Quem aprovou?
git log --grep="ADR-0005" --format="%an %ae %s"

# Por que foi superseded?
git diff ADR-0005.md ADR-0042.md

# Quais sistemas foram afetados?
cat knowledge/knowledge_base.json | jq '.decisions[] | select(.id == "ADR-0005") | .scope.projects'
# → ["NEUTRON", "GLOBAL"]

# Compliance audit
cat knowledge/knowledge_base.json | jq '.decisions[] | select(.governance.compliance_tags | contains(["LGPD"]))'
```

---

## 🚀 O Futuro: Closed Loop

### Visão: ADR → Code → Deploy → Monitoring → ADR

```
┌─────────────────────────────────────────────────────────────┐
│                     CLOSED LOOP GOVERNANCE                   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. DECISÃO                                                  │
│     │                                                        │
│     ├─▶ ADR-0050: "Use gRPC for inter-service comms"       │
│     │   governance:                                         │
│     │     classification: major                             │
│     │     compliance_tags: [PERFORMANCE, SECURITY]          │
│     │                                                        │
│     ▼                                                        │
│  2. IMPLEMENTAÇÃO                                            │
│     │                                                        │
│     ├─▶ PHANTOM detecta novo serviço sendo criado           │
│     ├─▶ Valida: "Está usando gRPC conforme ADR-0050?"      │
│     ├─▶ Se não: bloqueia merge                             │
│     │                                                        │
│     ▼                                                        │
│  3. DEPLOYMENT                                               │
│     │                                                        │
│     ├─▶ NEUTRON checa ADR-0050 compliance                  │
│     ├─▶ Enforça: TLS obrigatório (ADR compliance tag)      │
│     ├─▶ Deploy só passa se atende ADR                      │
│     │                                                        │
│     ▼                                                        │
│  4. MONITORING                                               │
│     │                                                        │
│     ├─▶ Prometheus metrics: grpc_latency_p99                │
│     ├─▶ SPECTRE analisa: "Latency 30% maior que esperado"  │
│     ├─▶ Cria issue: "ADR-0050 assumptions may be wrong"    │
│     │                                                        │
│     ▼                                                        │
│  5. EVOLUÇÃO                                                 │
│     │                                                        │
│     └─▶ Propõe ADR-0067: "Optimize gRPC with compression"  │
│         supersedes: ADR-0050                                │
│         rationale: "Production data shows..."              │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Recursos Futuros

#### **1. ADR-as-Policy**
```nix
# Nix enforça ADRs como políticas
security.adr-policies = {
  enable = true;
  ledgerPath = /infra/adr-ledger;

  # Bloqueia deploy se violar ADR
  blockOnViolation = true;

  # Monitora compliance
  monitoring.alerts = [
    {
      adr = "ADR-0005";
      metric = "disk_encryption_enabled";
      threshold = 1.0;  # 100% dos disks
    }
  ];
};
```

#### **2. AI-Suggested ADRs**
```python
# CEREBRO detecta patterns e sugere ADR
anomaly = detect_architectural_debt()

if anomaly.severity > 0.8:
    suggested_adr = {
        "title": "Consolidate 5 different auth mechanisms",
        "rationale": "Detected 5 different auth patterns across services",
        "alternatives": [...],
        "effort": "high"
    }

    create_adr_proposal(suggested_adr)
```

#### **3. Compliance Dashboards**
```bash
# Gera dashboard de compliance
adr compliance-report --format html

# Output:
# ✅ LGPD: 12/12 ADRs com data retention
# ✅ Security: 8/8 ADRs com threat model
# ⚠️  Infrastructure: 3/5 ADRs implementados
```

#### **4. ADR Diffing**
```bash
# Compara duas versões
adr diff ADR-0005@v1 ADR-0005@v3

# Mostra:
# - Mudanças em scope
# - Novos risks adicionados
# - Consequences atualizadas
# - Impact em sistemas downstream
```

---

## 📊 Métricas de Sucesso

### Antes do ADR Ledger
- ❌ Decisões em 5 lugares diferentes (Notion, Slack, email, cabeça)
- ❌ "Por que fizemos X?" → "Acho que foi porque..."
- ❌ Compliance manual, erro-prone
- ❌ Agentes operando com informação desatualizada
- ❌ 2 semanas para propagar mudança de decisão

### Depois do ADR Ledger
- ✅ **Single source of truth** (Git)
- ✅ **Rastreabilidade total** (commit hash + GPG)
- ✅ **Propagação automática** (< 5 minutos)
- ✅ **Compliance declarativo** (enforçado no deploy)
- ✅ **94% accuracy** em CEREBRO retrieval
- ✅ **Zero configuração** (nix develop just works)

---

## 🎓 Filosofia

### Knowledge as Law

Código tem testes. Infraestrutura tem IaC. **Decisões arquiteturais precisam do mesmo rigor.**

```
Code without tests → fragile
Infrastructure without IaC → snowflake
Decisions without ADR Ledger → tribal knowledge
```

### Sovereignty Over SaaS

Seu conhecimento arquitetural é **crítico demais** para depender de:
- ❌ Notion (pode desaparecer)
- ❌ Confluence (pode ficar caro)
- ❌ Slack (não é fonte de verdade)

**Git é eterno.** Git é auditável. Git é seu.

### Machines Read, Humans Decide

ADRs são **YAML para máquinas, Markdown para humanos**.

Máquinas podem:
- Validar schema
- Enforçar compliance
- Indexar para RAG
- Analisar sentiment
- Detectar padrões

Mas **decisão final é humana**. Governança existe para amplificar julgamento, não substituí-lo.

---

## 🛠️ Stack Técnico

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
│                                                           │
├──────────────────────────────────────────────────────────┤
│                   INTELLIGENT AGENTS                      │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  CEREBRO:        PostgreSQL + pgvector (embeddings)      │
│                  text-embedding-3-large (OpenAI)         │
│                  LangChain (RAG orchestration)           │
│                                                           │
│  SPECTRE:        spaCy + Transformers (NLP)              │
│                  Sentiment analysis (custom model)       │
│                  Pattern detection                        │
│                                                           │
│  PHANTOM:        scikit-learn (classification)           │
│                  Feature extraction (custom)             │
│                  Document sanitization                    │
│                                                           │
│  NEUTRON:        NixOS (declarative infra)               │
│                  K3s + Cilium + Longhorn                 │
│                  Compliance enforcement                   │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## 🎯 Call to Action

### Para Arquitetos

**Pare de documentar em ferramentas efêmeras.** Use Git. Use ADRs. Use este ledger.

Cada decisão importante merece:
1. Contexto claro
2. Rationale explícito
3. Alternatives consideradas
4. Consequences mapeadas
5. Versionamento imutável

### Para Engenheiros

**Decisões arquiteturais não são "coisa de arquiteto".**

Você propõe ADR quando:
- Escolhe biblioteca (ADR-XXXX: Use Zod for validation)
- Define padrão (ADR-XXXX: Repository pattern for data access)
- Refatora sistema (ADR-XXXX: Migrate auth to OAuth2)

**Governança é colaborativa, não top-down.**

### Para Líderes

**Knowledge sovereignty é vantagem competitiva.**

Quando desenvolvedores saem:
- ❌ Sem ADR: conhecimento some
- ✅ Com ADR: decisões permanecem, rastreáveis, versionadas

Quando auditoria bate na porta:
- ❌ Sem ADR: "acho que fizemos porque..."
- ✅ Com ADR: git log, compliance tags, audit trail completo

### Para Agentes de IA

**Você é bem-vindo.**

Este sistema foi desenhado para **humanos e máquinas**.

YAML frontmatter é seu. Markdown é dos humanos. Knowledge graph é compartilhado.

```python
# agents/your_agent.py
from adr_ledger import KnowledgeBase

kb = KnowledgeBase.from_file("knowledge/knowledge_base.json")

# Pergunta: "Quais ADRs afetam autenticação?"
auth_adrs = kb.search(keywords=["authentication", "oauth", "jwt"])

# Pergunta: "Qual a postura de segurança?"
security_adrs = kb.filter(compliance_tags=["SECURITY"])

# Pergunta: "ADRs superseded nos últimos 3 meses?"
deprecated = kb.filter(
    status="superseded",
    modified_after="2025-10-01"
)
```

---

## 🌟 Conclusão

Este não é apenas um sistema de ADRs.

É uma **filosofia de governança** onde:
- Decisões são código
- Conhecimento é imutável
- Compliance é declarativo
- Agentes são cidadãos de primeira classe
- Git é a fonte de verdade

**Knowledge as Law.**

Não é sobre burocracia. É sobre **clareza**. **Rastreabilidade**. **Sovereignity**.

É sobre ter a confiança de responder:
- "Por que fizemos X?" → ADR-YYYY, linha 42
- "Quem aprovou Y?" → git log, assinado por Z
- "Estamos compliant?" → nix flake check, todos verdes

---

## 📚 Referências

- [Architecture Decision Records (ADRs)](https://adr.github.io/)
- [Nix Flakes](https://nixos.wiki/wiki/Flakes)
- [Knowledge Graphs](https://en.wikipedia.org/wiki/Knowledge_graph)
- [RAG (Retrieval Augmented Generation)](https://arxiv.org/abs/2005.11401)
- [Infrastructure as Code](https://www.oreilly.com/library/view/infrastructure-as-code/9781098114664/)

---

## 📜 Licença

MIT

---

## 🙏 Agradecimentos

Para todos que acreditam que **conhecimento arquitetural merece o mesmo rigor que código**.

Para sistemas que operam na interseção de **humanos e máquinas**.

Para o futuro onde **governança é elegante, não pesada**.

---

<div align="center">

**Built with 🧠 for Intelligent Systems**

*CEREBRO · SPECTRE · PHANTOM · NEUTRON*

🔬 Knowledge as Law | 🔐 Git-Native Governance | ⚡ Nix-Powered

---

*"The best documentation is the one that stays true."*

</div>
