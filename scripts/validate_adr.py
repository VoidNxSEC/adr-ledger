#!/usr/bin/env python3.13
"""
ADR-Ledger validator.

Performs:
1. YAML frontmatter parsing
2. JSON schema validation against combined frontmatter + Markdown sections
3. Optional OPA policy evaluation for governance rules
4. Placeholder detection for draft templates
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml
from jsonschema import Draft7Validator, FormatChecker


FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
SECTION_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

PLACEHOLDER_PATTERNS = [
    re.compile(r"\[Descreva[^\]]*\]"),
    re.compile(r"\[Timeline estimado\]"),
    re.compile(r"\[Link para documentação relevante\]"),
    re.compile(r"\[Driver 1\]"),
    re.compile(r"\[Trade-off aceito\]"),
    re.compile(r"\[Consequência positiva\]"),
    re.compile(r"\[Consequência negativa\]"),
    re.compile(r"\[Risk\]"),
    re.compile(r"\[Mitigation\]"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ADR-Ledger documents")
    parser.add_argument(
        "path",
        nargs="?",
        default="adr",
        help="ADR file or directory to validate (default: adr)",
    )
    parser.add_argument(
        "--schema",
        default=".schema/adr.schema.json",
        help="JSON schema path (default: .schema/adr.schema.json)",
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip JSON schema validation",
    )
    parser.add_argument(
        "--schema-mode",
        choices=["enforce", "warn"],
        default="enforce",
        help="Schema validation severity (default: enforce)",
    )
    parser.add_argument(
        "--opa-policy",
        help="OPA/Rego policy to evaluate against each ADR",
    )
    parser.add_argument(
        "--opa-query",
        default="data.adr.validation.result",
        help="OPA query to evaluate (default: data.adr.validation.result)",
    )
    parser.add_argument(
        "--skip-opa",
        action="store_true",
        help="Skip OPA policy evaluation even if a policy path is provided",
    )
    return parser.parse_args()


def iter_adr_files(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    if not target.exists():
        raise FileNotFoundError(f"{target} not found")
    return sorted(target.glob("*/*.md"))


def parse_sections(body: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    parts = SECTION_PATTERN.split(body)

    for index in range(1, len(parts), 2):
        header = parts[index].strip().lower().replace(" ", "_")
        content = parts[index + 1].strip() if index + 1 < len(parts) else ""
        sections[header] = content

    return sections


def load_document(path: Path, repo_root: Path) -> Tuple[Dict[str, Any], str]:
    content = path.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(content)
    if not match:
        raise ValueError("missing YAML frontmatter")

    frontmatter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(frontmatter, dict):
        raise ValueError("frontmatter must decode to a mapping")

    body = match.group(2)
    sections = parse_sections(body)

    document = dict(frontmatter)
    document["context"] = sections.get("context", "")
    document["decision"] = sections.get("decision", "")
    document["_meta"] = {
        "file_path": str(path.relative_to(repo_root)),
        "status_dir": path.parent.name,
        "has_placeholders": has_placeholders(content),
    }
    return document, content


def has_placeholders(content: str) -> bool:
    return any(pattern.search(content) for pattern in PLACEHOLDER_PATTERNS)


def detect_placeholders(content: str) -> List[str]:
    warnings = []
    for pattern in PLACEHOLDER_PATTERNS:
        match = pattern.search(content)
        if match:
            warnings.append(f"placeholder found: {match.group(0)}")
    return warnings


def format_schema_error(error: Any) -> str:
    path = ".".join(str(component) for component in error.absolute_path) or "<root>"
    return f"{path}: {error.message}"


def validate_schema(document: Dict[str, Any], schema_path: Path) -> List[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft7Validator(schema, format_checker=FormatChecker())
    return [format_schema_error(error) for error in sorted(validator.iter_errors(document), key=str)]


def evaluate_opa(document: Dict[str, Any], policy_path: Path, query: str) -> Tuple[List[str], List[str], List[str]]:
    opa_bin = shutil.which("opa")
    if opa_bin is None:
        raise RuntimeError("OPA CLI not found on PATH. Use `nix develop --command` or add nixpkgs#open-policy-agent.")

    with tempfile.TemporaryDirectory(prefix="adr-opa.") as tmp_dir:
        input_path = Path(tmp_dir) / "input.json"
        input_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        result = subprocess.run(
            [
                opa_bin,
                "eval",
                "--format",
                "json",
                "--data",
                str(policy_path),
                "--input",
                str(input_path),
                query,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    if result.returncode != 0:
        stderr = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"OPA evaluation failed: {stderr}")

    payload = json.loads(result.stdout)
    values = payload.get("result", [])
    if not values:
        return [], [], []

    expressions = values[0].get("expressions", [])
    if not expressions:
        return [], [], []

    opa_result = expressions[0].get("value", {}) or {}
    deny = opa_result.get("deny", []) or []
    warn = opa_result.get("warn", []) or []
    notes = opa_result.get("notes", []) or []
    return list(deny), list(warn), list(notes)


def main() -> int:
    args = parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    target = Path(args.path)
    if not target.is_absolute():
        target = (Path.cwd() / target).resolve()

    schema_path = Path(args.schema)
    if not schema_path.is_absolute():
        schema_path = (repo_root / schema_path).resolve()

    policy_path = None
    if args.opa_policy:
        policy_path = Path(args.opa_policy)
        if not policy_path.is_absolute():
            policy_path = (repo_root / policy_path).resolve()

    try:
        files = iter_adr_files(target)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    if not files:
        print(f"[INFO] No ADRs found in {target}")
        return 0

    errors = 0
    schema_warnings = 0
    for adr_file in files:
        file_errors: List[str] = []
        file_warnings: List[str] = []
        file_notes: List[str] = []
        schema_errors: List[str] = []

        try:
            document, content = load_document(adr_file, repo_root)
        except Exception as exc:
            print(f"[ERROR] {adr_file.name}: {exc}")
            errors += 1
            continue

        if not args.skip_schema:
            schema_errors.extend(validate_schema(document, schema_path))
            if args.schema_mode == "enforce":
                file_errors.extend(schema_errors)
            else:
                file_warnings.extend([f"schema drift: {item}" for item in schema_errors])
                schema_warnings += len(schema_errors)

        file_warnings.extend(detect_placeholders(content))

        if policy_path and not args.skip_opa:
            try:
                deny, warn, notes = evaluate_opa(document, policy_path, args.opa_query)
            except Exception as exc:
                print(f"[ERROR] {adr_file.name}: {exc}")
                errors += 1
                continue
            file_errors.extend(deny)
            file_warnings.extend(warn)
            file_notes.extend(notes)

        if file_errors:
            print(f"[ERROR] {adr_file.name}:")
            for item in file_errors:
                print(f"  - {item}")
            errors += 1
        else:
            print(f"[OK] {adr_file.name}")

        for item in file_warnings:
            print(f"[WARN] {adr_file.name}: {item}")
        for item in file_notes:
            print(f"[INFO] {adr_file.name}: {item}")

    if errors:
        print(f"\nValidation failed: {errors} ADR(s) with errors", file=sys.stderr)
        return 1

    if schema_warnings and args.schema_mode == "warn":
        print(f"\nValidation completed with {schema_warnings} schema warning(s)")
        return 0

    print(f"\nAll {len(files)} ADR(s) validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
