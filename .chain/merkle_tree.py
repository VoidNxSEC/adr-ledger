"""
ADR-Ledger Merkle Tree

Binary Merkle tree over accepted ADR content hashes.
Enables O(log n) inclusion proofs: prove an ADR belongs
to the ledger without transmitting the entire chain.

The root hash represents the complete state of organizational knowledge.
"""

import hashlib
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

CHAIN_DIR = Path(__file__).parent
MERKLE_STATE_FILE = CHAIN_DIR / "merkle" / "merkle_state.json"
CHAIN_FILE = CHAIN_DIR / "chain.json"


def _hash_pair(left: str, right: str) -> str:
    """Hash two hex strings together (sorted for determinism)."""
    combined = min(left, right) + max(left, right)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def _hash_leaf(content_hash: str) -> str:
    """Hash a leaf node (prefix with 0x00 to distinguish from internal nodes)."""
    return hashlib.sha256(b"\x00" + content_hash.encode("utf-8")).hexdigest()


def _hash_internal(left: str, right: str) -> str:
    """Hash an internal node (prefix with 0x01)."""
    return hashlib.sha256(
        b"\x01" + left.encode("utf-8") + right.encode("utf-8")
    ).hexdigest()


@dataclass
class MerkleProof:
    """Proof that an ADR is included in the Merkle tree."""
    adr_id: str
    leaf_hash: str
    proof_path: List[Dict[str, str]]  # [{"hash": "...", "side": "left"|"right"}, ...]
    root_hash: str
    tree_size: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MerkleProof":
        return cls(**d)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class MerkleState:
    root_hash: str
    height: int
    leaf_count: int
    computed_at: str
    chain_height_at_computation: int
    leaves: List[Dict[str, str]]  # [{"adr_id": "...", "content_hash": "...", "leaf_hash": "..."}, ...]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "MerkleState":
        return cls(**d)


class MerkleTree:
    """Binary Merkle tree over ADR content hashes."""

    def __init__(self):
        self.leaves: List[Tuple[str, str, str]] = []  # (adr_id, content_hash, leaf_hash)
        self._tree_levels: List[List[str]] = []        # Bottom-up levels of hashes
        self._root: Optional[str] = None

    def build_from_chain(self, chain_file: Optional[Path] = None) -> str:
        """Build the Merkle tree from the chain state.

        Reads chain.json, extracts content_hashes of all blocks
        (excluding GENESIS), and builds the tree.

        Returns the root hash.
        """
        chain_file = chain_file or CHAIN_FILE
        if not chain_file.exists():
            raise FileNotFoundError(f"Chain file not found: {chain_file}")

        chain_data = json.loads(chain_file.read_text())
        blocks = chain_data.get("chain", [])

        self.leaves = []
        for block in blocks:
            if block["adr_id"] == "GENESIS":
                continue
            content_hash = block["content_hash"]
            leaf_hash = _hash_leaf(content_hash)
            self.leaves.append((block["adr_id"], content_hash, leaf_hash))

        if not self.leaves:
            self._root = hashlib.sha256(b"empty").hexdigest()
            self._tree_levels = [[self._root]]
            return self._root

        return self._build_tree()

    def _build_tree(self) -> str:
        """Build the binary Merkle tree bottom-up."""
        # Level 0 = leaf hashes
        current_level = [leaf_hash for _, _, leaf_hash in self.leaves]
        self._tree_levels = [current_level[:]]

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                # If odd number of nodes, duplicate the last one
                right = current_level[i + 1] if i + 1 < len(current_level) else current_level[i]
                parent = _hash_internal(left, right)
                next_level.append(parent)
            current_level = next_level
            self._tree_levels.append(current_level[:])

        self._root = current_level[0]
        return self._root

    @property
    def root(self) -> str:
        if self._root is None:
            raise RuntimeError("Tree not built. Call build_from_chain() first.")
        return self._root

    @property
    def height(self) -> int:
        return len(self._tree_levels)

    def generate_proof(self, adr_id: str) -> MerkleProof:
        """Generate an inclusion proof for a specific ADR."""
        if self._root is None:
            raise RuntimeError("Tree not built. Call build_from_chain() first.")

        # Find the leaf index
        leaf_index = None
        leaf_hash = None
        for i, (aid, _, lh) in enumerate(self.leaves):
            if aid == adr_id:
                leaf_index = i
                leaf_hash = lh
                break

        if leaf_index is None:
            raise ValueError(f"ADR '{adr_id}' not found in Merkle tree")

        # Walk up the tree collecting sibling hashes
        proof_path = []
        idx = leaf_index

        for level in self._tree_levels[:-1]:  # Skip root level
            sibling_idx = idx ^ 1  # XOR to get sibling index

            if sibling_idx < len(level):
                sibling_hash = level[sibling_idx]
            else:
                sibling_hash = level[idx]  # Odd node duplicated

            side = "right" if idx % 2 == 0 else "left"
            proof_path.append({"hash": sibling_hash, "side": side})

            idx = idx // 2

        return MerkleProof(
            adr_id=adr_id,
            leaf_hash=leaf_hash,
            proof_path=proof_path,
            root_hash=self._root,
            tree_size=len(self.leaves),
        )

    @staticmethod
    def verify_proof(proof: MerkleProof) -> bool:
        """Verify a Merkle inclusion proof."""
        current_hash = proof.leaf_hash

        for step in proof.proof_path:
            sibling = step["hash"]
            side = step["side"]

            if side == "right":
                # Sibling is to the right, current is left
                current_hash = _hash_internal(current_hash, sibling)
            else:
                # Sibling is to the left, current is right
                current_hash = _hash_internal(sibling, current_hash)

        return current_hash == proof.root_hash

    def save_state(self, state_file: Optional[Path] = None):
        """Save Merkle tree state to disk."""
        state_file = state_file or MERKLE_STATE_FILE
        state_file.parent.mkdir(parents=True, exist_ok=True)

        chain_data = json.loads(CHAIN_FILE.read_text()) if CHAIN_FILE.exists() else {}

        state = MerkleState(
            root_hash=self._root or "",
            height=self.height,
            leaf_count=len(self.leaves),
            computed_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            chain_height_at_computation=chain_data.get("height", 0),
            leaves=[
                {"adr_id": aid, "content_hash": ch, "leaf_hash": lh}
                for aid, ch, lh in self.leaves
            ],
        )

        state_file.write_text(json.dumps(state.to_dict(), indent=2) + "\n")

    def load_state(self, state_file: Optional[Path] = None) -> Optional[MerkleState]:
        """Load Merkle state from disk."""
        state_file = state_file or MERKLE_STATE_FILE
        if not state_file.exists():
            return None
        return MerkleState.from_dict(json.loads(state_file.read_text()))


