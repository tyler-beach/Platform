"""CLI: python3 -m tools.adr_pack <validate|scaffold|build> …"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .commands import build_pack, scaffold_adrs, validate_adrs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.adr_pack",
        description=(
            "Deterministic ADR pack helper: validate markdown structure, "
            "scaffold typed sidecars, build Pathfinder catalog artifacts. "
            "Does not call models or network APIs."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Lint ADR markdown + sidecar readiness")
    p_val.add_argument("adrs_dir", type=Path, help="Directory of *.md ADRs")
    p_val.add_argument("--json", action="store_true", help="Emit JSON report")

    p_sc = sub.add_parser("scaffold", help="Write draft .md.req.json sidecars")
    p_sc.add_argument("adrs_dir", type=Path)
    p_sc.add_argument("--force", action="store_true", help="Overwrite approved sidecars")
    p_sc.add_argument(
        "--predicates",
        type=Path,
        default=None,
        help="Optional predicates.json to hint known predicate ids",
    )
    p_sc.add_argument(
        "--no-heuristics",
        action="store_true",
        help="Do not fill kind/limit suggestions from Decision text",
    )

    p_b = sub.add_parser("build", help="Emit requirements.jsonl + predicates + manifest")
    p_b.add_argument("adrs_dir", type=Path)
    p_b.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Output catalog directory (receives json/jsonl/manifest)",
    )
    p_b.add_argument("--catalog-id", default="company-adr-pack")
    p_b.add_argument(
        "--base-predicates",
        type=Path,
        default=None,
        help="Existing predicates.json to merge (e.g. data/adr_catalog/predicates.json)",
    )
    p_b.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any ADR lacks an approved complete sidecar",
    )

    args = parser.parse_args(argv)

    if args.cmd == "validate":
        err_count, reports = validate_adrs(args.adrs_dir)
        if args.json:
            print(json.dumps({"error_count": err_count, "adrs": reports}, indent=2))
        else:
            for r in reports:
                status = "READY" if r["pack_ready"] else "NOT_READY"
                print(f"{r['path']}: {status}")
                for e in r["errors"]:
                    print(f"  ERROR: {e}")
                for w in r["warnings"]:
                    print(f"  WARN: {w}")
            print(f"\n{len(reports)} ADR(s); {err_count} error(s)")
        return 1 if err_count else 0

    if args.cmd == "scaffold":
        stats = scaffold_adrs(
            args.adrs_dir,
            force=args.force,
            predicates_path=args.predicates,
            use_heuristics=not args.no_heuristics,
        )
        print(json.dumps(stats, indent=2))
        return 0

    if args.cmd == "build":
        result = build_pack(
            args.adrs_dir,
            args.out,
            catalog_id=args.catalog_id,
            base_predicates_path=args.base_predicates,
            strict=args.strict,
        )
        print(json.dumps(result, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
