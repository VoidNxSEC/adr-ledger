"""
ADR-Ledger Cryptographic Primitives

Ed25519 digital signatures and SHA256 hashing utilities for the
private blockchain layer. Uses PyNaCl (libsodium bindings).
"""

import hashlib
import json
import os
import sys
import time
from base64 import b64decode, b64encode
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

try:
    from nacl.encoding import Base64Encoder
    from nacl.signing import SigningKey, VerifyKey
    from nacl.exceptions import BadSignatureError
    HAS_NACL = True
except ImportError:
    HAS_NACL = False


KEYS_DIR = Path(__file__).parent / "keys"


@dataclass
class KeyPair:
    name: str
    role: str
    public_key: str       # Base64-encoded Ed25519 public key
    created_at: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Signature:
    signer_id: str
    public_key: str       # Base64-encoded Ed25519 public key
    signature: str         # Base64-encoded Ed25519 signature
    timestamp: str
    role: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Signature":
        return cls(**d)


# --- Hashing ---

def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of an entire file's raw bytes."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_content_hash(content: str) -> str:
    """Compute SHA256 hash of a string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_block_hash(
    block_number: int,
    adr_id: str,
    content_hash: str,
    previous_hash: str,
    timestamp: str,
) -> str:
    """Compute deterministic block hash from canonical form."""
    canonical = f"{block_number}|{adr_id}|{content_hash}|{previous_hash}|{timestamp}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --- Ed25519 Key Management ---

def _require_nacl():
    if not HAS_NACL:
        print(
            "ERROR: PyNaCl is required for cryptographic operations.\n"
            "Install with: pip install pynacl  (or add to Nix devShell)",
            file=sys.stderr,
        )
        sys.exit(1)


def generate_keypair(name: str, role: str, keys_dir: Optional[Path] = None) -> KeyPair:
    """Generate an Ed25519 keypair and save to keys directory."""
    _require_nacl()
    keys_dir = keys_dir or KEYS_DIR
    keys_dir.mkdir(parents=True, exist_ok=True)

    pub_path = keys_dir / f"{name}.pub"
    key_path = keys_dir / f"{name}.key"

    if pub_path.exists():
        print(f"ERROR: Key already exists for '{name}'. Remove first to regenerate.", file=sys.stderr)
        sys.exit(1)

    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    pub_b64 = verify_key.encode(encoder=Base64Encoder).decode("ascii")
    key_b64 = signing_key.encode(encoder=Base64Encoder).decode("ascii")

    created_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    # Save public key (committed to git)
    pub_data = {
        "name": name,
        "role": role,
        "algorithm": "Ed25519",
        "public_key": pub_b64,
        "created_at": created_at,
    }
    pub_path.write_text(json.dumps(pub_data, indent=2) + "\n")

    # Save private key (GITIGNORED)
    key_data = {
        "name": name,
        "role": role,
        "algorithm": "Ed25519",
        "private_key": key_b64,
        "public_key": pub_b64,
        "created_at": created_at,
    }
    key_path.write_text(json.dumps(key_data, indent=2) + "\n")
    os.chmod(key_path, 0o600)

    return KeyPair(
        name=name,
        role=role,
        public_key=pub_b64,
        created_at=created_at,
    )


def load_signing_key(name: str, keys_dir: Optional[Path] = None) -> "SigningKey":
    """Load an Ed25519 private signing key."""
    _require_nacl()
    keys_dir = keys_dir or KEYS_DIR
    key_path = keys_dir / f"{name}.key"

    if not key_path.exists():
        print(f"ERROR: Private key not found for '{name}'. Run: adr keygen --name {name}", file=sys.stderr)
        sys.exit(1)

    key_data = json.loads(key_path.read_text())
    return SigningKey(key_data["private_key"].encode("ascii"), encoder=Base64Encoder)


def load_verify_key(name: str, keys_dir: Optional[Path] = None) -> "VerifyKey":
    """Load an Ed25519 public verification key."""
    _require_nacl()
    keys_dir = keys_dir or KEYS_DIR
    pub_path = keys_dir / f"{name}.pub"

    if not pub_path.exists():
        print(f"ERROR: Public key not found for '{name}'.", file=sys.stderr)
        sys.exit(1)

    pub_data = json.loads(pub_path.read_text())
    return VerifyKey(pub_data["public_key"].encode("ascii"), encoder=Base64Encoder)


def load_key_metadata(name: str, keys_dir: Optional[Path] = None) -> dict:
    """Load public key metadata (name, role, etc.)."""
    keys_dir = keys_dir or KEYS_DIR
    pub_path = keys_dir / f"{name}.pub"

    if not pub_path.exists():
        return {}

    return json.loads(pub_path.read_text())


def list_keys(keys_dir: Optional[Path] = None) -> list:
    """List all registered public keys."""
    keys_dir = keys_dir or KEYS_DIR
    if not keys_dir.exists():
        return []

    keys = []
    for pub_file in sorted(keys_dir.glob("*.pub")):
        data = json.loads(pub_file.read_text())
        has_private = (keys_dir / f"{pub_file.stem}.key").exists()
        data["has_private_key"] = has_private
        keys.append(data)
    return keys


# --- Signing & Verification ---

def sign_message(message: str, signer_name: str, keys_dir: Optional[Path] = None) -> Signature:
    """Sign a message with a named signer's Ed25519 private key."""
    _require_nacl()
    keys_dir = keys_dir or KEYS_DIR

    signing_key = load_signing_key(signer_name, keys_dir)
    key_meta = load_key_metadata(signer_name, keys_dir)

    signed = signing_key.sign(message.encode("utf-8"))
    sig_b64 = b64encode(signed.signature).decode("ascii")

    return Signature(
        signer_id=signer_name,
        public_key=key_meta.get("public_key", ""),
        signature=sig_b64,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        role=key_meta.get("role", "unknown"),
    )


