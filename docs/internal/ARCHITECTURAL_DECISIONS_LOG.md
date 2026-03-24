# Architectural Decisions Log

**Document Title:** Architectural Decisions Log
**Last Updated:** 2026-01-26
**Maintainer:** KernelCore (System Architect)

---

## AD-001: Supreme Technical Form (STF) Protocol

1.  **Decision ID:** AD-001
2.  **Date:** 2026-01-25 (Blockchain Record: Pending Future Implementation)
3.  **Status:** Proposed
4.  **Title:** Adoption of Supreme Technical Directive (STF) for AI Agents
5.  **Context:**
    Interaction with AI agents in critical engineering environments is currently fragmented. Agents rely on provider-specific system prompts (Claude vs Gemini vs OpenAI), leading to inconsistent behavior, potential hallucinations, and violations of strict project constraints (e.g., suggesting `pip` instead of `nix`). There is no unified "Constitution" that overrides provider defaults.
6.  **Decision:**
    Implement the **STF (Supreme Technical Directive)** as the sovereign source of truth for all agents.
    - **Structure:** XML/Markdown schema defining `identity`, `core_directives`, `behavioral_constraints`, and `error_prevention`.
    - **Priority:** STF > Provider Prompt > User Prompt.
    - **Protocol:** Strict adherence to "Nix-First" and "No Hallucination" policies.
7.  **Rationale:**
    - **Safety:** Prevents execution of arbitrary code or assumption of unverified APIs.
    - **Determinism:** Standardizes agent behavior across different LLM providers.
    - **Hermeticity:** Enforces the use of Nix for all environmental dependencies.
8.  **Consequences:**
    - **Positive:** predictable responses, reduced error rate, strict environment compliance.
    - **Negative:** Agents may refuse vague tasks, requiring more explicit user prompting.
9.  **Alternatives Considered:**
    - _Provider System Prompts (CLAUDE.md):_ Rejected due to lack of portability and weak enforcement.
    - _Runtime Wrappers:_ Rejected as they are reactive (post-generation) rather than preventive.
10. **Tags:** `governance`, `ai-safety`, `nix`, `protocol`

11. **Proposer:** KernelCore
12. **Reviewers:** Architecture Team
13. **Approval Date:** Pending
14. **Superseded By:** N/A
15. **Related Documents:** `adr/proposed/ADR-0012.md`
16. **Metrics:** N/A (Protocol definition phase)
17. **Risks:** Agents might become too rigid ("refusal to answer") if constraints are overly aggressive.
    - _Mitigation:_ Calibrated confidence markers and explicit override mechanisms.
18. **Trade-offs:** Flexibility vs. Reliability. We choose Reliability.
19. **Implementation Notes:** Requires parser implementation in the Agent Hub to inject STF context dynamically.
20. **Diagrams:** N/A

---

## AD-002: AI Assistant Hub & Ranking System

1.  **Decision ID:** AD-002
2.  **Date:** 2026-01-25
3.  **Status:** Proposed / In-Implementation
4.  **Title:** Centralized AI Assistant Hub for Observability and Ranking
5.  **Context:**
    As AI agents become more autonomous, "entropy" (unpredictability/creativity) increases. We need a mechanism to validate agent decisions, ensure they don't hallucinate features ("ghost features"), and maintain alignment with the codebase without stifling their utility.
6.  **Decision:**
    Establish a dedicated `ai-assistant-hub` service acting as a middleware/supervisor.
    - **Observability:** Prometheus/Grafana for metric tracking (latency, decision confidence).
    - **Ranking API:** A centralized scoring system for agent actions.
    - **Policy:** Actions with score < 0.9 require human (Developer) approval.
    - **Feedback Loop:** Store decision outcomes to retrain scoring models.
7.  **Rationale:**
    - **Governance:** We cannot trust black-box models blindly for critical infrastructure.
    - **Integration:** Ensures new features are actually integrated (Git hooks/CI checks) and not just "hallucinated".
    - **Fallback:** Explicitly codifies the Developer as the ultimate fallback for low-confidence decisions.
8.  **Consequences:**
    - **Positive:** High trust in automated actions, preventing system corruption.
    - **Negative:** Operational overhead of running additional services (Python API, DBs).
