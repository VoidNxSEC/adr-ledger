# Validation Pipeline

`adr-ledger` now has a layered validation path:

1. `scripts/validate_adr.py`
   - parses YAML frontmatter and Markdown sections
   - validates the merged document against [.schema/adr.schema.json](/home/kernelcore/master/adr-ledger/.schema/adr.schema.json)
   - detects unresolved template placeholders
2. `scripts/opa-validate.sh`
   - evaluates each ADR against [policies/adr/validation.rego](/home/kernelcore/master/adr-ledger/policies/adr/validation.rego)
   - uses `data.adr.validation.result` as the default OPA query
3. `.chain/bitcoin_attestation.py`
   - signs or verifies snapshot receipts using ECDSA `secp256k1`
   - stores receipts in [.chain/bitcoin/receipts](/home/kernelcore/master/adr-ledger/.chain/bitcoin/receipts)

## Commands

```bash
nix develop path:/home/kernelcore/master/adr-ledger --command bash -lc '
  cd /home/kernelcore/master/adr-ledger
  bash scripts/validate.sh
'
```

```bash
nix develop path:/home/kernelcore/master/adr-ledger --command bash -lc '
  cd /home/kernelcore/master/adr-ledger
  bash scripts/opa-validate.sh
'
```

```bash
nix develop path:/home/kernelcore/master/adr-ledger --command bash -lc '
  cd /home/kernelcore/master/adr-ledger
  python3.13 .chain/bitcoin_attestation.py keygen --name kernelcore
  python3.13 .chain/bitcoin_attestation.py attest --signer kernelcore
  python3.13 .chain/bitcoin_attestation.py verify-all
'
```

## Gate Semantics

- Hard fail: malformed ADR, schema violation, or OPA denial.
- Soft warning: historical chain drift or missing Bitcoin-compatible receipts when governance is in `warn` mode.
- Dedicated cryptographic commands remain available when you want strict enforcement:
  - `adr chain verify`
  - `adr bitcoin verify-all`

## Scope Clarification

The Bitcoin layer implemented here is a local `secp256k1` attestation flow, compatible with Bitcoin cryptographic primitives, but it does **not** broadcast transactions or implement wallet `signmessage` RPC semantics. It is intended as a deterministic receipt layer that can be anchored or bridged later.
