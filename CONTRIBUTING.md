# Contributing

## Setup

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
nix develop  # instala dependências e git hooks automaticamente
```

Sem Nix: instale `python3`, `python3-pyyaml`, `yamllint`, `jq` manualmente e rode `.hooks/install.sh`.

## Estrutura

```
adr/              # ADRs por status (proposed, accepted, superseded, rejected)
.schema/          # JSON Schema de validação
.governance/      # Governança como código (approval matrix, compliance rules)
.parsers/         # Parser Python (adr_parser.py)
.chain/           # Blockchain layer (provenance, assinaturas)
scripts/adr       # CLI
docs/             # Documentação
```

## Fluxo de contribuição

1. Fork + branch descritiva (`feat/hipaa-compliance-validator`)
2. Para mudanças no parser ou CLI: adicione testes em `.parsers/tests/`
3. `nix flake check` antes do PR — todos os checks devem passar
4. PRs pequenos e focados são mais fáceis de revisar

## Áreas abertas

- **Parsers**: suporte a outros formatos ADR (MADR, Y-statements)
- **Validators**: novos frameworks de compliance (HIPAA, PCI-DSS, ISO 27001)
- **Integrações**: conectores para Jira, Linear, Confluence
- **Visualizações**: layouts de grafo, timeline views

## Convenções

- ADRs em `adr/proposed/` seguem o schema em `.schema/adr.schema.json`
- Commits de código: `feat(parser):`, `fix(cli):`, `chore:`
- Commits de ADR: `arch(adr):` ou `ADR:`
- Não commite artefatos gerados (`knowledge/`, `reports/`) — estão no `.gitignore`

## Licença

MIT. Contribuições são feitas sob a mesma licença.
