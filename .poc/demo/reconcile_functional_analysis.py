#!/usr/bin/env python3
"""Reconcile eligible Functional Analysis attempts into the CSV audit ledger."""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from functional_analysis_ledger import (
    MAX_ARCHIVE_BYTES,
    execution_only_record,
    persist_record,
    project_bundle,
)
from store import CsvStore

WORKFLOW_PATH = ".github/workflows/functional-analysis-demo.yml"
WORKFLOW_FILE = "functional-analysis-demo.yml"
MAX_SCAN_DAYS = 13
MAX_RUNS = 500
MAX_ATTEMPTS_PER_RUN = 20
MAX_API_CALLS = 2000
API_DEADLINE_SECONDS = 12
_REPOSITORY = re.compile(r"[A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,100}\Z")
_SHA = re.compile(r"[a-fA-F0-9]{40}\Z")


class ReconciliationError(RuntimeError):
    pass


class GitHubAPI:
    """Small bounded GitHub REST adapter; never includes credentials in errors."""

    def __init__(self, token: str, repository: str):
        if not token:
            raise ValueError("GitHub token is required")
        if not isinstance(repository, str) or not _REPOSITORY.fullmatch(repository):
            raise ValueError("repository must use the owner/name form")
        self.token = token
        self.repository = repository
        self.root = f"https://api.github.com/repos/{repository}"
        self.calls = 0

    def _request(self, url: str, *, authenticated: bool, max_bytes: int) -> bytes:
        if self.calls >= MAX_API_CALLS:
            raise ReconciliationError("GitHub API call budget exhausted")
        self.calls += 1
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        if authenticated:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, headers=headers, method="GET")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=API_DEADLINE_SECONDS) as response:
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > max_bytes:
                        raise ReconciliationError("GitHub response exceeds the allowed size")
                    data = response.read(max_bytes + 1)
                    if len(data) > max_bytes:
                        raise ReconciliationError("GitHub response exceeds the allowed size")
                    return data
            except urllib.error.HTTPError as error:
                if error.code in {429, 500, 502, 503, 504} and attempt < 2:
                    retry_after = error.headers.get("Retry-After", "")
                    try:
                        delay = min(5, max(0, int(retry_after)))
                    except ValueError:
                        delay = 2 ** attempt
                    time.sleep(delay)
                    continue
                raise ReconciliationError(f"GitHub API returned HTTP {error.code}") from None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise ReconciliationError(f"GitHub request failed ({type(error).__name__})") from None
        raise ReconciliationError("GitHub request exhausted its retry policy")

    def get_json(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
        if not path.startswith("/") or ".." in path or "\n" in path:
            raise ValueError("GitHub API path is invalid")
        url = self.root + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        raw = self._request(url, authenticated=True, max_bytes=4 * 1024 * 1024)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ReconciliationError("GitHub returned malformed JSON") from error
        if not isinstance(value, dict):
            raise ReconciliationError("GitHub returned an unexpected JSON root")
        return value

    def download_artifact(self, artifact_id: int, declared_size: int, expected_digest: str) -> bytes:
        if not isinstance(artifact_id, int) or artifact_id <= 0:
            raise ValueError("artifact ID is invalid")
        if not isinstance(declared_size, int) or declared_size < 0 or declared_size > MAX_ARCHIVE_BYTES:
            raise ReconciliationError("compressed artifact exceeds the allowed size")
        url = f"{self.root}/actions/artifacts/{artifact_id}/zip"
        request = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github+json", "Authorization": f"Bearer {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }, method="GET")

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None

        try:
            opener = urllib.request.build_opener(NoRedirect)
            with opener.open(request, timeout=API_DEADLINE_SECONDS) as response:
                content = response.read(MAX_ARCHIVE_BYTES + 1)
        except urllib.error.HTTPError as error:
            if error.code not in {301, 302, 303, 307, 308}:
                raise ReconciliationError(f"Artifact API returned HTTP {error.code}") from None
            location = error.headers.get("Location", "")
            parsed = urllib.parse.urlsplit(location)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                raise ReconciliationError("Artifact download redirect is invalid") from None
            # The redirect URL is issued by the authenticated GitHub API. Never forward
            # the GitHub token to the signed artifact-storage URL.
            content = self._request(location, authenticated=False, max_bytes=MAX_ARCHIVE_BYTES)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ReconciliationError(f"Artifact download failed ({type(error).__name__})") from None
        if len(content) > MAX_ARCHIVE_BYTES:
            raise ReconciliationError("compressed artifact exceeds the allowed size")
        if not re.fullmatch(r"sha256:[a-f0-9]{64}", str(expected_digest)):
            raise ReconciliationError("artifact digest metadata is invalid")
        if "sha256:" + __import__("hashlib").sha256(content).hexdigest() != expected_digest:
            raise ReconciliationError("downloaded artifact digest does not match Actions metadata")
        return content


