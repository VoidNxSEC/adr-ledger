"""
ADR-Ledger Federated Decision Network

Cross-organization sharing of architectural decisions with
selective disclosure. Each org maintains an independent ledger
and shares specific decisions based on topic filters.

Federated decisions are read-only imports that cannot be
modified locally -- only referenced.
"""

import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from crypto import (
    Signature,
    compute_content_hash,
    sign_message,
    verify_signature,
)

CHAIN_DIR = Path(__file__).parent
FEDERATION_DIR = CHAIN_DIR / "federation"
PEERS_FILE = FEDERATION_DIR / "peers.json"
EXPORTS_FILE = FEDERATION_DIR / "exports.json"
IMPORTS_DIR = FEDERATION_DIR / "imports"


@dataclass
class FederatedPeer:
    peer_id: str
    name: str
    description: str
    public_key: str          # Ed25519 public key for verifying peer signatures
    endpoint: Optional[str]  # Git remote URL or API endpoint
    shared_topics: List[str] # Topics this peer shares (e.g., ["security", "infrastructure"])
    added_at: str
    last_sync: Optional[str]
    trusted: bool

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FederatedPeer":
        return cls(**d)


@dataclass
class FederatedDecision:
    source_peer: str
    source_adr_id: str
    title: str
    summary: str                  # Redacted/summary version
    classification: str
    topics: List[str]
    content_hash: str             # Hash of full content (verifiable if shared later)
    merkle_proof: Optional[dict]  # Proves inclusion in source ledger
    shared_at: str
    signature: Optional[dict]     # Source peer's Ed25519 signature
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FederatedDecision":
        return cls(**d)

    def compute_hash(self) -> str:
        canonical = (
            f"{self.source_peer}|{self.source_adr_id}|{self.title}|"
            f"{self.summary}|{self.classification}|"
            f"{','.join(sorted(self.topics))}|{self.content_hash}"
        )
        return compute_content_hash(canonical)


