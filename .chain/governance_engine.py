"""
ADR-Ledger Smart Governance Contracts

Transforms .governance/governance.yaml rules into executable
contract validators that MUST pass before ADR state transitions.

Each contract is a pure function: (ADRNode, ChainState) -> ContractResult
Audit log of all contract executions stored in .chain/audit_log.jsonl
"""

import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CHAIN_DIR = Path(__file__).parent
GOVERNANCE_FILE = CHAIN_DIR.parent / ".governance" / "governance.yaml"
AUDIT_LOG_FILE = CHAIN_DIR / "audit_log.jsonl"


@dataclass
class ContractResult:
    contract_name: str
    passed: bool
    reason: str
    severity: str = "error"  # error, warning, info
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditEntry:
    timestamp: str
    adr_id: str
    action: str           # acceptance_attempt, signing, rejection, etc.
    actor: str            # Who triggered this
    contracts: List[dict]
    all_passed: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class GovernanceEngine:
    """Executable governance engine based on governance.yaml rules."""

    def __init__(self, governance_file: Optional[Path] = None):
        self.governance_file = governance_file or GOVERNANCE_FILE
        self.rules = self._load_rules()

    def _load_rules(self) -> dict:
        if not self.governance_file.exists():
            print(f"WARNING: Governance file not found: {self.governance_file}", file=sys.stderr)
            return {}
        with open(self.governance_file) as f:
            return yaml.safe_load(f)

    # --- Contract Validators ---

    def check_approval_requirements(
        self, classification: str, signatures: List[dict]
    ) -> ContractResult:
        """Verify that enough approved roles have signed for the given classification."""
        matrix = self.rules.get("approval_matrix", {})
        rule = matrix.get(classification, {})

        required_count = rule.get("required_approvers", 1)
        required_roles = set(rule.get("required_roles", []))

        signer_roles = {sig.get("role", "") for sig in signatures}
        matching_roles = signer_roles & required_roles
        sig_count = len(signatures)

        if sig_count < required_count:
            return ContractResult(
                contract_name="approval_requirements",
                passed=False,
                reason=(
                    f"Classification '{classification}' requires {required_count} "
                    f"signature(s), got {sig_count}"
                ),
            )

        if required_roles and not matching_roles:
            return ContractResult(
                contract_name="approval_requirements",
                passed=False,
                reason=(
                    f"Classification '{classification}' requires roles "
                    f"{required_roles}, got {signer_roles}"
                ),
            )

        return ContractResult(
            contract_name="approval_requirements",
            passed=True,
            reason=f"OK: {sig_count} signature(s) from roles {signer_roles}",
        )

    def check_compliance_tags(
        self, context: str, decision: str, compliance_tags: List[str]
    ) -> ContractResult:
        """Check if compliance tags are present when trigger keywords are found."""
        compliance_rules = self.rules.get("compliance", {})
        text = f"{context} {decision}".lower()
        missing = []

        for rule_name, rule in compliance_rules.items():
            trigger_keywords = rule.get("trigger_keywords", [])
            required_tags = rule.get("required_tags", [])

            triggered = any(kw.lower() in text for kw in trigger_keywords)
            if triggered:
                for tag in required_tags:
                    if tag not in compliance_tags:
                        missing.append(f"{tag} (triggered by '{rule_name}' rule)")

        if missing:
            return ContractResult(
                contract_name="compliance_tags",
                passed=False,
                reason=f"Missing required compliance tags: {', '.join(missing)}",
            )

        return ContractResult(
            contract_name="compliance_tags",
            passed=True,
            reason="OK: All compliance triggers satisfied",
        )

    def check_required_sections(
        self, context: str, decision: str, compliance_tags: List[str], sections: List[str]
    ) -> ContractResult:
        """Check if required sections are present based on compliance rules."""
        compliance_rules = self.rules.get("compliance", {})
        text = f"{context} {decision}".lower()
        missing_sections = []

        for rule_name, rule in compliance_rules.items():
            trigger_keywords = rule.get("trigger_keywords", [])
            required_sections = rule.get("required_sections", [])

            triggered = any(kw.lower() in text for kw in trigger_keywords)
            if triggered and required_sections:
                for sec in required_sections:
                    if sec not in sections:
                        missing_sections.append(f"{sec} (required by '{rule_name}' rule)")

        if missing_sections:
            return ContractResult(
                contract_name="required_sections",
                passed=False,
                reason=f"Missing required sections: {', '.join(missing_sections)}",
                severity="warning",
            )

        return ContractResult(
            contract_name="required_sections",
            passed=True,
            reason="OK: All required sections present",
        )

    def check_lifecycle_transition(
        self, current_status: str, target_status: str
    ) -> ContractResult:
        """Verify the state transition is allowed by lifecycle rules."""
        lifecycle = self.rules.get("lifecycle", {}).get("states", {})
        state_rules = lifecycle.get(current_status, {})
        allowed = state_rules.get("allowed_transitions", [])

        if target_status not in allowed:
            return ContractResult(
                contract_name="lifecycle_transition",
                passed=False,
                reason=(
                    f"Transition '{current_status}' -> '{target_status}' not allowed. "
                    f"Allowed: {allowed}"
                ),
            )

        return ContractResult(
            contract_name="lifecycle_transition",
            passed=True,
            reason=f"OK: '{current_status}' -> '{target_status}' is valid",
        )

    def check_id_format(self, adr_id: str) -> ContractResult:
        """Verify ADR ID matches expected format."""
        if not re.match(r"^ADR-[0-9]{4}$", adr_id):
            return ContractResult(
                contract_name="id_format",
                passed=False,
                reason=f"Invalid ADR ID format: '{adr_id}'. Expected: ADR-XXXX",
            )

        return ContractResult(
            contract_name="id_format",
            passed=True,
            reason=f"OK: '{adr_id}' is valid",
        )

    def check_project_rules(
        self, projects: List[str], classification: str, compliance_tags: List[str]
    ) -> ContractResult:
        """Check project-specific rules."""
        project_rules = self.rules.get("projects", {})
        issues = []

        for project in projects:
            rules = project_rules.get(project, {})
            if not rules:
                continue

            # Check default classification enforcement
            default_class = rules.get("default_classification")
            class_order = {"patch": 0, "minor": 1, "major": 2, "critical": 3}
            if default_class and class_order.get(classification, 0) < class_order.get(default_class, 0):
                issues.append(
                    f"Project '{project}' requires minimum classification "
                    f"'{default_class}', got '{classification}'"
                )

            # Check required tags
            required = rules.get("required_tags", [])
            for tag in required:
                if tag not in compliance_tags:
                    issues.append(f"Project '{project}' requires tag '{tag}'")

        if issues:
            return ContractResult(
                contract_name="project_rules",
                passed=False,
                reason="; ".join(issues),
                severity="warning",
            )

        return ContractResult(
            contract_name="project_rules",
            passed=True,
            reason="OK: All project rules satisfied",
        )

    def check_chain_integrity(self, chain_file: Optional[Path] = None) -> ContractResult:
        """Verify chain integrity before allowing a new block."""
        chain_file = chain_file or (CHAIN_DIR / "chain.json")

        if not chain_file.exists():
            return ContractResult(
                contract_name="chain_integrity",
                passed=True,
                reason="OK: No chain yet (will be initialized)",
                severity="info",
            )

        # Import here to avoid circular deps
        from chain_manager import ChainManager

        cm = ChainManager(chain_file=chain_file)
        cm.load()
        report = cm.verify_chain()

        if not report["chain_valid"]:
            return ContractResult(
                contract_name="chain_integrity",
                passed=False,
                reason=f"Chain integrity check failed: {'; '.join(report['errors'][:3])}",
            )

        return ContractResult(
            contract_name="chain_integrity",
            passed=True,
            reason=f"OK: Chain valid ({report['height']} blocks)",
        )

    # --- Composite Validation ---

    def validate_acceptance(
        self,
        adr_id: str,
        classification: str,
        context: str,
        decision: str,
        compliance_tags: List[str],
        projects: List[str],
        sections: List[str],
        signatures: List[dict],
        actor: str = "system",
    ) -> List[ContractResult]:
        """Run all governance contracts for ADR acceptance.

        Returns list of ContractResults. Acceptance is blocked
        if any error-severity contract fails.
        """
        results = [
            self.check_id_format(adr_id),
            self.check_lifecycle_transition("proposed", "accepted"),
            self.check_approval_requirements(classification, signatures),
            self.check_compliance_tags(context, decision, compliance_tags),
            self.check_required_sections(context, decision, compliance_tags, sections),
            self.check_project_rules(projects, classification, compliance_tags),
            self.check_chain_integrity(),
        ]

        # Log to audit trail
        all_passed = all(r.passed for r in results if r.severity == "error")
        self._write_audit(
            adr_id=adr_id,
            action="acceptance_validation",
            actor=actor,
            contracts=[r.to_dict() for r in results],
            all_passed=all_passed,
            metadata={"classification": classification, "projects": projects},
        )

        return results

    def validate_proposal(
        self,
        adr_id: str,
        context: str,
        decision: str,
        compliance_tags: List[str],
        projects: List[str],
        actor: str = "system",
    ) -> List[ContractResult]:
        """Run governance contracts for ADR proposal validation."""
        results = [
            self.check_id_format(adr_id),
            self.check_compliance_tags(context, decision, compliance_tags),
            self.check_project_rules(projects, "minor", compliance_tags),  # Lenient on classification for proposals
        ]

        all_passed = all(r.passed for r in results if r.severity == "error")
        self._write_audit(
            adr_id=adr_id,
            action="proposal_validation",
            actor=actor,
            contracts=[r.to_dict() for r in results],
            all_passed=all_passed,
        )

        return results

    # --- Audit Log ---

    def _write_audit(self, **kwargs):
        """Append to audit log (JSONL format)."""
        AUDIT_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        entry = AuditEntry(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            **kwargs,
        )

        with open(AUDIT_LOG_FILE, "a") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")

    def read_audit_log(self, limit: int = 50) -> List[dict]:
        """Read recent audit log entries."""
        if not AUDIT_LOG_FILE.exists():
            return []

        entries = []
        for line in AUDIT_LOG_FILE.read_text().strip().split("\n"):
            if line:
                entries.append(json.loads(line))

        return entries[-limit:]

    def audit_summary(self) -> dict:
        """Generate summary of governance audit log."""
        entries = self.read_audit_log(limit=1000)

        total = len(entries)
        passed = sum(1 for e in entries if e.get("all_passed"))
        failed = total - passed

        actions = {}
        for e in entries:
            action = e.get("action", "unknown")
            actions[action] = actions.get(action, 0) + 1

        return {
            "total_validations": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": f"{(passed / total * 100):.1f}%" if total else "N/A",
            "by_action": actions,
        }


