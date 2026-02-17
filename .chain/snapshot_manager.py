"""
ADR-Ledger Cryptographic State Snapshots

Periodic signed snapshots of the complete ledger state.
Each snapshot captures: chain tip, Merkle root, statistics,
and timestamp proof. Snapshots chain together via previous_snapshot_hash.
"""

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from crypto import compute_content_hash, sign_message, verify_signature, Signature

CHAIN_DIR = Path(__file__).parent
SNAPSHOTS_DIR = CHAIN_DIR / "snapshots"
CHAIN_FILE = CHAIN_DIR / "chain.json"
MERKLE_STATE_FILE = CHAIN_DIR / "merkle" / "merkle_state.json"


@dataclass
class ChainSnapshot:
    snapshot_id: int
    timestamp: str
    chain_height: int
    chain_tip: str
    merkle_root: str
    total_accepted: int
    total_proposed: int
    total_superseded: int
    total_rejected: int
    by_classification: Dict[str, int]
    by_project: Dict[str, int]
    previous_snapshot_hash: str
    timestamp_proof: Optional[str]   # Reference to OTS/RFC3161 proof file
    snapshot_hash: str
    signature: Optional[dict]        # Ed25519 signature over snapshot_hash
    sbom_hash: Optional[str] = None  # SHA256 of current SBOM manifest

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ChainSnapshot":
        # Handle older snapshots without sbom_hash
        if "sbom_hash" not in d:
            d["sbom_hash"] = None
        return cls(**d)

    def compute_hash(self) -> str:
        """Compute snapshot hash from all fields (excluding hash and signature)."""
        canonical = (
            f"{self.snapshot_id}|{self.timestamp}|{self.chain_height}|"
            f"{self.chain_tip}|{self.merkle_root}|"
            f"{self.total_accepted}|{self.total_proposed}|"
            f"{self.total_superseded}|{self.total_rejected}|"
            f"{json.dumps(self.by_classification, sort_keys=True)}|"
            f"{json.dumps(self.by_project, sort_keys=True)}|"
            f"{self.previous_snapshot_hash}"
        )
        if self.sbom_hash is not None:
            canonical += f"|{self.sbom_hash}"
        return compute_content_hash(canonical)


