"""
ADR-Ledger Decision Economics

Quality tracking and feedback loops for architectural decisions.
Measures decision health over time: implementation compliance,
time-to-supersede, downstream impact, and composite quality scores.
"""

import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

CHAIN_DIR = Path(__file__).parent
ECONOMICS_DIR = CHAIN_DIR / "economics"
METRICS_FILE = ECONOMICS_DIR / "metrics.json"
ADR_ROOT = CHAIN_DIR.parent / "adr"


@dataclass
class DecisionMetrics:
    adr_id: str
    title: str
    classification: str
    status: str
    date_proposed: Optional[str]
    date_accepted: Optional[str]
    date_superseded: Optional[str]
    time_to_acceptance_days: Optional[int]
    time_to_supersede_days: Optional[int]
    is_active: bool
    active_duration_days: int
    implementation_tasks_total: int
    implementation_tasks_done: int
    implementation_compliance: float      # 0.0-1.0
    downstream_issues: int                # Manually tracked
    review_depth: int                     # Number of changelog entries
    has_provenance: bool
    has_chain_signatures: bool
    risk_count: int
    alternative_count: int
    quality_score: float                  # Composite 0.0-1.0
    projects: List[str]

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DecisionMetrics":
        return cls(**d)


class EconomicsEngine:
    """Computes decision quality metrics and generates reports."""

    def __init__(self):
        ECONOMICS_DIR.mkdir(parents=True, exist_ok=True)

    def _parse_frontmatter(self, file_path: str) -> dict:
        """Parse YAML frontmatter from an ADR file."""
        content = Path(file_path).read_text()
        match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        if not match:
            return {}
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        if not date_str:
            return None
        try:
            return datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            return None

    def _compute_quality_score(self, m: DecisionMetrics) -> float:
        """Composite quality score formula.

        Weights:
          0.25 - Implementation compliance
          0.20 - Low downstream issues
          0.15 - Review depth (min 2 reviews for full score)
          0.15 - Has provenance tracking
          0.10 - Has chain signatures
          0.10 - Risk analysis depth
          0.05 - Alternatives considered
        """
        impl = m.implementation_compliance

        # Fewer issues = better (max 10 issues mapped to 0.0)
        issue_score = max(0.0, 1.0 - (m.downstream_issues / 10.0))

        # Review depth: 2+ reviews for full score
        review_score = min(m.review_depth / 2.0, 1.0)

        provenance_score = 1.0 if m.has_provenance else 0.0
        signature_score = 1.0 if m.has_chain_signatures else 0.0

        # Risk analysis: at least 2 risks identified
        risk_score = min(m.risk_count / 2.0, 1.0)

        # Alternatives: at least 2 alternatives considered
        alt_score = min(m.alternative_count / 2.0, 1.0)

        return round(
            0.25 * impl
            + 0.20 * issue_score
            + 0.15 * review_score
            + 0.15 * provenance_score
            + 0.10 * signature_score
            + 0.10 * risk_score
            + 0.05 * alt_score,
            3,
        )

    def compute_metrics(self, adr_file: str) -> DecisionMetrics:
        """Compute metrics for a single ADR."""
        fm = self._parse_frontmatter(adr_file)

        adr_id = fm.get("id", Path(adr_file).stem[:8])
        title = fm.get("title", "")
        governance = fm.get("governance", {})
        scope = fm.get("scope", {})
        audit = fm.get("audit", {})
        impl = fm.get("implementation", {})

        classification = governance.get("classification", fm.get("classification", "unknown"))
        status = fm.get("status", "unknown")
        projects = scope.get("projects", fm.get("projects", []))
        if isinstance(projects, str):
            projects = [projects]

        # Dates
        date_str = str(fm.get("date", ""))
        created_at = audit.get("created_at", date_str)
        date_proposed = created_at if created_at else date_str
        date_accepted = date_str if status == "accepted" else None
        date_superseded = None  # Would need to check superseded dir

        # Time calculations
        proposed_dt = self._parse_date(date_proposed)
        accepted_dt = self._parse_date(date_accepted)
        now = datetime.now()

        time_to_acceptance = None
        if proposed_dt and accepted_dt:
            time_to_acceptance = (accepted_dt - proposed_dt).days

        is_active = status == "accepted"
        active_duration = 0
        if is_active and accepted_dt:
            active_duration = (now - accepted_dt).days

        # Implementation tasks
        tasks = impl.get("tasks", fm.get("tasks", []))
        if isinstance(tasks, list):
            total_tasks = len(tasks)
            done_tasks = sum(
                1 for t in tasks
                if isinstance(t, dict) and t.get("status", "").lower() in ("done", "completed")
            )
        else:
            total_tasks = 0
            done_tasks = 0

        impl_compliance = done_tasks / total_tasks if total_tasks > 0 else 1.0

        # Review depth from changelog
        changelog = audit.get("changelog", fm.get("changelog", []))
        review_depth = len(changelog) if isinstance(changelog, list) else 0

        # Risk & alternatives
        rationale = fm.get("rationale", {})
        risks = fm.get("risks", rationale.get("risks", []))
        risk_count = len(risks) if isinstance(risks, list) else 0

        alternatives = rationale.get("alternatives_considered", fm.get("alternatives_considered", []))
        alt_count = len(alternatives) if isinstance(alternatives, list) else 0

        # Provenance check
        prov_file = CHAIN_DIR / "provenance" / f"{adr_id}.json"
        has_provenance = prov_file.exists()

        # Chain signature check
        has_signatures = False
        chain_file = CHAIN_DIR / "chain.json"
        if chain_file.exists():
            chain_data = json.loads(chain_file.read_text())
            for block in chain_data.get("chain", []):
                if block.get("adr_id") == adr_id and block.get("signatures"):
                    has_signatures = True
                    break

        metrics = DecisionMetrics(
            adr_id=adr_id,
            title=title,
            classification=classification,
            status=status,
            date_proposed=date_proposed,
            date_accepted=date_accepted,
            date_superseded=date_superseded,
            time_to_acceptance_days=time_to_acceptance,
            time_to_supersede_days=None,
            is_active=is_active,
            active_duration_days=active_duration,
            implementation_tasks_total=total_tasks,
            implementation_tasks_done=done_tasks,
            implementation_compliance=round(impl_compliance, 3),
            downstream_issues=0,  # Must be manually tracked
            review_depth=review_depth,
            has_provenance=has_provenance,
            has_chain_signatures=has_signatures,
            risk_count=risk_count,
            alternative_count=alt_count,
            quality_score=0.0,
            projects=projects,
        )

        metrics.quality_score = self._compute_quality_score(metrics)
        return metrics

    def compute_all(self) -> List[DecisionMetrics]:
        """Compute metrics for all accepted ADRs."""
        metrics = []
        accepted_dir = ADR_ROOT / "accepted"
        if not accepted_dir.exists():
            return metrics

        for md in sorted(accepted_dir.glob("ADR-*.md")):
            m = self.compute_metrics(str(md))
            metrics.append(m)

        return metrics

    def generate_report(self) -> dict:
        """Generate a comprehensive economics report."""
        all_metrics = self.compute_all()

        if not all_metrics:
            return {"total": 0, "metrics": [], "summary": {}}

        scores = [m.quality_score for m in all_metrics]
        avg_score = sum(scores) / len(scores) if scores else 0

        # By classification
        by_class = {}
        for m in all_metrics:
            c = m.classification
            if c not in by_class:
                by_class[c] = {"count": 0, "avg_quality": 0, "scores": []}
            by_class[c]["count"] += 1
            by_class[c]["scores"].append(m.quality_score)

        for c, data in by_class.items():
            data["avg_quality"] = round(sum(data["scores"]) / len(data["scores"]), 3)
            del data["scores"]

        # By project
        by_project = {}
        for m in all_metrics:
            for p in m.projects:
                if p not in by_project:
                    by_project[p] = {"count": 0, "avg_quality": 0, "scores": []}
                by_project[p]["count"] += 1
                by_project[p]["scores"].append(m.quality_score)

        for p, data in by_project.items():
            data["avg_quality"] = round(sum(data["scores"]) / len(data["scores"]), 3)
            del data["scores"]

        # Health indicators
        low_quality = [m for m in all_metrics if m.quality_score < 0.4]
        unsigned = [m for m in all_metrics if not m.has_chain_signatures]
        no_provenance = [m for m in all_metrics if not m.has_provenance]

        report = {
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "total_decisions": len(all_metrics),
            "average_quality_score": round(avg_score, 3),
            "by_classification": by_class,
            "by_project": by_project,
            "health": {
                "low_quality_count": len(low_quality),
                "low_quality_ids": [m.adr_id for m in low_quality],
                "unsigned_count": len(unsigned),
                "unsigned_ids": [m.adr_id for m in unsigned],
                "no_provenance_count": len(no_provenance),
                "no_provenance_ids": [m.adr_id for m in no_provenance],
            },
            "metrics": [m.to_dict() for m in all_metrics],
        }

        # Save report
        METRICS_FILE.write_text(json.dumps(report, indent=2) + "\n")

        return report