# --- CLI ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ADR-Ledger Merkle Tree")
    sub = parser.add_subparsers(dest="command")

    # build
    sub.add_parser("build", help="Build Merkle tree from chain state")

    # root
    sub.add_parser("root", help="Show current Merkle root hash")

    # prove
    prove_p = sub.add_parser("prove", help="Generate inclusion proof for an ADR")
    prove_p.add_argument("adr_id", help="ADR ID (e.g., ADR-0001)")
    prove_p.add_argument("--output", help="Output proof to file")

    # verify-proof
    vp = sub.add_parser("verify-proof", help="Verify a Merkle inclusion proof")
    vp.add_argument("proof_file", help="Path to proof JSON file")

    # status
    sub.add_parser("status", help="Show Merkle tree status")

    args = parser.parse_args()
    tree = MerkleTree()

    if args.command == "build":
        root = tree.build_from_chain()
        tree.save_state()
        print(f"Merkle tree built:")
        print(f"  Root:   {root[:32]}...")
        print(f"  Leaves: {len(tree.leaves)}")
        print(f"  Height: {tree.height} levels")

    elif args.command == "root":
        state = tree.load_state()
        if state:
            print(state.root_hash)
        else:
            print("Merkle tree not built. Run: adr merkle build", file=sys.stderr)
            sys.exit(1)

    elif args.command == "prove":
        tree.build_from_chain()
        proof = tree.generate_proof(args.adr_id)
        proof_json = proof.to_json()

        if args.output:
            Path(args.output).write_text(proof_json + "\n")
            print(f"Proof written to {args.output}")
        else:
            print(proof_json)

        # Immediately verify
        valid = MerkleTree.verify_proof(proof)
        print(f"\nSelf-verification: {'VALID' if valid else 'INVALID'}", file=sys.stderr)

    elif args.command == "verify-proof":
        proof_data = json.loads(Path(args.proof_file).read_text())
        proof = MerkleProof.from_dict(proof_data)
        valid = MerkleTree.verify_proof(proof)
        print(f"Proof for {proof.adr_id}: {'VALID' if valid else 'INVALID'}")
        print(f"  Leaf hash: {proof.leaf_hash[:32]}...")
        print(f"  Root hash: {proof.root_hash[:32]}...")
        print(f"  Tree size: {proof.tree_size}")
        print(f"  Proof steps: {len(proof.proof_path)}")
        sys.exit(0 if valid else 1)

    elif args.command == "status":
        state = tree.load_state()
        if not state:
            print("Merkle tree not built. Run: adr merkle build")
            return
        print(f"Merkle Tree Status:")
        print(f"  Root:       {state.root_hash[:32]}...")
        print(f"  Height:     {state.height} levels")
        print(f"  Leaves:     {state.leaf_count}")
        print(f"  Computed:   {state.computed_at}")
        print(f"  Chain height at computation: {state.chain_height_at_computation}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