def _positive_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _attempt_context(repository: str, default_branch: str, workflow_id: int,
                     run: dict[str, Any], attempt: dict[str, Any], artifact: dict[str, Any] | None) -> dict[str, Any]:
    run_id = _positive_int(attempt.get("id")) or _positive_int(run.get("id"))
    run_attempt = _positive_int(attempt.get("run_attempt")) or _positive_int(run.get("run_attempt"))
    attempt_workflow_id = _positive_int(attempt.get("workflow_id")) or _positive_int(run.get("workflow_id"))
    if not run_id or not run_attempt or attempt_workflow_id != workflow_id:
        raise ReconciliationError("Actions run identity does not match the approved workflow")
    context = {
        "repository": repository,
        "workflow_id": workflow_id,
        "workflow_sha": attempt.get("head_sha") or run.get("head_sha"),
        "run_id": run_id,
        "run_attempt": run_attempt,
        "event": attempt.get("event") or run.get("event"),
        "head_branch": attempt.get("head_branch") or run.get("head_branch"),
        "default_branch": default_branch,
        "execution_status": attempt.get("status") or run.get("status"),
        "execution_conclusion": attempt.get("conclusion") or run.get("conclusion"),
    }
    if artifact is not None:
        context.update({
            "artifact_id": artifact.get("id"),
            "artifact_name": artifact.get("name"),
            "artifact_digest": artifact.get("digest"),
        })
    return context


def _latest_rows(store: CsvStore) -> dict[tuple[str, str, int], dict[str, str]]:
    latest: dict[tuple[str, str, int], dict[str, str]] = {}
    revisions: dict[tuple[str, str, int], set[int]] = {}
    for row in store.rows("functional_analysis_runs"):
        try:
            identity = (row["repository"], row["workflow_run_id"], int(row["run_attempt"]))
            revision = int(row["record_revision"])
        except (KeyError, ValueError):
            raise ReconciliationError("existing Functional Analysis ledger row is malformed") from None
        if not row["repository"] or not row["workflow_run_id"] or revision <= 0:
            raise ReconciliationError("existing Functional Analysis ledger row is malformed")
        seen = revisions.setdefault(identity, set())
        if revision in seen:
            raise ReconciliationError("existing Functional Analysis ledger has duplicate record revisions")
        seen.add(revision)
        if identity not in latest or revision > int(latest[identity]["record_revision"]):
            latest[identity] = row
    return latest


def _row_identities(store: CsvStore) -> set[tuple[str, str, int]]:
    # Unreconciled identities are deliberately omitted so a later schedule can
    # recover an artifact that was temporarily unavailable.
    return {identity for identity, row in _latest_rows(store).items()
            if row.get("persistence_state") != "unreconciled"}


