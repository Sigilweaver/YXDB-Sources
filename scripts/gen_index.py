"""
Generate index.json from data/known_repos.json.

Produces a machine-readable index of all repositories containing YXDB files
(both E1 and E2).  Only repos with at least one YXDB file are included.

Usage:
    python gen_index.py
"""

import json
import os
from datetime import datetime, timezone

from state import load_known_repos


def main():
    known = load_known_repos()
    repos = []

    for name, info in sorted(known.items(), key=lambda x: x[0].lower()):
        e1_count = info.get("e1_file_count", 0)
        e2_files = info.get("e2_files", [])
        if not e1_count and not e2_files:
            continue

        entry = {
            "repo": name,
            "url": f"https://github.com/{name}",
            "default_branch": info.get("default_branch", "main"),
            "last_checked_sha": info.get("last_checked_sha", ""),
            "last_checked_at": info.get("last_checked_at", ""),
            "e1_file_count": e1_count,
            "e2_file_count": len(e2_files),
        }
        if e2_files:
            entry["e2_files"] = [
                {
                    "path": f["path"],
                    "size": f["size"],
                    "sha256": f["sha256"],
                }
                for f in e2_files
            ]
        repos.append(entry)

    total_e1 = sum(r["e1_file_count"] for r in repos)
    total_e2 = sum(r["e2_file_count"] for r in repos)

    index = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "repos_scanned": len(known),
        "repos_with_yxdb": len(repos),
        "total_e1_files": total_e1,
        "total_e2_files": total_e2,
        "repos": repos,
    }

    out = os.path.join(os.path.dirname(__file__), "..", "index.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2)

    print(f"index.json: {len(repos)} repos, {total_e1} E1 files, {total_e2} E2 files")


if __name__ == "__main__":
    main()