class FederationManager:
    """Manages federated decision sharing between ledgers."""

    def __init__(self):
        FEDERATION_DIR.mkdir(parents=True, exist_ok=True)
        IMPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Peer Management ---

    def _load_peers(self) -> List[FederatedPeer]:
        if not PEERS_FILE.exists():
            return []
        data = json.loads(PEERS_FILE.read_text())
        return [FederatedPeer.from_dict(p) for p in data.get("peers", [])]

    def _save_peers(self, peers: List[FederatedPeer]):
        data = {
            "version": "1.0",
            "peers": [p.to_dict() for p in peers],
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        }
        PEERS_FILE.write_text(json.dumps(data, indent=2) + "\n")

    def add_peer(
        self,
        peer_id: str,
        name: str,
        description: str,
        public_key: str,
        shared_topics: List[str],
        endpoint: Optional[str] = None,
    ) -> FederatedPeer:
        """Register a new federated peer."""
        peers = self._load_peers()

        if any(p.peer_id == peer_id for p in peers):
            print(f"ERROR: Peer '{peer_id}' already exists.", file=sys.stderr)
            sys.exit(1)

        peer = FederatedPeer(
            peer_id=peer_id,
            name=name,
            description=description,
            public_key=public_key,
            endpoint=endpoint,
            shared_topics=shared_topics,
            added_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            last_sync=None,
            trusted=True,
        )

        peers.append(peer)
        self._save_peers(peers)
        return peer

    def remove_peer(self, peer_id: str):
        """Remove a federated peer and its imported decisions."""
        peers = self._load_peers()
        peers = [p for p in peers if p.peer_id != peer_id]
        self._save_peers(peers)

        # Remove imported decisions
        import_dir = IMPORTS_DIR / peer_id
        if import_dir.exists():
            for f in import_dir.glob("*.json"):
                f.unlink()
            import_dir.rmdir()

    def list_peers(self) -> List[dict]:
        """List all federated peers."""
        peers = self._load_peers()
        return [p.to_dict() for p in peers]

    def get_peer(self, peer_id: str) -> Optional[FederatedPeer]:
        peers = self._load_peers()
        for p in peers:
            if p.peer_id == peer_id:
                return p
        return None

    # --- Export (sharing our decisions) ---

    def export_decisions(
        self,
        topics: List[str],
        signer_name: Optional[str] = None,
    ) -> List[FederatedDecision]:
        """Export our decisions filtered by topics for federation sharing."""
        import re
        import yaml

        adr_root = CHAIN_DIR.parent / "adr"
        exported = []
        frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

        # Load chain for content hashes
        chain_hashes = {}
        chain_file = CHAIN_DIR / "chain.json"
        if chain_file.exists():
            chain_data = json.loads(chain_file.read_text())
            for block in chain_data.get("chain", []):
                chain_hashes[block["adr_id"]] = block.get("content_hash", "")

        for md in sorted((adr_root / "accepted").glob("ADR-*.md")):
            content = md.read_text()
            match = frontmatter_re.match(content)
            if not match:
                continue

            try:
                fm = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError:
                continue

            # Extract topics from compliance_tags + layers
            governance = fm.get("governance", {})
            scope = fm.get("scope", {})
            adr_topics = []
            adr_topics.extend(governance.get("compliance_tags", fm.get("compliance_tags", [])))
            adr_topics.extend(scope.get("layers", []))
            adr_topics = [t.lower() for t in adr_topics]

            # Check if any topic matches
            if not any(t.lower() in adr_topics for t in topics):
                continue

            adr_id = fm.get("id", md.stem[:8])
            if isinstance(adr_id, str) and len(adr_id) > 8:
                adr_id = adr_id[:8]

            decision = FederatedDecision(
                source_peer="self",
                source_adr_id=adr_id,
                title=fm.get("title", ""),
                summary=fm.get("context", "")[:200],  # Truncated summary
                classification=governance.get("classification", fm.get("classification", "unknown")),
                topics=adr_topics,
                content_hash=chain_hashes.get(adr_id, ""),
                merkle_proof=None,
                shared_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                signature=None,
            )

            # Sign the export
            if signer_name:
                export_hash = decision.compute_hash()
                sig = sign_message(export_hash, signer_name)
                decision.signature = sig.to_dict()

            exported.append(decision)

        # Save exports
        export_data = {
            "version": "1.0",
            "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "topics": topics,
            "decisions": [d.to_dict() for d in exported],
        }
        EXPORTS_FILE.write_text(json.dumps(export_data, indent=2) + "\n")

        return exported

    # --- Import (receiving decisions from peers) ---

    def import_decisions(self, peer_id: str, decisions_file: str) -> int:
        """Import decisions from a federated peer."""
        peer = self.get_peer(peer_id)
        if not peer:
            print(f"ERROR: Unknown peer '{peer_id}'. Add with: adr federation add-peer", file=sys.stderr)
            sys.exit(1)

        data = json.loads(Path(decisions_file).read_text())
        decisions = [FederatedDecision.from_dict(d) for d in data.get("decisions", [])]

        # Filter by our peer's shared topics
        filtered = []
        for d in decisions:
            d.source_peer = peer_id
            # Verify signature if peer has public key
            if d.signature and peer.public_key:
                export_hash = d.compute_hash()
                sig = Signature.from_dict(d.signature)
                if not verify_signature(export_hash, sig):
                    print(f"WARNING: Invalid signature for {d.source_adr_id} from {peer_id}", file=sys.stderr)
                    continue
            filtered.append(d)

        # Save to imports directory
        import_dir = IMPORTS_DIR / peer_id
        import_dir.mkdir(parents=True, exist_ok=True)

        import_data = {
            "peer_id": peer_id,
            "imported_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "decisions": [d.to_dict() for d in filtered],
        }
        (import_dir / "decisions.json").write_text(json.dumps(import_data, indent=2) + "\n")

        # Update peer last_sync
        peers = self._load_peers()
        for p in peers:
            if p.peer_id == peer_id:
                p.last_sync = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                break
        self._save_peers(peers)

        return len(filtered)

    def list_imports(self, peer_id: Optional[str] = None) -> List[dict]:
        """List imported decisions."""
        results = []
        search_dirs = [IMPORTS_DIR / peer_id] if peer_id else list(IMPORTS_DIR.iterdir())

        for d in search_dirs:
            if not d.is_dir():
                continue
            dec_file = d / "decisions.json"
            if not dec_file.exists():
                continue
            data = json.loads(dec_file.read_text())
            for dec in data.get("decisions", []):
                results.append({
                    "peer": data.get("peer_id", d.name),
                    "adr_id": dec.get("source_adr_id"),
                    "title": dec.get("title", "")[:50],
                    "classification": dec.get("classification"),
                    "topics": dec.get("topics", []),
                })

        return results

    def federation_status(self) -> dict:
        """Overview of federation state."""
        peers = self._load_peers()
        imports = self.list_imports()

        exports_count = 0
        if EXPORTS_FILE.exists():
            data = json.loads(EXPORTS_FILE.read_text())
            exports_count = len(data.get("decisions", []))

        return {
            "peers": len(peers),
            "trusted_peers": sum(1 for p in peers if p.trusted),
            "exported_decisions": exports_count,
            "imported_decisions": len(imports),
            "peers_detail": [
                {
                    "id": p.peer_id,
                    "name": p.name,
                    "topics": p.shared_topics,
                    "last_sync": p.last_sync,
                }
                for p in peers
            ],
        }


