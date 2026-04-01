┌──────────────────────────────────────────────────────────────┐
│ GOVERNANCE STACK │
│ │
│ Radicle ──→ Versionamento soberano de policies (p2p git) │
│ Algorand ──→ Audit trail imutável + governance on-chain │
│ OPA ──────→ Decisões de policy em runtime │
│ NixOS ────→ Enforcement no OS + reprodutibilidade │
└──────────────────────────────────────────────────────────────┘
┌─────────────┐
│ Agente │
└──────┬──────┘
│ ação
┌──────▼──────┐
│ OPA Enforce │◄──── Policies versionadas
└──────┬──────┘ no Radicle
│
┌──────▼──────┐
┌─────┤ Decision ├─────┐
│ └─────────────┘ │
┌─────▼─────┐ ┌──────▼──────┐
│ Permitir │ │ Negar │
└─────┬─────┘ └──────┬──────┘
│ │
│ ┌──────────────┐ │
└───►│ Algorand │◄───┘
│ Audit Tx │
└──────┬───────┘
│
┌──────▼───────┐
│ Immutable │
│ Ledger │
└──────────────┘
