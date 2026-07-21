"""
Check candidate repos discovered by expanded searches for actual .yxdb/archive files.

Consolidates candidates from:
  - data/search_results.json          (code search)
  - data/search_results_adjacent.json (adjacent extension search)
  - data/discovery_results.json       (forks/issues/commits/creative)
  - data/user_expansion_results.json  (user expansion)

Filters out known repos, Alteryx-owned repos, and obvious spam.
Checks each candidate's git tree for .yxdb files and archives (.yxzp/.zip).
"""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from detect import ARCHIVE_EXTENSIONS
from github import gh_api, is_alteryx_owned
from state import load_known_repos

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

# Spam pattern: random gibberish usernames/repo names (from yxwz false positives)
SPAM_RE = re.compile(r"^[A-Za-z0-9]{6,12}/[A-Za-z0-9]{8,}$")


def looks_like_spam(repo: str) -> bool:
    """Heuristic: random-looking owner/name with no separators."""
    owner, name = repo.split("/", 1)
    # If both owner and name have no hyphens/underscores/dots and are mostly random chars
    if SPAM_RE.match(repo):
        # Check for vowel ratio - real names have more structure
        chars = (owner + name).lower()
        vowels = sum(1 for c in chars if c in "aeiou")
        if vowels / max(len(chars), 1) < 0.15:
            return True
    return False


def _load_json(path: str) -> dict | list:
    """Load JSON, handling UTF-8 BOM."""
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def load_candidates() -> set[str]:
    """Load and merge all candidate repos from discovery JSON files."""
    candidates = set()

    # 1. Code search results
    path = os.path.join(DATA_DIR, "search_results.json")
    if os.path.exists(path):
        data = _load_json(path)
        if "new_repos" in data:
            for item in data["new_repos"]:
                if isinstance(item, dict):
                    candidates.add(item["repo"])
                else:
                    candidates.add(item)
        if "all_repos" in data:
            for item in data["all_repos"]:
                if isinstance(item, dict):
                    candidates.add(item.get("repo", ""))
                else:
                    candidates.add(item)

    # 2. Adjacent extension results
    path = os.path.join(DATA_DIR, "search_results_adjacent.json")
    if os.path.exists(path):
        data = _load_json(path)
        if "new_repos" in data:
            candidates.update(data["new_repos"])
        elif isinstance(data, list):
            candidates.update(data)

    # 3. Discovery results (forks/issues/commits/creative)
    path = os.path.join(DATA_DIR, "discovery_results.json")
    if os.path.exists(path):
        data = _load_json(path)
        for key in ["strategy_2_code_search", "strategy_3_issues",
                     "strategy_4_commits", "strategy_5_creative"]:
            if key in data:
                candidates.update(data[key])

    # 4. User expansion results
    path = os.path.join(DATA_DIR, "user_expansion_results.json")
    if os.path.exists(path):
        data = _load_json(path)
        if "by_user" in data:
            for repos in data["by_user"].values():
                candidates.update(repos)

    return candidates


def check_repo_for_yxdb(repo: str) -> dict | None:
    """Check if a repo actually contains .yxdb files or archives (.yxzp/.zip)."""
    info = gh_api(f"repos/{repo}")
    if not info:
        return None
    branch = info.get("default_branch", "main")

    ref = gh_api(f"repos/{repo}/git/ref/heads/{branch}")
    if not ref or "object" not in ref:
        return None
    sha = ref["object"]["sha"]

    tree = gh_api(f"repos/{repo}/git/trees/{sha}?recursive=1", timeout=60)
    if not tree or "tree" not in tree:
        return None

    entries = tree["tree"]
    yxdb = [e for e in entries if e["path"].lower().endswith(".yxdb")]
    archives = [e for e in entries if e["path"].lower().endswith(ARCHIVE_EXTENSIONS)]

    if not yxdb and not archives:
        return None

    return {
        "repo": repo,
        "branch": branch,
        "sha": sha,
        "yxdb_count": len(yxdb),
        "archive_count": len(archives),
        "yxdb_files": [e["path"] for e in yxdb[:20]],  # cap for display
        "archive_files": [e["path"] for e in archives[:10]],
    }


def main():
    known = load_known_repos()
    known_set = set(known.keys())

    print("Loading candidates from discovery results...")
    candidates = load_candidates()
    print(f"  Raw candidates: {len(candidates)}")

    # Filter
    candidates -= known_set
    candidates = {r for r in candidates if "/" in r}
    candidates = {r for r in candidates if not is_alteryx_owned(r)}

    spam = {r for r in candidates if looks_like_spam(r)}
    if spam:
        print(f"  Filtered {len(spam)} spam-looking repos")
        candidates -= spam

    print(f"  Candidates to check: {len(candidates)}")
    print()

    # Check each
    hits = []
    misses = 0
    errors = 0
    for i, repo in enumerate(sorted(candidates), 1):
        print(f"  [{i}/{len(candidates)}] {repo} ... ", end="", flush=True)
        try:
            result = check_repo_for_yxdb(repo)
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1
            time.sleep(1)
            continue

        if result:
            print(f"HIT! {result['yxdb_count']} yxdb, {result['archive_count']} archives")
            hits.append(result)
        else:
            print("no yxdb")
            misses += 1
        time.sleep(0.5)

    # Report
    print()
    print("=" * 60)
    print(f"RESULTS: {len(hits)} repos with .yxdb files found")
    print(f"  Checked: {len(candidates)} | Hits: {len(hits)} | Misses: {misses} | Errors: {errors}")
    print("=" * 60)

    for h in sorted(hits, key=lambda x: x["yxdb_count"], reverse=True):
        print(f"\n  {h['repo']} - {h['yxdb_count']} yxdb, {h['archive_count']} archives")
        for f in h["yxdb_files"][:5]:
            print(f"    {f}")
        if h["yxdb_count"] > 5:
            print(f"    ... and {h['yxdb_count'] - 5} more")

    # Save results
    out_path = os.path.join(DATA_DIR, "new_discoveries.json")
    with open(out_path, "w") as f:
        json.dump({"hits": hits, "checked": len(candidates), "misses": misses, "errors": errors}, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