def _list_recent_runs(api: GitHubAPI, workflow_id: int, max_runs: int = MAX_RUNS) -> list[dict[str, Any]]:
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=MAX_SCAN_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")
    found: list[dict[str, Any]] = []
    per_page = 100
    for page in range(1, (max_runs // per_page) + 2):
        payload = api.get_json(f"/actions/workflows/{workflow_id}/runs", {
            "created": f">={since}", "per_page": str(per_page), "page": str(page),
        })
        runs = payload.get("workflow_runs")
        if not isinstance(runs, list):
            raise ReconciliationError("GitHub workflow run listing is malformed")
        total = payload.get("total_count")
        if isinstance(total, int) and total > max_runs:
            raise ReconciliationError(f"recent workflow history exceeds the {max_runs}-run reconciliation bound")
        found.extend(row for row in runs if isinstance(row, dict))
        if len(found) >= max_runs or len(runs) < per_page:
            return found[:max_runs]
    raise ReconciliationError("recent workflow history exceeds the reconciliation page bound")


def _list_artifacts(api: GitHubAPI, run_id: int) -> list[dict[str, Any]]:
    payload = api.get_json(f"/actions/runs/{run_id}/artifacts", {"per_page": "100", "page": "1"})
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise ReconciliationError("GitHub artifact listing is malformed")
    return [item for item in artifacts if isinstance(item, dict)]


def reconcile(api: GitHubAPI, repository: str, db_dir: str | Path,
              direct_run: tuple[int, int] | None = None) -> dict[str, int]:
    repo = api.get_json("/")
    default_branch = repo.get("default_branch")
    if repo.get("full_name") != repository or not isinstance(default_branch, str) or not default_branch:
        raise ReconciliationError("repository identity or default branch could not be verified")
    workflow = api.get_json(f"/actions/workflows/{urllib.parse.quote(WORKFLOW_FILE, safe='')}")
    workflow_id = _positive_int(workflow.get("id"))
    if workflow.get("path", "").split("@", 1)[0] != WORKFLOW_PATH or not workflow_id:
        raise ReconciliationError("Functional Analysis workflow identity could not be verified")
    store = CsvStore(db_dir)
    known = _row_identities(store)
    if direct_run is not None:
        if not all(_positive_int(part) for part in direct_run):
            raise ValueError("direct workflow run identity is invalid")
        run_ids = [(direct_run[0], direct_run[1])]
        source_runs = {}
    else:
        runs = _list_recent_runs(api, workflow_id)
        source_runs = {run["id"]: run for run in runs if _positive_int(run.get("id"))}
        run_ids = []
        for run_id, run in source_runs.items():
            if run.get("workflow_id") != workflow_id:
                continue
            latest_attempt = _positive_int(run.get("run_attempt"))
            if latest_attempt is None or latest_attempt > MAX_ATTEMPTS_PER_RUN:
                raise ReconciliationError("workflow attempt count exceeds reconciliation bound")
            for attempt_number in range(1, latest_attempt + 1):
                if (repository, str(run_id), attempt_number) not in known:
                    run_ids.append((run_id, attempt_number))
    results = {"scanned": 0, "persisted": 0, "replayed": 0, "updated": 0,
               "execution_only": 0, "skipped_untrusted": 0, "unreconciled": 0}
    for run_id, attempt_number in run_ids:
        if direct_run is None and (repository, str(run_id), attempt_number) in known:
            results["replayed"] += 1
            continue
        run = source_runs.get(run_id, {})
        attempt = api.get_json(f"/actions/runs/{run_id}/attempts/{attempt_number}")
        results["scanned"] += 1
        if (attempt.get("workflow_id") != workflow_id or
                (attempt.get("event") or run.get("event")) != "workflow_dispatch" or
                (attempt.get("head_branch") or run.get("head_branch")) != default_branch):
            results["skipped_untrusted"] += 1
            continue
        context = _attempt_context(repository, default_branch, workflow_id, run, attempt, None)
        if context["execution_status"] != "completed":
            continue
        record = None
        if context["execution_conclusion"] == "success":
            artifact_name = f"functional-analysis-demo-{run_id}-{attempt_number}"
            artifacts = _list_artifacts(api, run_id)
            matches = [item for item in artifacts if item.get("name") == artifact_name]
            if len(matches) > 1:
                raise ReconciliationError("duplicate final artifacts match one run attempt")
            if matches and matches[0].get("expired") is not True:
                artifact = matches[0]
                artifact_run = artifact.get("workflow_run")
                if not isinstance(artifact_run, dict) or artifact_run.get("id") != run_id:
                    raise ReconciliationError("artifact belongs to a different workflow run")
                context = _attempt_context(repository, default_branch, workflow_id, run, attempt, artifact)
                bundle = api.download_artifact(context["artifact_id"], artifact.get("size_in_bytes"), context["artifact_digest"])
                record = project_bundle(bundle, context)
            else:
                record = execution_only_record(context, persistence_state="unreconciled")
                results["unreconciled"] += 1
        else:
            record = execution_only_record(context)
            results["execution_only"] += 1
        outcome = persist_record(store, record)
        if outcome == "persisted":
            results["persisted"] += 1
            known.add((repository, str(run_id), attempt_number))
        elif outcome == "updated":
            results["updated"] += 1
        else:
            results["replayed"] += 1
    # Keep older unresolved rows visible even after the automatic scan horizon
    # stops returning their source runs. A green reconciliation must not hide them.
    latest = _latest_rows(store)
    results["unreconciled"] = sum(
        1 for row in latest.values() if row.get("persistence_state") == "unreconciled"
    )
    return results


def _git_environment(token: str) -> dict[str, str]:
    environment = os.environ.copy()
    credential = "AUTHORIZATION: basic " + base64.b64encode(f"x-access-token:{token}".encode()).decode()
    environment.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "http.extraheader",
                        "GIT_CONFIG_VALUE_0": credential})
    return environment


def _run_git(args: list[str], *, token: str, timeout: int = 60) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(args, check=False, capture_output=True, timeout=timeout, env=_git_environment(token))
    except subprocess.TimeoutExpired:
        raise ReconciliationError("Git operation exceeded its deadline") from None


