"""
Regenerate README.md's index table plus E1-Sources.md and E2-Sources.md
from the committed data (known_repos.json, swh_submissions.json).

Usage:
    python gen_docs.py

Run this after scan.py (and, if applicable, archive.py) whenever the
counts or per-repo listings need to be refreshed.
"""

import json
import os
import re

SCRIPT_DIR = os.path.dirname(__file__)
ROOT = os.path.join(SCRIPT_DIR, "..")


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    known = load("data/known_repos.json")
    swh = load("data/swh_submissions.json")

    e1_repos = {k: v for k, v in known.items() if v.get("e1_file_count", 0) > 0}
    e2_repos = {k: v for k, v in known.items() if v.get("e2_files")}
    both = set(e1_repos) & set(e2_repos)
    union = set(e1_repos) | set(e2_repos)
    total_e1 = sum(v.get("e1_file_count", 0) for v in known.values())
    total_e2 = sum(len(v.get("e2_files", [])) for v in known.values())

    # ── E1-Sources.md ────────────────────────────────────────
    lines = [
        "# E1 Sources",
        "",
        f"{total_e1:,} E1 files across {len(e1_repos)} GitHub repositories. "
        "E1 is the original YXDB format, produced by the classic Alteryx engine.",
        "",
        "E1 files are common enough that individual file-level tracking and "
        "Software Heritage archival are not performed. This listing records "
        "per-repository file counts only.",
        "",
        "## Sources",
        "",
        "| # | Repository | E1 Files |",
        "|---|-----------|----------|",
    ]
    for i, repo in enumerate(sorted(e1_repos, key=str.lower), 1):
        count = e1_repos[repo]["e1_file_count"]
        lines.append(f"| {i} | [{repo}](https://github.com/{repo}) | {count} |")
    with open(os.path.join(ROOT, "E1-Sources.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"E1-Sources.md: {len(e1_repos)} repos, {total_e1} files")

    # ── E2-Sources.md ────────────────────────────────────────
    lines = [
        "# E2 Sources",
        "",
        f"{total_e2} E2 files across {len(e2_repos)} GitHub repositories. E2 is "
        "the AMP-engine variant of YXDB, produced by Alteryx's newer "
        "multi-threaded processing engine.",
        "",
        "All source repositories have been submitted to the "
        "[Software Heritage Foundation](https://www.softwareheritage.org/) "
        "for permanent archival.",
        "",
        "## Sources",
        "",
        "| # | Repository | E2 Files | Software Heritage |",
        "|---|-----------|----------|-------------------|",
    ]
    for i, repo in enumerate(sorted(e2_repos, key=str.lower), 1):
        count = len(e2_repos[repo]["e2_files"])
        if repo in swh:
            status = (
                f"[Archived](https://archive.softwareheritage.org/browse/origin/"
                f"directory/?origin_url=https://github.com/{repo})"
            )
        else:
            status = "Pending"
        lines.append(f"| {i} | [{repo}](https://github.com/{repo}) | {count} | {status} |")
    lines += [
        "",
        "## How E2 Was Discovered",
        "",
        r"We searched GitHub for \.yxdb\ files and found that most were produced "
        "by the classic Alteryx engine (E1), but a small number were produced by "
        "the newer AMP engine (E2). The two formats are distinct and not "
        "interchangeable.",
    ]
    with open(os.path.join(ROOT, "E2-Sources.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"E2-Sources.md: {len(e2_repos)} repos, {total_e2} files, "
          f"{sum(1 for r in e2_repos if r in swh)} archived")

    # ── README.md index table ────────────────────────────────
    readme_path = os.path.join(ROOT, "README.md")
    with open(readme_path, encoding="utf-8") as f:
        readme = f.read()

    new_table = (
        "| | Repositories | Files |\n"
        "|---|---:|---:|\n"
        f"| **E1** | {len(e1_repos)} | {total_e1:,} |\n"
        f"| **E2** | {len(e2_repos)} | {total_e2:,} |\n"
        f"| **Total unique repos** | {len(union)} | {total_e1 + total_e2:,} |\n"
        "\n"
        f"*{len(known):,} GitHub repositories scanned. {len(both)} repos contain "
        "both E1 and E2 files.*"
    )

    readme = re.sub(
        r"\| \| Repositories \| Files \|\n\|---\|---:\|---:\|\n\|.*?\n\|.*?\n\|.*?\n\n\*.*?repos contain both E1 and E2 files\.\*",
        new_table,
        readme,
        flags=re.DOTALL,
    )
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme)
    print("README.md index table updated")


if __name__ == "__main__":
    main()
