"""
E2-Sources weekly scan.

Usage:
    python scan.py                  # full run - discover + check + download
    python scan.py --discover-only  # just find new repos, don't download
    python scan.py --check-only     # re-check known repos for new commits

Requires the `gh` CLI to be installed and authenticated.
Downloads are saved to ./downloads/ (git-ignored).
"""

import argparse
import hashlib
import io
import json
import os
import sys
import time
import zipfile

from detect import ARCHIVE_EXTENSIONS, MAX_INNER_FILE_SIZE, detect_format, extract_e2_metadata
from download import e2_destination
from github import (
    ALTERYX_ORGS,
    download_raw,
    get_default_branch_sha,
    get_repo_tree,
    is_alteryx_owned,
    search_repos,
    search_code_repos,
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
    # Extended queries - added 2026-04-04
    "alteryx+designer",
    "alteryx+ETL",
    "alteryx+tool",
    "alteryx+training",
    "alteryx+gallery",
    "alteryx+server",
    "alteryx+predictive",
    "alteryx+certification",
    "alteryx+data+blending",
    "alteryx+spatial",
    "alteryx+Udacity",
    "yxdb+parser",
    "yxdb+reader",
    "topic:alteryx-designer",
]

# Code-search queries - uses search/code to find files by extension or name.
# These hit repos that don't mention "alteryx" in their description.
CODE_SEARCH_QUERIES = [
    "extension:yxmd",
    "extension:yxmc",
    "extension:yxzp",
]


# ── Phase 1: Discover repos ────────────────────────────────


def discover_repos(known: dict, max_pages: int = 10) -> set[str]:
    """Search GitHub for repos that might contain .yxdb files."""
    all_repos: set[str] = set()
    for query in SEARCH_QUERIES:
        print(f"  Searching: {query}")
        found = search_repos(query, max_pages=max_pages)
        new = found - all_repos - set(known.keys())
        all_repos.update(found)
        if new:
            print(f"    +{len(new)} new repos")
        time.sleep(2)
    # Code-search queries (find repos by adjacent file extensions)
    for query in CODE_SEARCH_QUERIES:
        print(f"  Code search: {query}")
        found = search_code_repos(query, max_pages=min(max_pages, 5))
        new = found - all_repos - set(known.keys())
        all_repos.update(found)
        if new:
            print(f"    +{len(new)} new repos")
        time.sleep(2)
    # Filter Alteryx-owned
    all_repos = {r for r in all_repos if not is_alteryx_owned(r)}
    print(f"  Total candidate repos: {len(all_repos)} ({len(all_repos - set(known.keys()))} new)")
    return all_repos


# ── Phase 2: Check repos for yxdb/archives ──────────────────


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
        return {"status": "tree_error"}
    if tree.get("truncated"):
        return {"status": "tree_truncated"}

    entries = tree["tree"]
    yxdb = [e for e in entries if e["path"].lower().endswith(".yxdb")]
    archives = [e for e in entries if e["path"].lower().endswith(ARCHIVE_EXTENSIONS)]

    if not yxdb and not archives:
        mark_repo_checked(known, repo, sha, branch, [], skipped=False)
        return {"status": "no_yxdb", "sha": sha}

    return {
        "status": "has_files",
        "sha": sha,
        "branch": branch,
        "yxdb": [(e["path"], e.get("size", 0)) for e in yxdb],
        "archives": [(e["path"], e.get("size", 0)) for e in archives],
    }


# ── Phase 3: Download & classify ───────────────────────────


def process_repo(repo: str, info: dict, known: dict, sources: dict) -> None:
    """Download .yxdb files and archives (.yxzp/.zip) from a repo, classify, and update state."""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    branch = info["branch"]
    sha = info["sha"]
    e2_files = []
    e1_count = 0
    had_error = False

    # ── Direct .yxdb files ──────────────────────────────────
    for path, size in info.get("yxdb", []):
        key = f"{repo}/{path}"
        if size and size > 100_000_000:
            sources.setdefault("errors", []).append(f"DIRECT_TOO_LARGE: {key}")
            continue

        data = download_raw(repo, path, sha)
        if not data:
            sources.setdefault("errors", []).append(f"DOWNLOAD_FAIL: {key}")
            had_error = True
            continue

        fmt = detect_format(data)
        file_hash = hashlib.sha256(data).hexdigest()

        if fmt == "E2":
            meta = extract_e2_metadata(data)
            dest, verified = e2_destination(DOWNLOADS_DIR, repo, path, file_hash)
            if not verified:
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

        time.sleep(0.15)

    # ── Archives (.yxzp / .zip) ──────────────────────────────
    for path, size in info.get("archives", []):
        key = f"ARCHIVE:{repo}/{path}"
        if size and size > 200_000_000:
            sources.setdefault("errors", []).append(f"ARCHIVE_TOO_LARGE: {key}")
            continue

        data = download_raw(repo, path, sha)
        if not data:
            sources.setdefault("errors", []).append(f"DOWNLOAD_FAIL: {key}")
            had_error = True
            continue

        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            sources.setdefault("errors", []).append(f"BAD_ZIP: {key}")
            had_error = True
            continue

        inner_infos = [zi for zi in zf.infolist() if zi.filename.lower().endswith(".yxdb")]
        for zi in inner_infos:
            if zi.file_size > MAX_INNER_FILE_SIZE:
                sources.setdefault("errors", []).append(f"INNER_TOO_LARGE: {key}!/{zi.filename}")
                continue
            name = zi.filename
            try:
                inner_data = zf.read(zi)
            except (zipfile.BadZipFile, RuntimeError, OSError, EOFError):
                sources.setdefault("errors", []).append(f"INNER_READ_FAIL: {key}!/{zi.filename}")
                had_error = True
                continue
            fmt = detect_format(inner_data)
            file_hash = hashlib.sha256(inner_data).hexdigest()

            if fmt == "E2":
                meta = extract_e2_metadata(inner_data)
                indexed_path = f"{path}!/{name}"
                dest, verified = e2_destination(DOWNLOADS_DIR, repo, indexed_path, file_hash)
                if not verified:
                    with open(dest, "wb") as f:
                        f.write(inner_data)
                e2_files.append({
                    "path": indexed_path,
                    "size": len(inner_data),
                    "sha256": file_hash,
                })
                print(f"    E2 (archive): {path} -> {name} ({len(inner_data):,} bytes)")
            elif fmt == "E1":
                e1_count += 1

        time.sleep(0.15)

    if had_error:
        print(f"    Incomplete: {repo} will be retried on the next scan")
        return
    mark_repo_checked(known, repo, sha, branch, e2_files, e1_count)


