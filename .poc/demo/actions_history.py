"""Bounded, read-only GitHub Actions history collector for internal Pages builds."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Callable

OWNER = "tyler-beach"
REPOSITORY = "Platform"
API_ROOT = f"https://api.github.com/repos/{OWNER}/{REPOSITORY}"
WORKFLOWS = (
    ("poc-analysis.yml", "ADR Deviation PoC Analysis"),
    ("poc-evaluation.yml", "ADR Deviation Labeled Evaluation"),
    ("functional-analysis-demo.yml", "Functional Analysis Demo"),
)
MAX_RUNS_PER_WORKFLOW = 10
_RUN_STATES = {"queued", "in_progress", "completed", "waiting", "requested", "pending"}
_CONCLUSIONS = {"success", "failure", "neutral", "cancelled", "skipped", "timed_out", "action_required"}
_STEP_STATES = {"queued", "in_progress", "completed"}


def _date(value: Any) -> str:
    return value[:40] if isinstance(value, str) else ""


def _job_rows(raw_jobs: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_jobs, list):
        return []
    jobs = []
    for job in raw_jobs[:100]:
        if not isinstance(job, dict) or not isinstance(job.get("id"), int) or job["id"] <= 0:
            continue
        if job.get("status") not in _RUN_STATES or not isinstance(job.get("name"), str):
            continue
        steps = []
        for step in (job.get("steps") if isinstance(job.get("steps"), list) else [])[:100]:
            if not isinstance(step, dict) or not isinstance(step.get("number"), int) or step["number"] <= 0:
                continue
            if not isinstance(step.get("name"), str) or step.get("status") not in _STEP_STATES:
                continue
            steps.append({
                "number": step["number"], "name": step["name"][:120], "status": step["status"],
                "conclusion": step.get("conclusion") if step.get("conclusion") in _CONCLUSIONS else "",
                "started_at": _date(step.get("started_at")), "completed_at": _date(step.get("completed_at")),
            })
        jobs.append({
            "id": job["id"], "name": job["name"][:120], "status": job["status"],
            "conclusion": job.get("conclusion") if job.get("conclusion") in _CONCLUSIONS else "",
            "steps": sorted(steps, key=lambda item: item["number"]),
        })
    return jobs


def _repository_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}", value):
        raise ValueError("repository must use the owner/name form")
    return value


def collect_history(fetch_json: Callable[[str], dict[str, Any]], limit: int = MAX_RUNS_PER_WORKFLOW,
                    repository: str = f"{OWNER}/{REPOSITORY}") -> dict[str, Any]:
    if not isinstance(limit, int) or limit < 1 or limit > MAX_RUNS_PER_WORKFLOW:
        raise ValueError("history limit must be between 1 and 10 per workflow")
    repository = _repository_name(repository)
    all_runs = []
    for workflow_file, workflow_name in WORKFLOWS:
        path = f"/actions/workflows/{workflow_file}/runs?per_page={limit}"
        payload = fetch_json(path)
        if not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
            raise ValueError("GitHub returned malformed workflow history")
        for raw in payload["workflow_runs"][:limit]:
            if not isinstance(raw, dict) or not isinstance(raw.get("id"), int) or raw["id"] <= 0:
                continue
            attempt = raw.get("run_attempt") if isinstance(raw.get("run_attempt"), int) and raw["run_attempt"] > 0 else 1
            if raw.get("status") not in _RUN_STATES:
                continue
            expected_url = f"https://github.com/{repository}/actions/runs/{raw['id']}"
            api_url = raw.get("html_url")
            # Construct a trusted run URL from the validated numeric ID; ignore API URL variants.
            if not isinstance(api_url, str) or api_url != expected_url:
                continue
            jobs_path = f"/actions/runs/{raw['id']}/attempts/{attempt}/jobs?per_page=100"
            jobs_payload = fetch_json(jobs_path)
            if not isinstance(jobs_payload, dict) or not isinstance(jobs_payload.get("jobs"), list):
                jobs_payload = {"jobs": []}
            all_runs.append({
                "id": raw["id"], "run_number": raw.get("run_number") if isinstance(raw.get("run_number"), int) else raw["id"],
                "run_attempt": attempt, "name": str(raw.get("name") or workflow_name)[:120],
                "workflow_file": workflow_file, "workflow_name": workflow_name,
                "event": str(raw.get("event") or "")[:48], "status": raw["status"],
                "conclusion": raw.get("conclusion") if raw.get("conclusion") in _CONCLUSIONS else "",
                "head_branch": str(raw.get("head_branch") or "")[:80],
                "head_sha": raw.get("head_sha") if isinstance(raw.get("head_sha"), str) and re.fullmatch(r"[a-fA-F0-9]{7,40}", raw["head_sha"]) else "",
                "created_at": _date(raw.get("created_at")), "updated_at": _date(raw.get("updated_at")),
                "html_url": expected_url, "jobs": _job_rows(jobs_payload["jobs"]),
            })
    all_runs.sort(key=lambda item: item.get("updated_at") or item.get("created_at", ""), reverse=True)
    return {"schema_version": "adr-demo-actions-v1", "available": True, "repository": repository,
            "runs": all_runs[:limit * len(WORKFLOWS)]}


def github_fetcher(token: str, repository: str) -> Callable[[str], dict[str, Any]]:
    if not token:
        raise ValueError("GitHub token was not provided to the internal build collector")

    repository = _repository_name(repository)

    def fetch(path: str) -> dict[str, Any]:
        if not path.startswith("/actions/") or ".." in path or "\n" in path:
            raise ValueError("Actions API path is outside the allowlist")
        request = urllib.request.Request(
            f"https://api.github.com/repos/{repository}" + path,
            headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}",
                     "X-GitHub-Api-Version": "2022-11-28"},
            method="GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                return json.loads(response.read(4 * 1024 * 1024))
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"GitHub Actions API returned HTTP {error.code}; internal history was not updated") from None
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RuntimeError(f"GitHub Actions API request failed ({type(error).__name__}); internal history was not updated") from None

    return fetch


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=MAX_RUNS_PER_WORKFLOW)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", f"{OWNER}/{REPOSITORY}"))
    args = parser.parse_args()
    data = collect_history(github_fetcher(os.environ.get("GH_TOKEN", ""), args.repository), args.limit, args.repository)
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    print(f"Collected {len(data['runs'])} workflow history records and job steps.")


if __name__ == "__main__":
    main()