9.  **Alternatives Considered:**
    - _Client-side filtering:_ Rejected because it lacks centralized logging and learning capabilities.
    - _Blind Trust:_ Rejected as unsafe for production systems.
10. **Tags:** `observability`, `python`, `nix`, `fastapi`, `mlflow`

11. **Proposer:** KernelCore
12. **Reviewers:** Infra Team
13. **Approval Date:** Pending
14. **Superseded By:** N/A
15. **Related Documents:** `~/arch/ai-assistant-hub/README.md`, `flake.nix`
16. **Metrics:**
    - Latency of decision ranking (< 50ms target).
    - Rate of human intervention (aiming for < 10% over time).
17. **Risks:**
    - **Bottleneck:** The Ranking API could become a single point of failure.
    - _Mitigation:_ Fail-safe mode (default to "Request Approval" if API down).
18. **Trade-offs:** Latency (extra API hop) vs. Safety.
19. **Implementation Notes:** Implemented as a Nix Flake project. Uses `FastAPI` for the ranking endpoint and `TimescaleDB` for persistence.
20. **Diagrams:** N/A

---

## AD-003: Sovereign Knowledge Storage via ADR Ledger

1.  **Decision ID:** AD-003
2.  **Date:** 2026-01-25
3.  **Status:** Accepted
4.  **Title:** Git-based Architectural Decision Records (ADR)
5.  **Context:**
    Architectural knowledge is often lost in chat logs or proprietary tools (Notion/Confluence). AI agents need a structured, parseable, and "sovereign" source of truth to understand the _why_ behind system designs.
6.  **Decision:**
    Use a Git-based ADR system (`adr-ledger`) with a strict JSON schema.
    - **Tooling:** Bash scripts (`scripts/adr`) for CRUD operations.
    - **Verification:** CI validation of markdown frontmatter.
    - **Consumption:** Agents consume this via RAG (Retrieval Augmented Generation).
7.  **Rationale:**
    - **Sovereignty:** "Not your repo, not your knowledge."
    - **Parseability:** Structured Markdown + YAML frontmatter is ideal for both humans and LLMs.
    - **Auditability:** Git history provides a cryptographically verifiable timeline of decisions.
8.  **Consequences:**
    - **Positive:** Knowledge base is portable, offline-accessible, and machine-readable.
    - **Negative:** Higher friction to write docs compared to a Wiki.
9.  **Alternatives Considered:**
    - _Wikis:_ Rejected due to lack of versioning and machine-readability.
    - _Database:_ Rejected due to lack of human-readability.
10. **Tags:** `documentation`, `git`, `knowledge-management`

11. **Proposer:** KernelCore
12. **Reviewers:** Self
13. **Approval Date:** 2026-01-25
14. **Superseded By:** N/A
15. **Related Documents:** `ADR-0001`
16. **Metrics:** N/A
17. **Risks:** documentation drift (code changes, docs don't).
    - _Mitigation:_ `adr-compliance` checks in CI pipeline.
18. **Trade-offs:** Write-friction vs. Read-reliability.
19. **Implementation Notes:** Fixed syntax errors in `scripts/adr` to support nullglob for robust file handling.
20. **Diagrams:** N/A

---

## AD-004: Dev Environment Integration & CEREBRO Full Implementation

1.  **Decision ID:** AD-004
2.  **Date:** 2026-01-26
3.  **Status:** Accepted
4.  **Title:** Integrated Dev Deployment & CEREBRO (~6k LOC)
5.  **Context:**
    Successful deployment and integration of core ecosystem components, highlighted by the full implementation of the CEREBRO Intelligence System.
6.  **Decision:**
    Formal acknowledgement of the technical milestone achieving operational status for CEREBRO (Intelligence Core, Project Scanner, React Dashboard), Phantom, SecureLLM-Bridge, Neutron, and Sentinel in `dev`.
7.  **Rationale:**
    - Validates the transition of the project to a professional career goal.
    - Demonstrates full-stack capability (Python/FastAPI + React/Tailwind) and advanced AI (RAG/Hybrid Search).
8.  **Consequences:**
    - **Positive:** Robust integrated platform with semantic search and intelligence gathering capabilities.
9.  **Tags:** `milestone`, `deployment`, `cerebro`, `rag`, `full-stack`
10. **Related Documents:** `ADR-0013`