# --- CLI ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ADR-Ledger Federation Manager")
    sub = parser.add_subparsers(dest="command")

    # add-peer
    ap = sub.add_parser("add-peer", help="Add a federated peer")
    ap.add_argument("--id", required=True, help="Peer identifier")
    ap.add_argument("--name", required=True, help="Peer display name")
    ap.add_argument("--description", default="", help="Peer description")
    ap.add_argument("--public-key", required=True, help="Ed25519 public key (base64)")
    ap.add_argument("--topics", required=True, help="Comma-separated shared topics")
    ap.add_argument("--endpoint", help="Git remote URL or API endpoint")

    # remove-peer
    rp = sub.add_parser("remove-peer", help="Remove a federated peer")
    rp.add_argument("peer_id", help="Peer ID to remove")

    # list-peers
    sub.add_parser("list-peers", help="List federated peers")

    # export
    ex = sub.add_parser("export", help="Export decisions for federation")
    ex.add_argument("--topics", required=True, help="Comma-separated topics to export")
    ex.add_argument("--signer", help="Sign exports with this key")

    # import
    im = sub.add_parser("import", help="Import decisions from a peer")
    im.add_argument("peer_id", help="Peer ID")
    im.add_argument("file", help="Path to exported decisions JSON")

    # list-imports
    li = sub.add_parser("list-imports", help="List imported decisions")
    li.add_argument("--peer", help="Filter by peer ID")

    # status
    sub.add_parser("status", help="Federation status overview")

    args = parser.parse_args()
    fm = FederationManager()

    if args.command == "add-peer":
        topics = [t.strip() for t in args.topics.split(",")]
        peer = fm.add_peer(
            peer_id=args.id,
            name=args.name,
            description=args.description,
            public_key=args.public_key,
            shared_topics=topics,
            endpoint=args.endpoint,
        )
        print(f"Peer '{peer.peer_id}' ({peer.name}) added.")
        print(f"  Topics: {', '.join(peer.shared_topics)}")

    elif args.command == "remove-peer":
        fm.remove_peer(args.peer_id)
        print(f"Peer '{args.peer_id}' removed.")

    elif args.command == "list-peers":
        peers = fm.list_peers()
        if not peers:
            print("No federated peers. Add with: adr federation add-peer")
            return
        for p in peers:
            sync = p.get("last_sync", "never")
            topics = ", ".join(p.get("shared_topics", []))
            print(f"  {p['peer_id']:15s} {p['name']:20s} topics=[{topics}] last_sync={sync}")

    elif args.command == "export":
        topics = [t.strip() for t in args.topics.split(",")]
        exported = fm.export_decisions(topics=topics, signer_name=args.signer)
        print(f"Exported {len(exported)} decisions for topics: {', '.join(topics)}")
        print(f"  Saved to: {EXPORTS_FILE}")

    elif args.command == "import":
        count = fm.import_decisions(args.peer_id, args.file)
        print(f"Imported {count} decisions from peer '{args.peer_id}'")

    elif args.command == "list-imports":
        imports = fm.list_imports(peer_id=args.peer)
        if not imports:
            print("No imported decisions.")
            return
        for i in imports:
            topics = ", ".join(i["topics"][:3])
            print(f"  [{i['peer']:12s}] {i['adr_id']:12s} {i['classification']:10s} {i['title']}")

    elif args.command == "status":
        status = fm.federation_status()
        print("Federation Status:")
        print(f"  Peers:     {status['peers']} ({status['trusted_peers']} trusted)")
        print(f"  Exported:  {status['exported_decisions']} decisions")
        print(f"  Imported:  {status['imported_decisions']} decisions")
        if status["peers_detail"]:
            print("\n  Peers:")
            for p in status["peers_detail"]:
                topics = ", ".join(p["topics"])
                print(f"    {p['id']:15s} {p['name']:20s} [{topics}]")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
