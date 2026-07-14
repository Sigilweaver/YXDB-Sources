"""
Download YXDB files from the index.

Downloads E2 files directly (paths are in index.json).
Downloads E1 files by enumerating each repo's git tree (only counts are indexed).

Usage:
    python download.py e2                  # download all E2 files
    python download.py e1                  # download all E1 files
    python download.py all                 # download everything
    python download.py e2 --repo OWNER/NAME  # single repo only
    python download.py e2 --dry-run        # show what would be downloaded

Requires the `gh` CLI to be installed and authenticated.
Downloads are saved to ./downloads/e2/ and ./downloads/e1/ (git-ignored).
"""

import argparse
import hashlib
import io
import json
import os
import sys
import time
import zipfile

from detect import detect_format
from github import download_raw, gh_api

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "downloads")
INDEX_FILE = os.path.join(os.path.dirname(__file__), "..", "index.json")


def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_filename(repo: str, path: str) -> str:
    return f"{repo.replace('/', '_')}_{os.path.basename(path)}"


def download_e2(index: dict, repo_filter: str | None, dry_run: bool) -> None:
    dest_dir = os.path.join(DOWNLOADS_DIR, "e2")
    os.makedirs(dest_dir, exist_ok=True)

    total = 0
    skipped = 0
    downloaded = 0
    failed = 0

    for repo_entry in index["repos"]:
        repo = repo_entry["repo"]
        if repo_filter and repo != repo_filter:
            continue
        e2_files = repo_entry.get("e2_files", [])
        if not e2_files:
            continue
        branch = repo_entry.get("default_branch", "main")

        for f in e2_files:
            total += 1
            path = f["path"]
            dest = os.path.join(dest_dir, safe_filename(repo, path))

            if os.path.exists(dest):
                skipped += 1
                continue

            if dry_run:
                print(f"  [dry-run] {repo}: {path}")
                continue

            # Handle yxzp paths (path contains !/)
            if "!/" in path:
                yxzp_path, inner_name = path.split("!/", 1)
                data = download_raw(repo, yxzp_path, branch)
                if not data:
                    print(f"  FAIL (yxzp download): {repo}: {path}")
                    failed += 1
                    continue
                try:
                    zf = zipfile.ZipFile(io.BytesIO(data))
                except zipfile.BadZipFile:
                    print(f"  FAIL (bad zip): {repo}: {path}")
                    failed += 1
                    continue
                if inner_name not in zf.namelist():
                    print(f"  FAIL (missing inner): {repo}: {path}")
                    failed += 1
                    continue
                data = zf.read(inner_name)
            else:
                data = download_raw(repo, path, branch)
            if not data:
                print(f"  FAIL: {repo}: {path}")
                failed += 1
                continue

            file_hash = hashlib.sha256(data).hexdigest()
            expected = f.get("sha256", "").lower()
            if expected and file_hash != expected:
                print(f"  HASH MISMATCH: {repo}: {path}")
                failed += 1
                continue

            with open(dest, "wb") as out:
                out.write(data)
            downloaded += 1
            print(f"  {repo}: {path} ({len(data):,} bytes)")
            time.sleep(0.15)

    print(f"\nE2: {total} total, {downloaded} downloaded, {skipped} skipped, {failed} failed")


def download_e1(index: dict, repo_filter: str | None, dry_run: bool) -> None:
    dest_dir = os.path.join(DOWNLOADS_DIR, "e1")
    os.makedirs(dest_dir, exist_ok=True)

    total = 0
    skipped = 0
    downloaded = 0
    failed = 0

    for repo_entry in index["repos"]:
        repo = repo_entry["repo"]
        if repo_filter and repo != repo_filter:
            continue
        e1_count = repo_entry.get("e1_file_count", 0)
        if not e1_count:
            continue
        branch = repo_entry.get("default_branch", "main")

        print(f"\n  {repo} ({e1_count} E1 files)")

        if dry_run:
            total += e1_count
            continue

        # Enumerate tree to find .yxdb paths
        tree = gh_api(f"repos/{repo}/git/trees/{branch}?recursive=1", timeout=60)
        if not tree or "tree" not in tree:
            print(f"    FAIL: could not enumerate tree")
            failed += e1_count
            continue

        yxdb_entries = [
            e for e in tree["tree"]
            if e["path"].lower().endswith(".yxdb")
        ]
        yxzp_entries = [
            e for e in tree["tree"]
            if e["path"].lower().endswith(".yxzp")
        ]

        for entry in yxdb_entries:
            path = entry["path"]
            dest = os.path.join(dest_dir, safe_filename(repo, path))

            if os.path.exists(dest):
                skipped += 1
                continue

            size = entry.get("size", 0)
            if size and size > 100_000_000:
                skipped += 1
                continue

            data = download_raw(repo, path, branch)
            if not data:
                print(f"    FAIL: {path}")
                failed += 1
                continue

            fmt = detect_format(data)
            if fmt != "E1":
                continue  # skip E2/UNKNOWN - only want E1 here

            total += 1
            with open(dest, "wb") as out:
                out.write(data)
            downloaded += 1
            time.sleep(0.15)

        # Also check inside .yxzp archives for E1 files
        for entry in yxzp_entries:
            zpath = entry["path"]
            size = entry.get("size", 0)
            if size and size > 200_000_000:
                continue

            zdata = download_raw(repo, zpath, branch)
            if not zdata:
                print(f"    FAIL (yxzp): {zpath}")
                failed += 1
                continue

            try:
                zf = zipfile.ZipFile(io.BytesIO(zdata))
            except zipfile.BadZipFile:
                print(f"    FAIL (bad zip): {zpath}")
                failed += 1
                continue

            inner = [n for n in zf.namelist() if n.lower().endswith(".yxdb")]
            for name in inner:
                inner_data = zf.read(name)
                fmt = detect_format(inner_data)
                if fmt != "E1":
                    continue

                dest = os.path.join(dest_dir, safe_filename(repo, name))
                if os.path.exists(dest):
                    skipped += 1
                    continue

                total += 1
                with open(dest, "wb") as out:
                    out.write(inner_data)
                downloaded += 1

            time.sleep(0.15)

        time.sleep(0.3)

    print(f"\nE1: {total} total, {downloaded} downloaded, {skipped} skipped, {failed} failed")


def main():
    parser = argparse.ArgumentParser(description="Download YXDB files from the index")
    parser.add_argument("format", choices=["e1", "e2", "all"], help="Which format to download")
    parser.add_argument("--repo", help="Download from a single repo only (owner/name)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    args = parser.parse_args()

    if not os.path.exists(INDEX_FILE):
        print("index.json not found. Run: uv run gen_index.py", file=sys.stderr)
        sys.exit(1)

    index = load_index()

    if args.format in ("e2", "all"):
        print("=== Downloading E2 files ===")
        download_e2(index, args.repo, args.dry_run)

    if args.format in ("e1", "all"):
        print("\n=== Downloading E1 files ===")
        download_e1(index, args.repo, args.dry_run)


if __name__ == "__main__":
    main()