class SnapshotManager:
    """Manages cryptographic state snapshots of the ADR ledger."""

    def __init__(self, snapshots_dir: Optional[Path] = None):
        self.snapshots_dir = snapshots_dir or SNAPSHOTS_DIR
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _get_latest_snapshot(self) -> Optional[ChainSnapshot]:
        """Find the most recent snapshot."""
        files = sorted(self.snapshots_dir.glob("snapshot_*.json"))
        if not files:
            return None
        return ChainSnapshot.from_dict(json.loads(files[-1].read_text()))

    def _count_adrs_by_status(self) -> Dict[str, int]:
        """Count ADRs in each status directory."""
        adr_root = CHAIN_DIR.parent / "adr"
        counts = {}
        for status in ["accepted", "proposed", "superseded", "rejected", "deprecated"]:
            d = adr_root / status
            if d.exists():
                counts[status] = len(list(d.glob("ADR-*.md")))
            else:
                counts[status] = 0
        return counts

    def _count_by_classification(self) -> Dict[str, int]:
        """Count ADRs by classification from chain state."""
        import re
        import yaml

        counts = {"critical": 0, "major": 0, "minor": 0, "patch": 0, "unclassified": 0}
        adr_root = CHAIN_DIR.parent / "adr"
        frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

        for md in (adr_root / "accepted").glob("ADR-*.md"):
            content = md.read_text()
            match = frontmatter_re.match(content)
            if match:
                try:
                    fm = yaml.safe_load(match.group(1)) or {}
                    gov = fm.get("governance", {})
                    cls = gov.get("classification", fm.get("classification", "unclassified"))
                    counts[cls] = counts.get(cls, 0) + 1
                except yaml.YAMLError:
                    counts["unclassified"] += 1

        return counts

    def _count_by_project(self) -> Dict[str, int]:
        """Count ADRs by project from chain state."""
        import re
        import yaml

        counts = {}
        adr_root = CHAIN_DIR.parent / "adr"
        frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

        for md in (adr_root / "accepted").glob("ADR-*.md"):
            content = md.read_text()
            match = frontmatter_re.match(content)
            if match:
                try:
                    fm = yaml.safe_load(match.group(1)) or {}
                    scope = fm.get("scope", {})
                    projects = scope.get("projects", fm.get("projects", []))
                    if isinstance(projects, list):
                        for p in projects:
                            counts[p] = counts.get(p, 0) + 1
                except yaml.YAMLError:
                    pass

        return counts

    def create_snapshot(self, signer_name: Optional[str] = None) -> ChainSnapshot:
        """Create a new state snapshot."""
        # Load chain state
        chain_height = 0
        chain_tip = "0" * 64
        if CHAIN_FILE.exists():
            chain_data = json.loads(CHAIN_FILE.read_text())
            chain_height = chain_data.get("height", 0)
            chain_tip = chain_data.get("tip", "0" * 64)

        # Load Merkle root
        merkle_root = ""
        if MERKLE_STATE_FILE.exists():
            merkle_data = json.loads(MERKLE_STATE_FILE.read_text())
            merkle_root = merkle_data.get("root_hash", "")

        # Count ADRs
        status_counts = self._count_adrs_by_status()
        by_classification = self._count_by_classification()
        by_project = self._count_by_project()

        # Get previous snapshot hash
        prev = self._get_latest_snapshot()
        prev_hash = prev.snapshot_hash if prev else "0" * 64
        next_id = (prev.snapshot_id + 1) if prev else 0

        ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")

        # Load SBOM hash if available
        sbom_hash = None
        sbom_file = CHAIN_DIR / "sbom" / "sbom_current.json"
        if sbom_file.exists():
            try:
                sbom_data = json.loads(sbom_file.read_text())
                sbom_hash = sbom_data.get("sbom_hash")
            except (json.JSONDecodeError, KeyError):
                pass

        snapshot = ChainSnapshot(
            snapshot_id=next_id,
            timestamp=ts,
            chain_height=chain_height,
            chain_tip=chain_tip,
            merkle_root=merkle_root,
            total_accepted=status_counts.get("accepted", 0),
            total_proposed=status_counts.get("proposed", 0),
            total_superseded=status_counts.get("superseded", 0),
            total_rejected=status_counts.get("rejected", 0),
            by_classification=by_classification,
            by_project=by_project,
            previous_snapshot_hash=prev_hash,
            timestamp_proof=None,
            snapshot_hash="",
            signature=None,
            sbom_hash=sbom_hash,
        )

        # Compute hash
        snapshot.snapshot_hash = snapshot.compute_hash()

        # Sign if signer provided
        if signer_name:
            sig = sign_message(snapshot.snapshot_hash, signer_name)
            snapshot.signature = sig.to_dict()

        # Save
        out_file = self.snapshots_dir / f"snapshot_{next_id:04d}.json"
        out_file.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n")

        # Anchor snapshot if temporal anchoring is enabled
        try:
            from temporal import TemporalManager
            tm = TemporalManager()
            if tm.is_enabled() and tm._check_ots_available():
                proof = tm.stamp_snapshot(snapshot.snapshot_id)
                if proof.ots_file:
                    snapshot.timestamp_proof = proof.ots_file
                    # Re-save snapshot with proof reference
                    out_file.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n")
        except ImportError:
            pass  # temporal module not available

        return snapshot

    def verify_snapshot(self, snapshot_id: int) -> dict:
        """Verify a snapshot's integrity."""
        snap_file = self.snapshots_dir / f"snapshot_{snapshot_id:04d}.json"
        if not snap_file.exists():
            return {"valid": False, "error": f"Snapshot {snapshot_id} not found"}

        snap = ChainSnapshot.from_dict(json.loads(snap_file.read_text()))

        report = {
            "snapshot_id": snap.snapshot_id,
            "timestamp": snap.timestamp,
            "hash_valid": False,
            "signature_valid": None,
            "chain_link_valid": False,
            "errors": [],
        }

        # Verify hash
        recomputed = snap.compute_hash()
        report["hash_valid"] = recomputed == snap.snapshot_hash
        if not report["hash_valid"]:
            report["errors"].append(
                f"Hash mismatch: expected {recomputed[:16]}..., got {snap.snapshot_hash[:16]}..."
            )

        # Verify signature
        if snap.signature:
            sig = Signature.from_dict(snap.signature)
            report["signature_valid"] = verify_signature(snap.snapshot_hash, sig)
            if not report["signature_valid"]:
                report["errors"].append(f"Invalid signature from {sig.signer_id}")
        else:
            report["signature_valid"] = None  # Not signed

        # Verify chain link to previous snapshot
        if snap.snapshot_id == 0:
            report["chain_link_valid"] = snap.previous_snapshot_hash == "0" * 64
        else:
            prev_file = self.snapshots_dir / f"snapshot_{snap.snapshot_id - 1:04d}.json"
            if prev_file.exists():
                prev = ChainSnapshot.from_dict(json.loads(prev_file.read_text()))
                report["chain_link_valid"] = snap.previous_snapshot_hash == prev.snapshot_hash
                if not report["chain_link_valid"]:
                    report["errors"].append("Previous snapshot hash mismatch")
            else:
                report["chain_link_valid"] = False
                report["errors"].append(f"Previous snapshot {snap.snapshot_id - 1} not found")

        # Verify timestamp proof if present
        if snap.timestamp_proof:
            try:
                from temporal import TemporalManager
                tm = TemporalManager()
                proof_report = tm.verify_by_file(snap.timestamp_proof)
                report["timestamp_proof_valid"] = proof_report.get("valid")
                report["timestamp_proof_status"] = proof_report.get("detail", "unknown")
            except ImportError:
                report["timestamp_proof_valid"] = "unknown (temporal module not available)"

        report["valid"] = (
            report["hash_valid"]
            and report["chain_link_valid"]
            and (report["signature_valid"] is not False)
        )

        return report

    def list_snapshots(self) -> List[dict]:
        """List all snapshots with summary info."""
        snapshots = []
        for f in sorted(self.snapshots_dir.glob("snapshot_*.json")):
            snap = ChainSnapshot.from_dict(json.loads(f.read_text()))
            snapshots.append({
                "id": snap.snapshot_id,
                "timestamp": snap.timestamp,
                "chain_height": snap.chain_height,
                "accepted": snap.total_accepted,
                "signed": snap.signature is not None,
                "hash": snap.snapshot_hash[:16] + "...",
            })
        return snapshots


