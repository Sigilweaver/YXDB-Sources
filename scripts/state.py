"""
Persistent state for the E2 sourcing pipeline.

State is stored in ``data/sources.json`` (git-ignored — local only) and
``data/known_repos.json`` (committed — the canonical record of what we've found).

The split:
- ``known_repos.json`` — committed.  Maps every repo we've ever checked to its
  latest-checked commit SHA, E2 file count, and per-file SHA-256 hashes.
  This is the public ledger.
- ``sources.json`` — git-ignored.  Transient download state so interrupted runs
  can resume.  Not useful to anyone else.
"""

import json
import os
from datetime import datetime, timezone

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
KNOWN_REPOS_FILE = os.path.join(STATE_DIR, "known_repos.json")
SOURCES_FILE = os.path.join(STATE_DIR, "sources.json")


def _ensure_dir():
    os.makedirs(STATE_DIR, exist_ok=True)


# ── known_repos.json (committed) ───────────────────────────


def load_known_repos() -> dict:
    """
    Load the committed repo ledger.

    Structure::

        {
            "owner/repo": {
                "last_checked_sha": "abc123...",
                "last_checked_at": "2026-03-18T00:00:00Z",
                "default_branch": "main",
                "e2_files": [
                    {
                        "path": "foo/bar.yxdb",
                        "size": 12345,
                        "sha256": "...",
                    }
                ],
                "e1_file_count": 3,
                "skipped": false
            },
            ...
        }
    """
    if os.path.exists(KNOWN_REPOS_FILE):
        with open(KNOWN_REPOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_known_repos(data: dict) -> None:
    _ensure_dir()
    with open(KNOWN_REPOS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


def mark_repo_checked(
    known: dict,
    repo: str,
    sha: str,
    branch: str,
    e2_files: list[dict],
    e1_count: int = 0,
    *,
    skipped: bool = False,
) -> None:
    """Update the ledger entry for *repo*."""
    known[repo] = {
        "last_checked_sha": sha,
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
        "default_branch": branch,
        "e2_files": e2_files,
        "e1_file_count": e1_count,
        "skipped": skipped,
    }


def repo_needs_check(known: dict, repo: str, current_sha: str | None) -> bool:
    """Return True if *repo* has never been checked or has new commits."""
    entry = known.get(repo)
    if entry is None:
        return True
    if current_sha is None:
        # Couldn't resolve HEAD — skip to be safe
        return False
    return entry.get("last_checked_sha") != current_sha


# ── sources.json (git-ignored, transient) ──────────────────


def load_sources() -> dict:
    if os.path.exists(SOURCES_FILE):
        with open(SOURCES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"downloaded_keys": [], "errors": []}


def save_sources(data: dict) -> None:
    _ensure_dir()
    with open(SOURCES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
