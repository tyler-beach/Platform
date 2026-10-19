"""CLI: python3 -m tools.adr_pack <validate|scaffold|suggest|build> …"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from .claude_suggest import (
    DEFAULT_MAX_CALLS,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL_CLI,
    suggest_with_claude,
)
from .commands import build_pack, scaffold_adrs, validate_adrs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools.adr_pack",
        description=(
            "ADR pack helper: validate markdown, scaffold typed sidecars, "
            "optionally ask Claude for draft fields under a budget, then build. "
            "Default path is offline; Claude is opt-in and never auto-approves."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Lint ADR markdown + sidecar readiness")
    p_val.add_argument("adrs_dir", type=Path, help="Directory of *.md ADRs")
    p_val.add_argument("--json", action="store_true", help="Emit JSON report")

    p_sc = sub.add_parser("scaffold", help="Write draft .md.req.json sidecars (offline)")
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

    p_sg = sub.add_parser(
        "suggest",
        help="Opt-in Claude drafts for incomplete sidecars (budgeted; never approves)",
    )
    p_sg.add_argument("adrs_dir", type=Path)
    p_sg.add_argument(
        "--predicates",
        type=Path,
        default=None,
        help="predicates.json whose ids may be reused",
    )
    p_sg.add_argument(
        "--claude-bin",
        default=None,
        help="Path to Claude Code binary (default: CLAUDE_CLI or `claude` on PATH)",
    )
    p_sg.add_argument(
        "--execute",
        action="store_true",
        help="Actually invoke Claude Code CLI (default is dry-run; also requires --yes)",
    )
    p_sg.add_argument(
        "--yes",
        action="store_true",
        help="Required with --execute to confirm usage",
    )
    p_sg.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    p_sg.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    p_sg.add_argument("--max-input-tokens-total", type=int, default=50_000)
    p_sg.add_argument("--max-output-tokens-total", type=int, default=4_000)
    p_sg.add_argument(
        "--model",
        default=None,
        help=f"Claude Code model alias (default {DEFAULT_MODEL_CLI} / CLAUDE_CLI_MODEL)",
    )
    p_sg.add_argument(
        "--no-cache",
        action="store_true",
        help="Do not read/write .adr_pack_cache/claude_suggestions.json",
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

    if args.cmd == "suggest":
        dry_run = not args.execute
        if args.execute and not args.yes:
            print(
                "Refusing --execute without --yes. "
                "Run with --dry-run first, then re-run with --execute --yes.",
                file=sys.stderr,
            )
            return 2
        stats = suggest_with_claude(
            args.adrs_dir,
            predicates_path=args.predicates,
            dry_run=dry_run,
            max_calls=args.max_calls,
            max_output_tokens=args.max_output_tokens,
            max_input_tokens_total=args.max_input_tokens_total,
            max_output_tokens_total=args.max_output_tokens_total,
            model=args.model,
            claude_bin=args.claude_bin,
            use_cache=not args.no_cache,
        )
        print(json.dumps(asdict(stats), indent=2))
        if dry_run:
            print(
                "\nDry-run only (no Claude Code CLI calls). "
                f"{stats.dry_run} ADR(s) would be sent within budget. "
                "Re-run with --execute --yes.",
                file=sys.stderr,
            )
        return 1 if stats.failed and stats.called == 0 and not dry_run else 0

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