# --- CLI ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ADR-Ledger Snapshot Manager")
    sub = parser.add_subparsers(dest="command")

    # create
    cr = sub.add_parser("create", help="Create a new state snapshot")
    cr.add_argument("--signer", help="Sign the snapshot with this key")

    # verify
    vf = sub.add_parser("verify", help="Verify a snapshot")
    vf.add_argument("snapshot_id", type=int, help="Snapshot ID")

    # list
    sub.add_parser("list", help="List all snapshots")

    # show
    sh = sub.add_parser("show", help="Show snapshot details")
    sh.add_argument("snapshot_id", type=int, help="Snapshot ID")

    args = parser.parse_args()
    sm = SnapshotManager()

    if args.command == "create":
        snap = sm.create_snapshot(signer_name=args.signer)
        print(f"Snapshot {snap.snapshot_id} created:")
        print(f"  Chain height: {snap.chain_height}")
        print(f"  Merkle root:  {snap.merkle_root[:32]}..." if snap.merkle_root else "  Merkle root:  (not computed)")
        print(f"  Accepted:     {snap.total_accepted}")
        print(f"  Hash:         {snap.snapshot_hash[:32]}...")
        print(f"  Signed:       {'Yes' if snap.signature else 'No'}")

    elif args.command == "verify":
        report = sm.verify_snapshot(args.snapshot_id)
        print(f"Snapshot {args.snapshot_id} Verification:")
        print(f"  Hash valid:      {report['hash_valid']}")
        print(f"  Signature valid: {report['signature_valid']}")
        print(f"  Chain link:      {report['chain_link_valid']}")
        print(f"  Overall:         {'VALID' if report['valid'] else 'INVALID'}")
        if report["errors"]:
            for err in report["errors"]:
                print(f"  ERROR: {err}")
        sys.exit(0 if report["valid"] else 1)

    elif args.command == "list":
        snapshots = sm.list_snapshots()
        if not snapshots:
            print("No snapshots. Run: adr snapshot create")
            return
        print(f"{'ID':>4}  {'Timestamp':25s}  {'Height':>6}  {'Accepted':>8}  {'Signed':>6}  {'Hash'}")
        print("-" * 85)
        for s in snapshots:
            signed = "Yes" if s["signed"] else "No"
            print(f"{s['id']:4d}  {s['timestamp']:25s}  {s['chain_height']:6d}  {s['accepted']:8d}  {signed:>6s}  {s['hash']}")

    elif args.command == "show":
        snap_file = sm.snapshots_dir / f"snapshot_{args.snapshot_id:04d}.json"
        if not snap_file.exists():
            print(f"Snapshot {args.snapshot_id} not found", file=sys.stderr)
            sys.exit(1)
        print(snap_file.read_text())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
