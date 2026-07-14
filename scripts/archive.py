"""
Submit repos containing E2 .yxdb files to Software Heritage for archival.

Usage:
    python archive.py                  # submit all unarchived repos
    python archive.py --dry-run        # show what would be submitted
    python archive.py --status         # check status of previous submissions

Reads from state/known_repos.json.  Tracks submission state in
state/swh_submissions.json so interrupted runs can resume.

Rate limits (Software Heritage API):
    Anonymous:      120 requests/hour
    Authenticated: 1200 requests/hour

Set SWH_API_TOKEN env var to use authenticated requests.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from state import load_known_repos

# Load .env if present (simple KEY=VALUE parser, no extra dependencies)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

SWH_API_BASE = "https://archive.softwareheritage.org/api/1"
USER_AGENT = "E2-Sources/1.0 (https://github.com/SigilYX/E2-Sources)"

SUBMISSIONS_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "swh_submissions.json")


def load_submissions() -> dict:
    if os.path.exists(SUBMISSIONS_FILE):
        with open(SUBMISSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_submissions(data: dict) -> None:
    os.makedirs(os.path.dirname(SUBMISSIONS_FILE), exist_ok=True)
    with open(SUBMISSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def swh_request(method: str, endpoint: str, timeout: int = 30) -> tuple[dict | None, dict]:
    """Make a request to the SWH API. Returns (json_body, headers_dict)."""
    url = f"{SWH_API_BASE}/{endpoint}"
    req = urllib.request.Request(url, method=method)
    req.add_header("User-Agent", USER_AGENT)
    req.add_header("Accept", "application/json")

    token = os.environ.get("SWH_API_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        headers = {k.lower(): v for k, v in resp.getheaders()}
        body = json.loads(resp.read().decode("utf-8"))
        return body, headers
    except urllib.error.HTTPError as e:
        headers = {k.lower(): v for k, v in e.headers.items()}
        try:
            body = json.loads(e.read().decode("utf-8"))
        except Exception:
            body = None
        return body, headers
    except (urllib.error.URLError, OSError):
        return None, {}


def get_rate_limit_wait(headers: dict) -> float:
    """Return seconds to wait based on rate-limit headers. 0 if no wait needed."""
    remaining = headers.get("x-ratelimit-remaining")
    reset_at = headers.get("x-ratelimit-reset")

    if remaining is not None and int(remaining) <= 1 and reset_at is not None:
        wait = max(0, int(reset_at) - time.time()) + 2  # +2s buffer
        return wait
    return 0


def submit_repo(repo: str) -> tuple[str, dict | None]:
    """
    Submit a single repo to Software Heritage for archival.

    Returns (status, response_body).
    status is one of: 'accepted', 'pending', 'rejected', 'error', 'rate_limited'
    """
    origin_url = f"https://github.com/{repo}"
    encoded = urllib.parse.quote(origin_url, safe="")
    endpoint = f"origin/save/git/url/{encoded}/"

    body, headers = swh_request("POST", endpoint)

    # Handle rate limiting
    wait = get_rate_limit_wait(headers)
    if wait > 0:
        return "rate_limited", {"wait_seconds": wait}

    if body is None:
        return "error", None

    status = body.get("save_request_status", "unknown")
    return status, body


def check_status(repo: str, request_id: int) -> dict | None:
    """Check the status of a previously submitted save request."""
    body, _ = swh_request("GET", f"origin/save/{request_id}/")
    return body


def get_repos_to_archive(known: dict) -> list[str]:
    """Return sorted list of repos that have E2 files."""
    return sorted(r for r, v in known.items() if v.get("e2_files"))


def main():
    parser = argparse.ArgumentParser(description="Submit E2 repos to Software Heritage")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be submitted without submitting")
    parser.add_argument("--status", action="store_true", help="Check status of previous submissions")
    parser.add_argument("--force", action="store_true", help="Re-submit even if already submitted")
    args = parser.parse_args()

    known = load_known_repos()
    submissions = load_submissions()
    repos = get_repos_to_archive(known)

    if not repos:
        print("No repos with E2 files found.")
        return

    print(f"Repos with E2 files: {len(repos)}")

    # ── Status check mode ───────────────────────────────────
    if args.status:
        for repo in repos:
            sub = submissions.get(repo)
            if not sub:
                print(f"  {repo}: not submitted")
                continue
            req_id = sub.get("request_id")
            if req_id:
                body = check_status(repo, req_id)
                if body:
                    task = body.get("save_task_status", "?")
                    req = body.get("save_request_status", "?")
                    print(f"  {repo}: request={req} task={task}")
                    submissions[repo]["save_task_status"] = task
                    submissions[repo]["last_polled_at"] = datetime.now(timezone.utc).isoformat()
                else:
                    print(f"  {repo}: request_id={req_id} (API error)")
                time.sleep(1)
            else:
                print(f"  {repo}: {sub.get('save_request_status', '?')}")
        save_submissions(submissions)
        return

    # ── Submission mode ─────────────────────────────────────
    to_submit = []
    for repo in repos:
        if not args.force and repo in submissions:
            continue
        to_submit.append(repo)

    if not to_submit:
        print("All repos already submitted. Use --force to re-submit, or --status to check.")
        return

    print(f"Repos to submit: {len(to_submit)}")

    if args.dry_run:
        for repo in to_submit:
            n = len(known[repo]["e2_files"])
            print(f"  [DRY RUN] would submit: {repo} ({n} E2 files)")
        return

    # Check rate limit info up front
    token = os.environ.get("SWH_API_TOKEN")
    limit_type = "authenticated (1200/hr)" if token else "anonymous (120/hr)"
    print(f"Rate limit mode: {limit_type}")
    print()

    submitted = 0
    errors = 0

    for i, repo in enumerate(to_submit, 1):
        n = len(known[repo]["e2_files"])
        print(f"  [{i}/{len(to_submit)}] {repo} ({n} E2 files) ... ", end="", flush=True)

        status, body = submit_repo(repo)

        if status == "rate_limited":
            wait = body["wait_seconds"] if body else 65
            print(f"RATE LIMITED - waiting {wait:.0f}s")
            time.sleep(wait)
            # Retry once
            status, body = submit_repo(repo)

        if status in ("accepted", "pending"):
            print(f"{status}")
            submissions[repo] = {
                "save_request_status": status,
                "request_id": body.get("id") if body else None,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "save_task_status": body.get("save_task_status") if body else None,
            }
            submitted += 1
        elif status == "rate_limited":
            wait = body["wait_seconds"] if body else 65
            print(f"RATE LIMITED again - pausing {wait:.0f}s and stopping.")
            save_submissions(submissions)
            print(f"\nStopped early. Submitted {submitted} repos. Re-run to continue.")
            return
        else:
            note = ""
            if body and isinstance(body, dict):
                note = body.get("reason", body.get("note", ""))
            print(f"{status} {note}")
            submissions[repo] = {
                "save_request_status": status,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "error": note or str(body),
            }
            errors += 1

        # Save progress periodically
        if i % 5 == 0:
            save_submissions(submissions)

        # Pace requests: anonymous = 120/hr (30s), authenticated = 1200/hr (3s)
        pace = 3 if os.environ.get("SWH_API_TOKEN") else 32
        time.sleep(pace)

    save_submissions(submissions)

    print()
    print("=" * 60)
    print("ARCHIVAL SUBMISSION COMPLETE")
    print("=" * 60)
    print(f"  Submitted: {submitted}")
    print(f"  Errors:    {errors}")
    print(f"  Run with --status to check progress.")


if __name__ == "__main__":
    main()