def verify_signature(message: str, signature: Signature, keys_dir: Optional[Path] = None) -> bool:
    """Verify an Ed25519 signature against a message."""
    _require_nacl()
    keys_dir = keys_dir or KEYS_DIR

    try:
        verify_key = load_verify_key(signature.signer_id, keys_dir)
    except SystemExit:
        # No registered public key = untrusted signer
        return False

    try:
        sig_bytes = b64decode(signature.signature)
        verify_key.verify(message.encode("utf-8"), sig_bytes)
        return True
    except (BadSignatureError, Exception):
        return False


# --- CLI ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ADR-Ledger Crypto Utilities")
    sub = parser.add_subparsers(dest="command")

    # keygen
    kg = sub.add_parser("keygen", help="Generate Ed25519 keypair")
    kg.add_argument("--name", required=True, help="Signer name (e.g., 'pina')")
    kg.add_argument("--role", required=True, help="Role (architect, engineer, security_lead)")
    kg.add_argument("--keys-dir", help="Keys directory override")

    # list-keys
    sub.add_parser("list-keys", help="List registered keys")

    # hash-file
    hf = sub.add_parser("hash-file", help="Compute SHA256 of a file")
    hf.add_argument("file", help="File path")

    # sign
    sg = sub.add_parser("sign", help="Sign a message")
    sg.add_argument("--signer", required=True, help="Signer name")
    sg.add_argument("--message", required=True, help="Message to sign")

    # verify
    vf = sub.add_parser("verify", help="Verify a signature")
    vf.add_argument("--signer", required=True, help="Signer name")
    vf.add_argument("--message", required=True, help="Original message")
    vf.add_argument("--signature", required=True, help="Base64 signature")

    args = parser.parse_args()

    if args.command == "keygen":
        kd = Path(args.keys_dir) if args.keys_dir else None
        kp = generate_keypair(args.name, args.role, kd)
        print(f"Keypair generated for '{kp.name}' (role: {kp.role})")
        print(f"  Public key:  .chain/keys/{kp.name}.pub")
        print(f"  Private key: .chain/keys/{kp.name}.key (GITIGNORED)")

    elif args.command == "list-keys":
        keys = list_keys()
        if not keys:
            print("No keys registered. Run: adr keygen --name <name> --role <role>")
            return
        for k in keys:
            priv = "YES" if k.get("has_private_key") else "no"
            print(f"  {k['name']:20s} role={k['role']:15s} private_key={priv}")

    elif args.command == "hash-file":
        h = compute_file_hash(args.file)
        print(h)

    elif args.command == "sign":
        sig = sign_message(args.message, args.signer)
        print(json.dumps(sig.to_dict(), indent=2))

    elif args.command == "verify":
        sig = Signature(
            signer_id=args.signer,
            public_key="",
            signature=args.signature,
            timestamp="",
            role="",
        )
        valid = verify_signature(args.message, sig)
        print("VALID" if valid else "INVALID")
        sys.exit(0 if valid else 1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
