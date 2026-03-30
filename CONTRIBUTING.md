# Contributing

## Setup

```bash
git clone https://github.com/marcosfpina/adr-ledger.git
cd adr-ledger
nix develop  # automatically installs dependencies and git hooks
```

Without Nix: manually install `python3`, `python3-pyyaml`, `yamllint`, `jq` and run `.hooks/install.sh`.

## Structure

```
adr/              # ADRs by status (proposed, accepted, superseded, rejected)
.schema/          # JSON Schema for validation
.governance/      # Governance as code (approval matrix, compliance rules)
.parsers/         # Python parser (adr_parser.py)
.chain/           # Blockchain layer (provenance, signatures)
scripts/adr       # CLI
docs/             # Documentation
```

## Contribution Workflow

1. Fork + descriptive branch (`feat/hipaa-compliance-validator`)
2. For parser or CLI changes: add tests in `.parsers/tests/`
3. Run `nix flake check` before opening a PR — all checks must pass
4. Small, focused PRs are easier to review

## Open Areas

- **Parsers**: support for other ADR formats (MADR, Y-statements)
- **Validators**: new compliance frameworks (HIPAA, PCI-DSS, ISO 27001)
- **Integrations**: connectors for Jira, Linear, Confluence
- **Visualizations**: graph layouts, timeline views

## Conventions

- ADRs in `adr/proposed/` follow the schema defined in `.schema/adr.schema.json`
- Code commits: `feat(parser):`, `fix(cli):`, `chore:`
- ADR commits: `arch(adr):` or `ADR:`
- Do not commit generated artifacts (`knowledge/`, `reports/`) — they are listed in `.gitignore`

## License

Apache 2.0. Contributions are made under the same license.