def _checkout_branch(path: Path, repository: str, token: str) -> None:
    remote = f"https://github.com/{repository}.git"
    check = _run_git(["git", "ls-remote", "--exit-code", remote, "refs/heads/poc-database"], token=token)
    if check.returncode not in {0, 2}:
        raise ReconciliationError("could not verify the CSV ledger branch")
    if check.returncode == 0:
        result = _run_git(["git", "clone", "--quiet", "--depth", "1", "--single-branch",
                           "--branch", "poc-database", remote, str(path)], token=token)
        if result.returncode:
            raise ReconciliationError("could not clone the CSV ledger branch")
        return
    path.mkdir(parents=True, exist_ok=True)
    for args in (["git", "init", "--quiet", "--initial-branch=poc-database", str(path)],
                 ["git", "-C", str(path), "remote", "add", "origin", remote]):
        result = _run_git(args, token=token)
        if result.returncode:
            raise ReconciliationError("could not initialize the CSV ledger branch")


def _persist_branch(db_dir: Path, repository: str, token: str) -> bool:
    """Commit one snapshot; return False only for a non-fast-forward conflict."""
    csv_paths = sorted((db_dir / ".poc-db").glob("*.csv"))
    if not csv_paths:
        raise ReconciliationError("CSV ledger contains no tables")
    add = _run_git(["git", "-C", str(db_dir), "add", "--", *[str(path.relative_to(db_dir)) for path in csv_paths]], token=token)
    if add.returncode:
        raise ReconciliationError("could not stage CSV ledger changes")
    diff = _run_git(["git", "-C", str(db_dir), "diff", "--cached", "--quiet"], token=token)
    if diff.returncode == 0:
        return True
    if diff.returncode != 1:
        raise ReconciliationError("could not inspect CSV ledger changes")
    for args in (["git", "-C", str(db_dir), "config", "user.name", "github-actions[bot]"],
                 ["git", "-C", str(db_dir), "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
                 ["git", "-C", str(db_dir), "commit", "--quiet", "-m", "chore(poc-db): reconcile Functional Analysis"]):
        result = _run_git(args, token=token)
        if result.returncode:
            raise ReconciliationError("could not commit the CSV ledger snapshot")
    push = _run_git(["git", "-C", str(db_dir), "push", "origin", "HEAD:poc-database"], token=token)
    if push.returncode == 0:
        return True
    message = (push.stderr or b"").decode("utf-8", errors="replace").lower()
    if "non-fast-forward" in message or "fetch first" in message or "rejected" in message:
        return False
    raise ReconciliationError("CSV ledger push failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", default=os.environ.get("GITHUB_REPOSITORY", ""))
    parser.add_argument("--database-dir", required=True)
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH", ""))
    args = parser.parse_args()
    token = os.environ.get("GH_TOKEN", "")
    api = GitHubAPI(token, args.repository)
    direct_run = None
    if args.event_name == "workflow_run":
        try:
            payload = json.loads(Path(args.event_path).read_text(encoding="utf-8"))
            event_run = payload["workflow_run"]
            direct_run = (_positive_int(event_run.get("id")), _positive_int(event_run.get("run_attempt")))
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as error:
            raise ReconciliationError(f"workflow_run event payload is malformed ({type(error).__name__})") from error
    elif args.event_name not in {"schedule", "workflow_dispatch"}:
        raise ReconciliationError("event is not allowlisted for ledger reconciliation")

    api_repo = api.get_json("/")
    if api_repo.get("full_name") != args.repository:
        raise ReconciliationError("repository identity does not match the workflow context")
    base_dir = Path(args.database_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, int] = {}
    for retry in range(3):
        checkout = base_dir / f"ledger-attempt-{retry + 1}"
        if checkout.exists():
            shutil.rmtree(checkout)
        _checkout_branch(checkout, args.repository, token)
        summary = reconcile(api, args.repository, checkout / ".poc-db", direct_run)
        if not (summary["persisted"] or summary["updated"]):
            break
        if _persist_branch(checkout, args.repository, token):
            break
        if retry == 2:
            raise ReconciliationError("CSV ledger push conflicted after three fresh-snapshot attempts")
        time.sleep(2 ** retry)
    print("Functional Analysis ledger reconciliation: " + json.dumps(summary, sort_keys=True))
    if summary["unreconciled"]:
        print("One or more successful workflow attempts lack a recoverable final artifact; the ledger records them without a domain outcome.", file=sys.stderr)
    if summary["unreconciled"]:
        raise ReconciliationError("reconciliation is incomplete because a successful attempt has no valid final artifact")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Avoid printing raw exception bodies that may contain a URL/token.
        print(f"ERROR: {type(exc).__name__}: {str(exc)}", file=sys.stderr)
        raise SystemExit(1)
