"""
ADR-Ledger Decision Provenance Graph

End-to-end traceability for architectural decisions:
research -> analysis -> proposal -> review -> approval -> acceptance -> implementation -> outcome

Each stage has its own hash and optional signature, creating
a verifiable evidence chain for every decision.
"""

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from crypto import compute_content_hash, sign_message, verify_signature, Signature

CHAIN_DIR = Path(__file__).parent
PROVENANCE_DIR = CHAIN_DIR / "provenance"


class ProvenanceStage(str, Enum):
    RESEARCH = "research"
    ANALYSIS = "analysis"
    PROPOSAL = "proposal"
    REVIEW = "review"
    APPROVAL = "approval"
    ACCEPTANCE = "acceptance"
    IMPLEMENTATION = "implementation"
    OUTCOME = "outcome"

    @classmethod
    def ordered(cls) -> list:
        return [
            cls.RESEARCH, cls.ANALYSIS, cls.PROPOSAL, cls.REVIEW,
            cls.APPROVAL, cls.ACCEPTANCE, cls.IMPLEMENTATION, cls.OUTCOME,
        ]


@dataclass
class ProvenanceEntry:
    stage: str               # ProvenanceStage value
    adr_id: str
    timestamp: str
    actor: str               # Who performed this stage
    description: str         # What happened
    evidence_hash: str       # SHA256 of evidence content
    evidence_ref: str        # URI/path to evidence (git commit, file, URL)
    previous_entry_hash: str # Hash of prior entry (chain link)
    entry_hash: str          # SHA256 of this entry
    signature: Optional[dict] = None  # Ed25519 signature
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProvenanceEntry":
        return cls(**d)

    def compute_hash(self) -> str:
        canonical = (
            f"{self.stage}|{self.adr_id}|{self.timestamp}|{self.actor}|"
            f"{self.description}|{self.evidence_hash}|{self.evidence_ref}|"
            f"{self.previous_entry_hash}"
        )
        return compute_content_hash(canonical)