# --- CLI ---

def _parse_adr_frontmatter(adr_file: str) -> dict:
    """Quick parse of ADR YAML frontmatter."""
    content = Path(adr_file).read_text()
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    try:
        return yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}


def main():
    import argparse
    from glob import glob

    parser = argparse.ArgumentParser(description="ADR-Ledger Governance Engine")
    sub = parser.add_subparsers(dest="command")

    # validate-accept
    va = sub.add_parser("validate-accept", help="Validate ADR for acceptance")
    va.add_argument("adr_id", help="ADR ID (e.g., ADR-0032)")
    va.add_argument("--actor", default="system", help="Who is performing validation")

    # validate-proposal
    vp = sub.add_parser("validate-proposal", help="Validate ADR proposal")
    vp.add_argument("adr_id", help="ADR ID")

    # audit
    sub.add_parser("audit", help="Show audit log summary")

    # audit-log
    al = sub.add_parser("audit-log", help="Show recent audit entries")
    al.add_argument("--limit", type=int, default=20, help="Number of entries")

    # check-transition
    ct = sub.add_parser("check-transition", help="Check if a state transition is allowed")
    ct.add_argument("current", help="Current status")
    ct.add_argument("target", help="Target status")

    args = parser.parse_args()
    engine = GovernanceEngine()

    if args.command == "validate-accept":
        # Find ADR file
        adr_root = CHAIN_DIR.parent / "adr"
        adr_file = None
        for d in ["proposed", "accepted"]:
            matches = glob(str(adr_root / d / f"{args.adr_id}*.md"))
            if matches:
                adr_file = matches[0]
                break

        if not adr_file:
            print(f"ERROR: ADR file not found for {args.adr_id}", file=sys.stderr)
            sys.exit(1)

        fm = _parse_adr_frontmatter(adr_file)

        # Extract chain signatures if they exist
        chain_file = CHAIN_DIR / "chain.json"
        signatures = []
        if chain_file.exists():
            chain_data = json.loads(chain_file.read_text())
            for block in chain_data.get("chain", []):
                if block.get("adr_id") == args.adr_id:
                    signatures = block.get("signatures", [])
                    break

        governance = fm.get("governance", {})
        scope = fm.get("scope", {})

        results = engine.validate_acceptance(
            adr_id=args.adr_id,
            classification=governance.get("classification", fm.get("classification", "minor")),
            context=fm.get("context", ""),
            decision=fm.get("decision", ""),
            compliance_tags=governance.get("compliance_tags", fm.get("compliance_tags", [])),
            projects=scope.get("projects", fm.get("projects", [])),
            sections=[],  # Would need to parse markdown sections
            signatures=signatures,
            actor=args.actor,
        )

        all_ok = True
        for r in results:
            symbol = "PASS" if r.passed else ("WARN" if r.severity == "warning" else "FAIL")
            if not r.passed and r.severity == "error":
                all_ok = False
            print(f"  [{symbol}] {r.contract_name}: {r.reason}")

        if all_ok:
            print(f"\nGovernance validation PASSED for {args.adr_id}")
        else:
            print(f"\nGovernance validation FAILED for {args.adr_id}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "validate-proposal":
        adr_root = CHAIN_DIR.parent / "adr"
        matches = glob(str(adr_root / "proposed" / f"{args.adr_id}*.md"))
        if not matches:
            print(f"ERROR: Proposed ADR not found: {args.adr_id}", file=sys.stderr)
            sys.exit(1)

        fm = _parse_adr_frontmatter(matches[0])
        governance = fm.get("governance", {})
        scope = fm.get("scope", {})

        results = engine.validate_proposal(
            adr_id=args.adr_id,
            context=fm.get("context", ""),
            decision=fm.get("decision", ""),
            compliance_tags=governance.get("compliance_tags", fm.get("compliance_tags", [])),
            projects=scope.get("projects", fm.get("projects", [])),
        )

        for r in results:
            symbol = "PASS" if r.passed else "FAIL"
            print(f"  [{symbol}] {r.contract_name}: {r.reason}")

    elif args.command == "audit":
        summary = engine.audit_summary()
        print("Governance Audit Summary:")
        print(f"  Total validations: {summary['total_validations']}")
        print(f"  Passed:            {summary['passed']}")
        print(f"  Failed:            {summary['failed']}")
        print(f"  Pass rate:         {summary['pass_rate']}")
        if summary["by_action"]:
            print("  By action:")
            for action, count in summary["by_action"].items():
                print(f"    {action}: {count}")

    elif args.command == "audit-log":
        entries = engine.read_audit_log(limit=args.limit)
        for e in entries:
            passed = "PASS" if e.get("all_passed") else "FAIL"
            print(f"  {e['timestamp']} [{passed}] {e['action']} {e['adr_id']} (by {e['actor']})")

    elif args.command == "check-transition":
        result = engine.check_lifecycle_transition(args.current, args.target)
        symbol = "PASS" if result.passed else "FAIL"
        print(f"  [{symbol}] {result.reason}")
        sys.exit(0 if result.passed else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
