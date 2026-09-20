"""
GitHub interaction layer.

Uses the `gh` CLI for API calls with built-in rate-limit back-off.
All downloads go through raw.githubusercontent.com.
"""

import json
import os
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

# Alteryx-owned orgs - we never source from these.
ALTERYX_ORGS = frozenset(["alteryx", "AlteryxLabs"])

USER_AGENT = "E2-Sources/1.0 (https://github.com/SigilYX/E2-Sources)"
RATE_LIMIT_PAUSE = 65  # seconds


def is_alteryx_owned(repo: str) -> bool:
    owner = repo.split("/")[0].lower()
    return owner in {o.lower() for o in ALTERYX_ORGS}


# ── gh CLI helpers ──────────────────────────────────────────


def gh_api(endpoint: str, timeout: int = 30) -> dict | list | None:
    """Call `gh api <endpoint>`, with one automatic retry on rate-limit."""
    for attempt in range(2):
        try:
            r = subprocess.run(
                ["gh", "api", endpoint],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return None

        if r.returncode == 0:
            try:
                return json.loads(r.stdout)
            except json.JSONDecodeError:
                return None

        if attempt == 0 and ("rate limit" in r.stderr.lower() or "403" in r.stderr):
            print(f"  Rate-limited - pausing {RATE_LIMIT_PAUSE}s ...")
            time.sleep(RATE_LIMIT_PAUSE)
            continue
        return None
    return None


def search_repos(query: str, per_page: int = 100, max_pages: int = 10) -> set[str]:
    """Return a set of `owner/name` strings matching a code-search query."""
    repos: set[str] = set()
    for page in range(1, max_pages + 1):
        ep = f"search/repositories?q={query}&per_page={per_page}&page={page}&sort=updated"
        data = gh_api(ep)
        if not data or "items" not in data:
            break
        items = data["items"]
        for item in items:
            repos.add(item["full_name"])
        if len(items) < per_page:
            break
        time.sleep(2)  # stay well under 30 req/min search limit
    return repos


def search_code_repos(query: str, per_page: int = 100, max_pages: int = 5) -> set[str]:
    """Return repos from a code-search query (search/code endpoint)."""
    repos: set[str] = set()
    for page in range(1, max_pages + 1):
        ep = f"search/code?q={query}&per_page={per_page}&page={page}"
        data = gh_api(ep)
        if not data or "items" not in data:
            break
        items = data["items"]
        for item in items:
            repo = item.get("repository", {})
            name = repo.get("full_name")
            if name:
                repos.add(name)
        if len(items) < per_page:
            break
        time.sleep(3)  # code search has stricter rate limits
    return repos


def get_default_branch_sha(repo: str) -> str | None:
    """Return the HEAD commit SHA of the repo's default branch, or None."""
    data = gh_api(f"repos/{repo}")
    if not data:
        return None
    branch = data.get("default_branch", "main")
    ref = gh_api(f"repos/{repo}/git/ref/heads/{branch}")
    if ref and "object" in ref:
        return ref["object"]["sha"]
    return None


def get_repo_tree(repo: str) -> list[dict] | None:
    """
    Return the recursive git tree for the latest commit.

    Each entry is ``{"path": ..., "size": ..., "sha": ...}``.
    Returns None on failure.
    """
    data = gh_api(f"repos/{repo}")
    if not data:
        return None
    branch = data.get("default_branch", "main")
    tree = gh_api(f"repos/{repo}/git/trees/{branch}?recursive=1", timeout=60)
    if tree and "tree" in tree:
        return tree["tree"]
    return None


# ── raw download ────────────────────────────────────────────


def download_raw(repo: str, path: str, branch: str = "main") -> bytes | None:
    """Download a single raw file from GitHub. Returns bytes or None."""
    encoded_path = urllib.parse.quote(path, safe="/")
    encoded_repo = urllib.parse.quote(repo, safe="/")
    encoded_branch = urllib.parse.quote(branch, safe="")
    url = f"https://raw.githubusercontent.com/{encoded_repo}/{encoded_branch}/{encoded_path}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                return None
        except (urllib.error.URLError, OSError):
            if attempt == 2:
                return None
        time.sleep(2 ** attempt)
    return None