@dataclass
class ProvenanceGraph:
    adr_id: str
    entries: List[ProvenanceEntry]
    created_at: str
    last_updated: str

    def to_dict(self) -> dict:
        return {
            "adr_id": self.adr_id,
            "entries": [e.to_dict() for e in self.entries],
            "created_at": self.created_at,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProvenanceGraph":
        entries = [ProvenanceEntry.from_dict(e) for e in d.get("entries", [])]
        return cls(
            adr_id=d["adr_id"],
            entries=entries,
            created_at=d.get("created_at", ""),
            last_updated=d.get("last_updated", ""),
        )


class ProvenanceManager:
    """Manages decision provenance graphs."""

    def __init__(self, provenance_dir: Optional[Path] = None):
        self.provenance_dir = provenance_dir or PROVENANCE_DIR
        self.provenance_dir.mkdir(parents=True, exist_ok=True)

    def _graph_file(self, adr_id: str) -> Path:
        return self.provenance_dir / f"{adr_id}.json"

    def load_graph(self, adr_id: str) -> Optional[ProvenanceGraph]:
        """Load provenance graph for an ADR."""
        f = self._graph_file(adr_id)
        if not f.exists():
            return None
        return ProvenanceGraph.from_dict(json.loads(f.read_text()))

    def _save_graph(self, graph: ProvenanceGraph):
        f = self._graph_file(graph.adr_id)
        f.write_text(json.dumps(graph.to_dict(), indent=2) + "\n")

    def add_entry(
        self,
        adr_id: str,
        stage: str,
        actor: str,
        description: str,
        evidence_ref: str = "",
        evidence_content: str = "",
        signer_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> ProvenanceEntry:
        """Add a provenance entry for an ADR."""
        graph = self.load_graph(adr_id)
        ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        if graph is None:
            graph = ProvenanceGraph(
                adr_id=adr_id,
                entries=[],
                created_at=ts,
                last_updated=ts,
            )

        # Compute evidence hash
        evidence_hash = compute_content_hash(evidence_content) if evidence_content else ""

        # Previous entry hash (chain link)
        prev_hash = graph.entries[-1].entry_hash if graph.entries else "0" * 64

        entry = ProvenanceEntry(
            stage=stage,
            adr_id=adr_id,
            timestamp=ts,
            actor=actor,
            description=description,
            evidence_hash=evidence_hash,
            evidence_ref=evidence_ref,
            previous_entry_hash=prev_hash,
            entry_hash="",  # Will be computed
            metadata=metadata or {},
        )

        entry.entry_hash = entry.compute_hash()

        # Sign if signer provided
        if signer_name:
            sig = sign_message(entry.entry_hash, signer_name)
            entry.signature = sig.to_dict()

        graph.entries.append(entry)
        graph.last_updated = ts
        self._save_graph(graph)

        return entry

    def verify_graph(self, adr_id: str) -> dict:
        """Verify provenance graph integrity for an ADR."""
        graph = self.load_graph(adr_id)
        if graph is None:
            return {"valid": False, "error": f"No provenance graph for {adr_id}"}

        report = {
            "adr_id": adr_id,
            "total_entries": len(graph.entries),
            "stages_completed": [],
            "entries": [],
            "valid": True,
            "errors": [],
        }

        for i, entry in enumerate(graph.entries):
            entry_report = {
                "stage": entry.stage,
                "actor": entry.actor,
                "hash_valid": False,
                "link_valid": False,
                "signature_valid": None,
            }

            # Verify entry hash
            recomputed = entry.compute_hash()
            entry_report["hash_valid"] = recomputed == entry.entry_hash
            if not entry_report["hash_valid"]:
                report["valid"] = False
                report["errors"].append(f"Entry {i} ({entry.stage}): hash mismatch")

            # Verify chain link
            expected_prev = graph.entries[i - 1].entry_hash if i > 0 else "0" * 64
            entry_report["link_valid"] = entry.previous_entry_hash == expected_prev
            if not entry_report["link_valid"]:
                report["valid"] = False
                report["errors"].append(f"Entry {i} ({entry.stage}): chain link broken")

            # Verify signature
            if entry.signature:
                sig = Signature.from_dict(entry.signature)
                entry_report["signature_valid"] = verify_signature(entry.entry_hash, sig)
                if not entry_report["signature_valid"]:
                    report["valid"] = False
                    report["errors"].append(f"Entry {i} ({entry.stage}): invalid signature")

            report["entries"].append(entry_report)
            if entry.stage not in report["stages_completed"]:
                report["stages_completed"].append(entry.stage)

        return report

    def get_stage_summary(self, adr_id: str) -> dict:
        """Get a summary of provenance stages for an ADR."""
        graph = self.load_graph(adr_id)
        if graph is None:
            return {"adr_id": adr_id, "stages": {}}

        stages = {}
        ordered = ProvenanceStage.ordered()

        for stage in ordered:
            entries = [e for e in graph.entries if e.stage == stage.value]
            if entries:
                latest = entries[-1]
                stages[stage.value] = {
                    "completed": True,
                    "timestamp": latest.timestamp,
                    "actor": latest.actor,
                    "entries": len(entries),
                }
            else:
                stages[stage.value] = {"completed": False}

        return {"adr_id": adr_id, "stages": stages}

    def list_all(self) -> List[dict]:
        """List all ADRs with provenance tracking."""
        results = []
        for f in sorted(self.provenance_dir.glob("ADR-*.json")):
            graph = ProvenanceGraph.from_dict(json.loads(f.read_text()))
            stages = [e.stage for e in graph.entries]
            unique_stages = list(dict.fromkeys(stages))  # Preserve order, deduplicate
            results.append({
                "adr_id": graph.adr_id,
                "entries": len(graph.entries),
                "stages": unique_stages,
                "last_updated": graph.last_updated,
            })
        return results


# --- CLI ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ADR-Ledger Decision Provenance")
    sub = parser.add_subparsers(dest="command")

    # add
    add_p = sub.add_parser("add", help="Add provenance entry")
    add_p.add_argument("adr_id", help="ADR ID")
    add_p.add_argument("--stage", required=True, choices=[s.value for s in ProvenanceStage])
    add_p.add_argument("--actor", required=True, help="Who performed this")
    add_p.add_argument("--description", required=True, help="What happened")
    add_p.add_argument("--evidence-ref", default="", help="Reference to evidence (URL, commit, file)")
    add_p.add_argument("--signer", help="Sign this entry")

    # show
    show_p = sub.add_parser("show", help="Show provenance graph")
    show_p.add_argument("adr_id", help="ADR ID")

    # verify
    vf = sub.add_parser("verify", help="Verify provenance integrity")
    vf.add_argument("adr_id", help="ADR ID")

    # summary
    sum_p = sub.add_parser("summary", help="Stage summary for an ADR")
    sum_p.add_argument("adr_id", help="ADR ID")

    # list
    sub.add_parser("list", help="List all tracked ADRs")

    args = parser.parse_args()
    pm = ProvenanceManager()

    if args.command == "add":
        entry = pm.add_entry(
            adr_id=args.adr_id,
            stage=args.stage,
            actor=args.actor,
            description=args.description,
            evidence_ref=args.evidence_ref,
            signer_name=args.signer,
        )
        print(f"Provenance entry added: {entry.stage} for {entry.adr_id}")
        print(f"  Hash: {entry.entry_hash[:32]}...")
        print(f"  Signed: {'Yes' if entry.signature else 'No'}")

    elif args.command == "show":
        graph = pm.load_graph(args.adr_id)
        if not graph:
            print(f"No provenance for {args.adr_id}")
            return
        print(json.dumps(graph.to_dict(), indent=2))

    elif args.command == "verify":
        report = pm.verify_graph(args.adr_id)
        print(f"Provenance Verification for {args.adr_id}:")
        print(f"  Entries:  {report['total_entries']}")
        print(f"  Stages:   {', '.join(report['stages_completed'])}")
        print(f"  Valid:    {report['valid']}")
        if report["errors"]:
            for err in report["errors"]:
                print(f"  ERROR: {err}")
        sys.exit(0 if report["valid"] else 1)

    elif args.command == "summary":
        summary = pm.get_stage_summary(args.adr_id)
        print(f"Provenance Summary for {summary['adr_id']}:")
        for stage in ProvenanceStage.ordered():
            info = summary["stages"].get(stage.value, {})
            if info.get("completed"):
                print(f"  [{stage.value:15s}]  completed  {info['timestamp']}  by {info['actor']}")
            else:
                print(f"  [{stage.value:15s}]  pending")

    elif args.command == "list":
        items = pm.list_all()
        if not items:
            print("No provenance tracking yet.")
            return
        for item in items:
            stages = ", ".join(item["stages"])
            print(f"  {item['adr_id']:12s}  entries={item['entries']:3d}  stages=[{stages}]")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
