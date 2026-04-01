PROPOR MUDANÇA DE POLICY:
══════════════════════════

Agent (proposer)
│
├─1─► Radicle: rad patch open "nova policy de rate limit"
│ (assinado com chave do agente)
│
├─2─► Reviewers recebem via p2p
│ ├── Reviewer A: rad patch review --accept
│ └── Reviewer B: rad patch review --accept
│
├─3─► Merge: rad patch merge <id>
│
├─4─► Watcher detecta novo commit
│ ├── Sync .rego → OPA bundle
│ └── OPA recarrega policies
│
└─5─► Algorand: record_decision(
action="policy_deploy",
resource="patch:<id>",
policy_version="<sha256>",
)
→ tx_id imutável

AGENTE EXECUTA AÇÃO:
═════════════════════

Agent (qualquer)
│
├─1─► IAMEnforcer.enforce(agent, action, resource)
│
├─2─► OPA avalia policies (vindas do Radicle)
│ ├── RBAC: role permite ação?
│ ├── ABAC: contexto válido?
│ ├── Rate limit: dentro do limite?
│ └── Lifecycle: transição válida?
│
├─3─► Decisão: ALLOW / DENY
│
├─4─► Algorand: record_decision(...)
│ → hash chain: H(n) = sha256(H(n-1) || entry)
│ → tx_id para auditoria
│
└─5─► Se ALLOW → executa ação
Se DENY → retorna erro + audit_id

AUDITORIA:
══════════

Auditor (qualquer pessoa)
│
├── Algorand Indexer: busca todas txns do app_id
├── Verifica hash chain: H(0) → H(1) → ... → H(n)
├── Radicle: verifica histórico de policies (git log)
└── Cruza: "decisão X usou policy version Y"
→ Totalmente verificável e reprodutível
