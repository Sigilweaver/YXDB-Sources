"""
E2-Sources weekly scan.

Usage:
    python scan.py                  # full run — discover + check + download
    python scan.py --discover-only  # just find new repos, don't download
    python scan.py --check-only     # re-check known repos for new commits

Requires the `gh` CLI to be installed and authenticated.
Downloads are saved to ./downloads/ (git-ignored).
"""

import argparse
import hashlib
import io
import os
import sys
import time
import zipfile

from detect import detect_format, extract_e2_metadata
from github import (
    ALTERYX_ORGS,
    download_raw,
    get_default_branch_sha,
    get_repo_tree,
    is_alteryx_owned,
    search_repos,
    gh_api,
)
from state import (
    load_known_repos,
    load_sources,
    mark_repo_checked,
    repo_needs_check,
    save_known_repos,
    save_sources,
)

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "downloads")

# ── Search queries ──────────────────────────────────────────

SEARCH_QUERIES = [
    "yxdb+in:path",
    "yxzp+in:path",
    "yxdb+extension:yxdb",
    "alteryx",
    "alteryx+challenge",
    "alteryx+workflow",
    "alteryx+weekly+challenge",
    "alteryx+macro",
    "alteryx+project",
    "alteryx+analytics",
    "alteryx+AMP",
    "alteryx+yxdb",
    "topic:alteryx",
]


# ── Phase 1: Discover repos ────────────────────────────────


def discover_repos(known: dict) -> set[str]:
    """Search GitHub for repos that might contain .yxdb files."""
    all_repos: set[str] = set()
    for query in SEARCH_QUERIES:
        print(f"  Searching: {query}")
        found = search_repos(query)
        new = found - all_repos - set(known.keys())
        all_repos.update(found)
        if new:
            print(f"    +{len(new)} new repos")
        time.sleep(2)
    # Filter Alteryx-owned
    all_repos = {r for r in all_repos if not is_alteryx_owned(r)}
    print(f"  Total candidate repos: {len(all_repos)} ({len(all_repos - set(known.keys()))} new)")
    return all_repos


# ── Phase 2: Check repos for yxdb/yxzp ─────────────────────


def check_repo(repo: str, known: dict, sources: dict) -> dict:
    """
    Check a single repo.  Returns a summary dict.

    Skips the repo entirely if the HEAD SHA hasn't changed since last check.
    """
    # Get current HEAD SHA
    info = gh_api(f"repos/{repo}")
    if not info:
        return {"status": "api_error"}
    branch = info.get("default_branch", "main")
    ref = gh_api(f"repos/{repo}/git/ref/heads/{branch}")
    if not ref or "object" not in ref:
        return {"status": "ref_error"}
    sha = ref["object"]["sha"]

    if not repo_needs_check(known, repo, sha):
        return {"status": "unchanged", "sha": sha}

    # Enumerate tree
    tree = gh_api(f"repos/{repo}/git/trees/{sha}?recursive=1", timeout=60)
    if not tree or "tree" not in tree:
        mark_repo_checked(known, repo, sha, branch, [], skipped=True)
        return {"status": "tree_error"}

    entries = tree["tree"]
    yxdb = [e for e in entries if e["path"].lower().endswith(".yxdb")]
    yxzp = [e for e in entries if e["path"].lower().endswith(".yxzp")]

    if not yxdb and not yxzp:
        mark_repo_checked(known, repo, sha, branch, [], skipped=False)
        return {"status": "no_yxdb", "sha": sha}

    return {
        "status": "has_files",
        "sha": sha,
        "branch": branch,
        "yxdb": [(e["path"], e.get("size", 0)) for e in yxdb],
        "yxzp": [(e["path"], e.get("size", 0)) for e in yxzp],
    }


# ── Phase 3: Download & classify ───────────────────────────