# --- CLI ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ADR-Ledger Decision Economics")
    sub = parser.add_subparsers(dest="command")

    # report
    sub.add_parser("report", help="Generate full economics report")

    # score
    sc = sub.add_parser("score", help="Show quality score for an ADR")
    sc.add_argument("adr_id", help="ADR ID")

    # health
    sub.add_parser("health", help="Show ledger health indicators")

    # leaderboard
    sub.add_parser("leaderboard", help="Show ADRs ranked by quality score")

    args = parser.parse_args()
    engine = EconomicsEngine()

    if args.command == "report":
        report = engine.generate_report()
        print(f"Economics Report ({report['generated_at']}):")
        print(f"  Total decisions:       {report['total_decisions']}")
        print(f"  Average quality score: {report['average_quality_score']}")
        print(f"\n  By Classification:")
        for cls, data in report["by_classification"].items():
            print(f"    {cls:12s}: {data['count']:3d} ADRs, avg quality {data['avg_quality']}")
        print(f"\n  By Project:")
        for proj, data in report["by_project"].items():
            print(f"    {proj:12s}: {data['count']:3d} ADRs, avg quality {data['avg_quality']}")
        print(f"\n  Health:")
        h = report["health"]
        print(f"    Low quality (<0.4): {h['low_quality_count']}")
        print(f"    Unsigned:           {h['unsigned_count']}")
        print(f"    No provenance:      {h['no_provenance_count']}")
        print(f"\n  Report saved to: {METRICS_FILE}")

    elif args.command == "score":
        # Find the ADR file
        adr_file = None
        for status_dir in ["accepted", "proposed", "superseded"]:
            from glob import glob
            matches = glob(str(ADR_ROOT / status_dir / f"{args.adr_id}*.md"))
            if matches:
                adr_file = matches[0]
                break

        if not adr_file:
            print(f"ADR not found: {args.adr_id}", file=sys.stderr)
            sys.exit(1)

        m = engine.compute_metrics(adr_file)
        print(f"Quality Score for {m.adr_id}: {m.quality_score}")
        print(f"  Classification:        {m.classification}")
        print(f"  Implementation:        {m.implementation_compliance:.0%}")
        print(f"  Review depth:          {m.review_depth}")
        print(f"  Risks analyzed:        {m.risk_count}")
        print(f"  Alternatives:          {m.alternative_count}")
        print(f"  Has provenance:        {m.has_provenance}")
        print(f"  Has chain signatures:  {m.has_chain_signatures}")
        print(f"  Active duration:       {m.active_duration_days} days")

    elif args.command == "health":
        report = engine.generate_report()
        h = report["health"]
        total = report["total_decisions"]
        print("Ledger Health Check:")
        print(f"  Total decisions:  {total}")
        print(f"  Avg quality:      {report['average_quality_score']}")

        if h["low_quality_ids"]:
            print(f"\n  Low Quality ({h['low_quality_count']}):")
            for aid in h["low_quality_ids"]:
                print(f"    - {aid}")

        if h["unsigned_ids"]:
            print(f"\n  Unsigned ({h['unsigned_count']}):")
            for aid in h["unsigned_ids"]:
                print(f"    - {aid}")

    elif args.command == "leaderboard":
        all_metrics = engine.compute_all()
        ranked = sorted(all_metrics, key=lambda m: m.quality_score, reverse=True)
        print(f"{'Rank':>4}  {'ADR':12s}  {'Score':>6}  {'Class':12s}  {'Impl%':>5}  {'Title'}")
        print("-" * 80)
        for i, m in enumerate(ranked, 1):
            impl_pct = f"{m.implementation_compliance:.0%}"
            title = m.title[:35] if m.title else ""
            print(f"{i:4d}  {m.adr_id:12s}  {m.quality_score:6.3f}  {m.classification:12s}  {impl_pct:>5}  {title}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
