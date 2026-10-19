#!/usr/bin/env python3
"""Copy a bounded Pathfinder projection into Pages only after private-visibility checks."""

import argparse
import base64
import json
import re
from pathlib import Path


ALLOWED_ROOT_KEYS = {
    "schema_version", "generated_at", "window_days", "records_seen", "rejected_records",
    "totals", "daily", "model_metering", "operational_telemetry",
}
FORBIDDEN_KEY = re.compile(r"^(?:issue(?:_.*)?|repository|repo(?:_.*)?|run_id|job_id|trace(?:_.*)?|span(?:_.*)?|source|report|hash|person|user|engineer|finding|prompt|content|identifier|.*_id)$", re.I)


def has_forbidden_key(value):
    if isinstance(value, dict):
        return any(FORBIDDEN_KEY.search(str(key)) or has_forbidden_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(has_forbidden_key(item) for item in value)
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True, type=Path)
    parser.add_argument("--pages", required=True, type=Path)
    parser.add_argument("--contents", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        repository = json.loads(args.repository.read_text(encoding="utf-8"))
        pages = json.loads(args.pages.read_text(encoding="utf-8"))
        if repository.get("visibility") != "private" or repository.get("owner", {}).get("type") != "Organization" or pages.get("public") is not False:
            print("Private repository and private Pages visibility were not both verified; keeping empty summary.")
            return 1

        response = json.loads(args.contents.read_text(encoding="utf-8"))
        if response.get("type") != "file" or response.get("path") != "dashboard/summary.json":
            raise ValueError("GitHub returned an unexpected summary file.")
        encoded = response.get("content")
        if not isinstance(encoded, str):
            raise ValueError("GitHub summary content is missing.")
        payload = base64.b64decode(encoded, validate=False)
        if len(payload) > 262144:
            raise ValueError("GitHub summary exceeds the 256 KiB publication limit.")
        summary = json.loads(payload)
        if not isinstance(summary, dict) or summary.get("schema_version") not in {"pathfinder-usage-dashboard-v1", "pathfinder-usage-dashboard-v2"}:
            raise ValueError("GitHub summary schema is not supported.")
        expected_root_keys = ALLOWED_ROOT_KEYS if summary["schema_version"].endswith("-v2") else ALLOWED_ROOT_KEYS - {"operational_telemetry"}
        if set(summary) != expected_root_keys or has_forbidden_key(summary):
            raise ValueError("GitHub summary contains fields outside the publication allowlist.")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload if payload.endswith(b"\n") else payload + b"\n")
        print("Verified private organization repository and private Pages; embedded bounded aggregate summary.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Could not verify/embed Pathfinder summary; keeping empty summary: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
