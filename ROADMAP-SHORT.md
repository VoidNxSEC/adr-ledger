Fase 1 — AUDIT MODE (semana 1-2)
├── Deploya OPA + policies em modo "log-only"
├── Todas as decisões são registradas mas NÃO enforced
├── Analisa logs para calibrar policies
│
Fase 2 — SOFT ENFORCE (semana 3-4)
├── Ativa enforcement para ações de ESCRITA
├── Leitura permanece aberta
├── Alertas em caso de deny inesperado
│
Fase 3 — FULL ENFORCE (semana 5+)
├── Todas as ações passam pelo enforcer
├── Fail-closed ativado
├── Audit trail completo
│
Fase 4 — AGENT GOVERNANCE
├── Agents automatizados com identidade própria
├── Rate limiting por agente
├── Approval workflows multi-party
└── Hash chain no audit log