# ── Main ────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="E2-Sources weekly scan")
    parser.add_argument("--discover-only", action="store_true", help="Only discover new repos, don't download")
    parser.add_argument("--check-only", action="store_true", help="Only re-check known repos for new commits")
    parser.add_argument("--search-pages", type=int, default=10, help="Maximum pages per discovery query")
    parser.add_argument("--limit", type=int, help="Maximum repositories to check this run")
    parser.add_argument("--report", help="Write a JSON run report")
    parser.add_argument("--candidates-from", help="Check candidates from a prior discovery JSON report")
    parser.add_argument("--new-only", action="store_true", help="Exclude candidates already present in the ledger")
    args = parser.parse_args()

    if args.search_pages < 1:
        parser.error("--search-pages must be at least 1")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    known = load_known_repos()
    sources = load_sources()

    # 1. Discover
    if args.candidates_from:
        with open(args.candidates_from, encoding="utf-8") as src:
            discovery = json.load(src)
        candidates = set(discovery.get("new_candidates", []))
        report_search_pages = discovery.get("search_pages", 0)
    elif not args.check_only:
        print("=" * 60)
        print("PHASE 1: DISCOVER REPOS")
        print("=" * 60)
        candidates = discover_repos(known, args.search_pages)
        report_search_pages = args.search_pages
    else:
        candidates = set(known.keys())
        report_search_pages = 0

    new_candidates = sorted(candidates - set(known))

    if args.new_only:
        candidates = set(new_candidates)

    if args.limit is not None:
        ordered = new_candidates + sorted(candidates & set(known))
        candidates = set(ordered[:args.limit])

    if args.discover_only:
        print(f"\nDiscovery complete. {len(candidates)} candidate repos found.")
        if args.report:
            with open(args.report, "w", encoding="utf-8") as out:
                json.dump({
                    "mode": "discover-only",
                    "search_pages": args.search_pages,
                    "candidate_count": len(candidates),
                    "new_candidate_count": len(new_candidates),
                    "new_candidates": new_candidates,
                }, out, indent=2)
                out.write("\n")
        return

    # 2. Check & download
    print("\n" + "=" * 60)
    print("PHASE 2: CHECK REPOS & DOWNLOAD")
    print("=" * 60)

    total = len(candidates)
    unchanged = 0
    checked = 0
    new_e2 = 0
    statuses = {}
    repositories_by_status = {}

    for i, repo in enumerate(sorted(candidates), 1):
        if is_alteryx_owned(repo):
            continue

        info = check_repo(repo, known, sources)
        status = info["status"]
        statuses[status] = statuses.get(status, 0) + 1
        repositories_by_status.setdefault(status, []).append(repo)

        if status == "unchanged":
            unchanged += 1
            continue
        elif status in ("api_error", "ref_error", "tree_error", "tree_truncated", "no_yxdb"):
            checked += 1
            if i % 50 == 0:
                print(f"  [{i}/{total}] {status}: {repo}")
            continue

        # Has files - process
        checked += 1
        e2_before = sum(len(e.get("e2_files", [])) for e in known.values())
        print(f"  [{i}/{total}] Checking: {repo} ({len(info['yxdb'])} yxdb, {len(info['archives'])} archives)")
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
    if args.report:
        with open(args.report, "w", encoding="utf-8") as out:
            json.dump({
                "mode": "candidate-report" if args.candidates_from else ("check-only" if args.check_only else "full"),
                "search_pages": report_search_pages,
                "candidate_count": total,
                "new_candidate_count": len(new_candidates),
                "statuses": statuses,
                "repositories_by_status": repositories_by_status,
                "new_e2_files": new_e2,
                "total_e2_files": total_e2,
                "total_repos": len(known),
            }, out, indent=2)
            out.write("\n")


if __name__ == "__main__":
    main()
