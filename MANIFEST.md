# ADR-Ledger: Agent Governance Protocol

## The Problem

AI agents are making consequential decisions — about code architecture,
system configuration, resource allocation — with increasing autonomy.

But we have no verifiable way to answer:

- **Who** authorized this agent to act?
- **What** rules was it following when it decided?
- **Why** was this specific decision made?
- **Can I verify** all of this without trusting anyone?

## The Thesis

We need **institutional infrastructure for autonomous agents** —
the equivalent of constitutions, courts, and auditors —
built on substrate that no single party controls.

## Principles

### From d/acc (Vitalik Buterin)

> "Build technology that is structurally more favorable
> to defense than offense."

Our agents operate in sandboxes. Fail-closed by default.
Power is distributed through quadratic mechanisms.
Identity is soulbound — earned, not bought.

### From Sovereign Computing (Radicle)

> "Your code, your rules, your infrastructure."

Policies live in Radicle, not GitHub. No one can censor
a governance proposal. Forks are legitimate dissent.
Everything works local-first.

### Synthesis

> "Verifiable institutions for autonomous agents,
> built on infrastructure nobody controls alone."

## Architecture

- **NixOS**: Declarative, reproducible, atomic enforcement
- **OPA/Rego**: Policy-as-code, deterministic evaluation
- **Radicle**: Sovereign, p2p policy versioning
- **Algorand**: Immutable audit trail, atomic multi-party approval

Every decision an agent makes is:

1. Evaluated against peer-reviewed policies (Radicle → OPA)
2. Enforced at the OS level (NixOS)
3. Recorded immutably (Algorand)
4. Reproducibly verifiable (by anyone, forever)