def process_repo(repo: str, info: dict, known: dict, sources: dict) -> None:
    """Download .yxdb/.yxzp files from a repo, classify, and update state."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    branch = info["branch"]
    sha = info["sha"]
    downloaded = set(sources.get("downloaded_keys", []))
    e2_files = []
    e1_count = 0

    # ── Direct .yxdb files ──────────────────────────────────
    for path, size in info.get("yxdb", []):
        key = f"{repo}/{path}"
        if key in downloaded:
            continue
        if size and size > 100_000_000:
            sources.setdefault("downloaded_keys", []).append(key)
            continue

        data = download_raw(repo, path, branch)
        if not data:
            sources.setdefault("errors", []).append(f"DOWNLOAD_FAIL: {key}")
            sources.setdefault("downloaded_keys", []).append(key)
            continue

        fmt = detect_format(data)
        file_hash = hashlib.sha256(data).hexdigest()

        if fmt == "E2":
            meta = extract_e2_metadata(data)
            safe = f"{repo.replace('/', '_')}_{os.path.basename(path)}"
            dest = os.path.join(DOWNLOADS_DIR, safe)
            if not os.path.exists(dest):
                with open(dest, "wb") as f:
                    f.write(data)
            e2_files.append({
                "path": path,
                "size": len(data),
                "sha256": file_hash,
            })
            print(f"    E2: {path} ({len(data):,} bytes, {meta['field_count']} fields)")
        elif fmt == "E1":
            e1_count += 1

        sources.setdefault("downloaded_keys", []).append(key)
        time.sleep(0.15)

    # ── .yxzp archives ──────────────────────────────────────
    for path, size in info.get("yxzp", []):
        key = f"YXZP:{repo}/{path}"
        if key in downloaded:
            continue
        if size and size > 200_000_000:
            sources.setdefault("downloaded_keys", []).append(key)
            continue

        data = download_raw(repo, path, branch)
        if not data:
            sources.setdefault("downloaded_keys", []).append(key)
            continue

        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            sources.setdefault("errors", []).append(f"BAD_ZIP: {key}")
            sources.setdefault("downloaded_keys", []).append(key)
            continue

        inner = [n for n in zf.namelist() if n.lower().endswith(".yxdb")]
        for name in inner:
            inner_data = zf.read(name)
            fmt = detect_format(inner_data)
            file_hash = hashlib.sha256(inner_data).hexdigest()

            if fmt == "E2":
                meta = extract_e2_metadata(inner_data)
                safe = f"{repo.replace('/', '_')}_{os.path.basename(name)}"
                dest = os.path.join(DOWNLOADS_DIR, safe)
                if not os.path.exists(dest):
                    with open(dest, "wb") as f:
                        f.write(inner_data)
                e2_files.append({
                    "path": f"{path}!/{name}",
                    "size": len(inner_data),
                    "sha256": file_hash,
                })
                print(f"    E2 (yxzp): {path} -> {name} ({len(inner_data):,} bytes)")
            elif fmt == "E1":
                e1_count += 1

        sources.setdefault("downloaded_keys", []).append(key)
        time.sleep(0.15)

    mark_repo_checked(known, repo, sha, branch, e2_files, e1_count)


# ── Main ────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="E2-Sources weekly scan")
    parser.add_argument("--discover-only", action="store_true", help="Only discover new repos, don't download")
    parser.add_argument("--check-only", action="store_true", help="Only re-check known repos for new commits")
    args = parser.parse_args()

    known = load_known_repos()
    sources = load_sources()

    # 1. Discover
    if not args.check_only:
        print("=" * 60)
        print("PHASE 1: DISCOVER REPOS")
        print("=" * 60)
        candidates = discover_repos(known)
    else:
        candidates = set(known.keys())

    if args.discover_only:
        print(f"\nDiscovery complete. {len(candidates)} candidate repos found.")
        return

    # 2. Check & download
    print("\n" + "=" * 60)
    print("PHASE 2: CHECK REPOS & DOWNLOAD")
    print("=" * 60)

    total = len(candidates)
    unchanged = 0
    checked = 0
    new_e2 = 0

    for i, repo in enumerate(sorted(candidates), 1):
        if is_alteryx_owned(repo):
            continue

        info = check_repo(repo, known, sources)
        status = info["status"]

        if status == "unchanged":
            unchanged += 1
            continue
        elif status in ("api_error", "ref_error", "tree_error", "no_yxdb"):
            checked += 1
            if i % 50 == 0:
                print(f"  [{i}/{total}] {status}: {repo}")
            continue

        # Has files — process
        checked += 1
        e2_before = sum(len(e.get("e2_files", [])) for e in known.values())
        print(f"  [{i}/{total}] Checking: {repo} ({len(info['yxdb'])} yxdb, {len(info['yxzp'])} yxzp)")
        process_repo(repo, info, known, sources)
        e2_after = sum(len(e.get("e2_files", [])) for e in known.values())
        new_e2 += e2_after - e2_before

        # Periodic save
        if checked % 10 == 0:
            save_known_repos(known)
            save_sources(sources)

        time.sleep(0.3)

    save_known_repos(known)
    save_sources(sources)

    # Summary
    total_e2 = sum(len(e.get("e2_files", [])) for e in known.values())
    repos_with_e2 = sum(1 for e in known.values() if e.get("e2_files"))
    print("\n" + "=" * 60)
    print("SCAN COMPLETE")
    print("=" * 60)
    print(f"  Repos checked this run:  {checked}")
    print(f"  Repos unchanged (skip):  {unchanged}")
    print(f"  New E2 files found:      {new_e2}")
    print(f"  Total E2 files tracked:  {total_e2}")
    print(f"  Repos with E2 files:     {repos_with_e2}")
    print(f"  Total repos in ledger:   {len(known)}")


if __name__ == "__main__":
    main()
