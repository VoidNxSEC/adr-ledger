#!/usr/bin/env python3.13
"""
ADR-Ledger Bitcoin-compatible attestation helper.

This module does not publish transactions on-chain. It creates and verifies
local ECDSA/secp256k1 attestations over ledger snapshots, which can later be
anchored or bridged to Bitcoin-native infrastructure.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


CHAIN_DIR = Path(__file__).parent
BITCOIN_DIR = CHAIN_DIR / "bitcoin"
KEYS_DIR = BITCOIN_DIR / "keys"
RECEIPTS_DIR = BITCOIN_DIR / "receipts"
SNAPSHOTS_DIR = CHAIN_DIR / "snapshots"
GOVERNANCE_FILE = CHAIN_DIR.parent / ".governance" / "governance.yaml"


@dataclass
class BitcoinReceipt:
    version: str
    algorithm: str
    target_type: str
    target_id: str
    target_hash: str
    payload: Dict[str, Any]
    payload_hash: str
    signer: str
    public_key_pem: str
    created_at: str
    signature: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "BitcoinReceipt":
        return cls(**payload)

    def signing_message(self) -> str:
        return (
            "ADR-LEDGER BITCOIN ATTESTATION\n"
            f"version:{self.version}\n"
            f"algorithm:{self.algorithm}\n"
            f"target_type:{self.target_type}\n"
            f"target_id:{self.target_id}\n"
            f"target_hash:{self.target_hash}\n"
            f"payload_hash:{self.payload_hash}\n"
            f"created_at:{self.created_at}\n"
        )


def ensure_dirs() -> None:
    KEYS_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)


def governance_config() -> Dict[str, Any]:
    config = {
        "enabled": True,
        "mode": "warn",
        "require_receipt_on_validate": False,
        "default_target": "latest_snapshot",
        "algorithm": "ecdsa-secp256k1-sha256",
    }

    if not GOVERNANCE_FILE.exists():
        return config

    try:
        loaded = yaml.safe_load(GOVERNANCE_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return config

    chain = loaded.get("chain", {}) or {}
    bitcoin = chain.get("bitcoin_attestations", {}) or {}
    config.update({key: value for key, value in bitcoin.items() if value is not None})
    return config


def openssl_bin() -> str:
    path = shutil.which("openssl")
    if path is None:
        print(
            "ERROR: openssl not found on PATH. Use `nix develop --command` or add nixpkgs#openssl.",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


def run_openssl(args: List[str], *, input_bytes: Optional[bytes] = None) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [openssl_bin(), *args],
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or "openssl command failed")
    return result


def snapshot_path(snapshot_id: Optional[int] = None) -> Path:
    if snapshot_id is None:
        files = sorted(SNAPSHOTS_DIR.glob("snapshot_*.json"))
        if not files:
            raise FileNotFoundError("No snapshots found. Run `adr snapshot create` first.")
        return files[-1]

    path = SNAPSHOTS_DIR / f"snapshot_{snapshot_id:04d}.json"
    if not path.exists():
        raise FileNotFoundError(f"Snapshot {snapshot_id} not found: {path}")
    return path


def build_snapshot_target(snapshot_id: Optional[int] = None) -> Dict[str, Any]:
    path = snapshot_path(snapshot_id)
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    return {
        "target_type": "snapshot",
        "target_id": f"snapshot_{int(snapshot['snapshot_id']):04d}",
        "target_hash": snapshot["snapshot_hash"],
        "payload": {
            "snapshot_id": int(snapshot["snapshot_id"]),
            "timestamp": snapshot["timestamp"],
            "chain_height": snapshot["chain_height"],
            "chain_tip": snapshot["chain_tip"],
            "merkle_root": snapshot.get("merkle_root", ""),
            "sbom_hash": snapshot.get("sbom_hash"),
            "timestamp_proof": snapshot.get("timestamp_proof"),
        },
    }


def canonical_payload_hash(payload: Dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def key_paths(name: str) -> Dict[str, Path]:
    return {
        "private": KEYS_DIR / f"{name}.pem",
        "public": KEYS_DIR / f"{name}.pub.pem",
    }


def keygen(name: str) -> None:
    ensure_dirs()
    paths = key_paths(name)

    if paths["private"].exists() or paths["public"].exists():
        print(f"ERROR: key already exists for {name}", file=sys.stderr)
        sys.exit(1)

    run_openssl(["ecparam", "-name", "secp256k1", "-genkey", "-noout", "-out", str(paths["private"])])
    run_openssl(["ec", "-in", str(paths["private"]), "-pubout", "-out", str(paths["public"])])

    print(f"Generated secp256k1 keypair for {name}:")
    print(f"  Private: {paths['private']}")
    print(f"  Public:  {paths['public']}")


def sign_message(message: str, private_key: Path) -> str:
    with tempfile.NamedTemporaryFile("wb", delete=False, prefix="adr-btc-msg.") as tmp_message:
        tmp_message.write(message.encode("utf-8"))
        message_path = Path(tmp_message.name)

    with tempfile.NamedTemporaryFile("wb", delete=False, prefix="adr-btc-sig.") as tmp_sig:
        signature_path = Path(tmp_sig.name)

    try:
        run_openssl(
            ["dgst", "-sha256", "-sign", str(private_key), "-out", str(signature_path), str(message_path)]
        )
        signature = base64.b64encode(signature_path.read_bytes()).decode("ascii")
    finally:
        message_path.unlink(missing_ok=True)
        signature_path.unlink(missing_ok=True)

    return signature


def verify_signature(message: str, public_key_pem: str, signature_b64: str) -> bool:
    with tempfile.NamedTemporaryFile("wb", delete=False, prefix="adr-btc-pub.") as tmp_pub:
        pub_path = Path(tmp_pub.name)
        tmp_pub.write(public_key_pem.encode("utf-8"))

    with tempfile.NamedTemporaryFile("wb", delete=False, prefix="adr-btc-msg.") as tmp_message:
        msg_path = Path(tmp_message.name)
        tmp_message.write(message.encode("utf-8"))

    with tempfile.NamedTemporaryFile("wb", delete=False, prefix="adr-btc-sig.") as tmp_sig:
        sig_path = Path(tmp_sig.name)
        tmp_sig.write(base64.b64decode(signature_b64.encode("ascii")))

    try:
        result = subprocess.run(
            [openssl_bin(), "dgst", "-sha256", "-verify", str(pub_path), "-signature", str(sig_path), str(msg_path)],
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    finally:
        pub_path.unlink(missing_ok=True)
        msg_path.unlink(missing_ok=True)
        sig_path.unlink(missing_ok=True)


def attest_snapshot(signer: str, snapshot_id: Optional[int] = None, notes: str = "") -> BitcoinReceipt:
    ensure_dirs()
    paths = key_paths(signer)
    if not paths["private"].exists():
        print(f"ERROR: private key not found for {signer}: {paths['private']}", file=sys.stderr)
        sys.exit(1)
    if not paths["public"].exists():
        print(f"ERROR: public key not found for {signer}: {paths['public']}", file=sys.stderr)
        sys.exit(1)

    target = build_snapshot_target(snapshot_id)
    created_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    payload_hash = canonical_payload_hash(target["payload"])
    public_key_pem = paths["public"].read_text(encoding="utf-8")

    receipt = BitcoinReceipt(
        version="1.0",
        algorithm=governance_config().get("algorithm", "ecdsa-secp256k1-sha256"),
        target_type=target["target_type"],
        target_id=target["target_id"],
        target_hash=target["target_hash"],
        payload=target["payload"],
        payload_hash=payload_hash,
        signer=signer,
        public_key_pem=public_key_pem,
        created_at=created_at,
        notes=notes,
    )
    receipt.signature = sign_message(receipt.signing_message(), paths["private"])

    receipt_path = RECEIPTS_DIR / f"{receipt.target_id}.json"
    receipt_path.write_text(json.dumps(receipt.to_dict(), indent=2) + "\n", encoding="utf-8")
    print(f"Bitcoin-compatible receipt created: {receipt_path}")
    print(f"  Target:    {receipt.target_id}")
    print(f"  Hash:      {receipt.target_hash[:32]}...")
    print(f"  Signer:    {receipt.signer}")
    return receipt


def current_target_hash(target_type: str, target_id: str) -> str:
    if target_type != "snapshot":
        raise ValueError(f"Unsupported target_type: {target_type}")

    snapshot_number = int(target_id.split("_")[1])
    target = build_snapshot_target(snapshot_number)
    return target["target_hash"]


def verify_receipt(receipt_path: Path) -> Dict[str, Any]:
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt = BitcoinReceipt.from_dict(payload)

    report = {
        "receipt": str(receipt_path.relative_to(RECEIPTS_DIR.parent)),
        "target_id": receipt.target_id,
        "payload_hash_valid": False,
        "signature_valid": False,
        "target_hash_valid": False,
        "valid": False,
        "errors": [],
    }

    actual_payload_hash = canonical_payload_hash(receipt.payload)
    report["payload_hash_valid"] = actual_payload_hash == receipt.payload_hash
    if not report["payload_hash_valid"]:
        report["errors"].append(
            f"payload hash mismatch ({actual_payload_hash[:16]}... != {receipt.payload_hash[:16]}...)"
        )

    if verify_signature(receipt.signing_message(), receipt.public_key_pem, receipt.signature):
        report["signature_valid"] = True
    else:
        report["errors"].append("signature verification failed")

    try:
        live_target_hash = current_target_hash(receipt.target_type, receipt.target_id)
        report["target_hash_valid"] = live_target_hash == receipt.target_hash
        if not report["target_hash_valid"]:
            report["errors"].append(
                f"target hash mismatch ({live_target_hash[:16]}... != {receipt.target_hash[:16]}...)"
            )
    except Exception as exc:
        report["errors"].append(str(exc))

    report["valid"] = (
        report["payload_hash_valid"]
        and report["signature_valid"]
        and report["target_hash_valid"]
    )
    return report


def verify_all() -> int:
    config = governance_config()
    if not config.get("enabled", True):
        print("[INFO] Bitcoin attestation verification is disabled by governance config")
        return 0

    receipts = sorted(RECEIPTS_DIR.glob("*.json")) if RECEIPTS_DIR.exists() else []

    if not receipts:
        message = "No Bitcoin attestation receipts found"
        if config.get("require_receipt_on_validate") or config.get("mode") == "enforce":
            print(f"ERROR: {message}", file=sys.stderr)
            return 1
        print(f"[WARN] {message}")
        return 0

    failures = 0
    for receipt in receipts:
        report = verify_receipt(receipt)
        status = "OK" if report["valid"] else "FAIL"
        print(f"[{status}] {report['target_id']} ({report['receipt']})")
        for error in report["errors"]:
            print(f"  - {error}")
        if not report["valid"]:
            failures += 1

    if failures:
        return 1
    print(f"Verified {len(receipts)} Bitcoin-compatible receipt(s)")
    return 0


def list_receipts() -> None:
    receipts = sorted(RECEIPTS_DIR.glob("*.json")) if RECEIPTS_DIR.exists() else []
    if not receipts:
        print("No Bitcoin attestation receipts found")
        return

    for receipt_path in receipts:
        payload = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt = BitcoinReceipt.from_dict(payload)
        print(
            f"{receipt.target_id:<18} signer={receipt.signer:<16} "
            f"created_at={receipt.created_at} file={receipt_path.name}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ADR-Ledger Bitcoin-compatible attestation helper")
    sub = parser.add_subparsers(dest="command", required=True)

    keygen_cmd = sub.add_parser("keygen", help="Generate a secp256k1 keypair")
    keygen_cmd.add_argument("--name", required=True, help="Key name")

    attest_cmd = sub.add_parser("attest", help="Create a snapshot attestation receipt")
    attest_cmd.add_argument("--signer", required=True, help="Existing key name under .chain/bitcoin/keys")
    attest_cmd.add_argument("--snapshot-id", type=int, help="Snapshot id to attest (default: latest)")
    attest_cmd.add_argument("--notes", default="", help="Optional free-form notes")

    verify_cmd = sub.add_parser("verify", help="Verify a single attestation receipt")
    verify_cmd.add_argument("receipt", help="Receipt JSON path")

    sub.add_parser("verify-all", help="Verify all attestation receipts")
    sub.add_parser("list", help="List attestation receipts")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.command == "keygen":
        keygen(args.name)
        return 0

    if args.command == "attest":
        attest_snapshot(args.signer, snapshot_id=args.snapshot_id, notes=args.notes)
        return 0

    if args.command == "verify":
        report = verify_receipt(Path(args.receipt))
        status = "VALID" if report["valid"] else "INVALID"
        print(f"{report['target_id']}: {status}")
        for error in report["errors"]:
            print(f"  - {error}")
        return 0 if report["valid"] else 1

    if args.command == "verify-all":
        return verify_all()

    if args.command == "list":
        list_receipts()
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
