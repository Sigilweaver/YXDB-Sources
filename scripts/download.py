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
import shutil
import sys
import time
import zipfile

from detect import ARCHIVE_EXTENSIONS, MAX_INNER_FILE_SIZE, detect_format
from github import download_raw, gh_api

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "downloads")
INDEX_FILE = os.path.join(os.path.dirname(__file__), "..", "index.json")


def load_index():
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_filename(repo: str, path: str) -> str:
    return f"{repo.replace('/', '_')}_{os.path.basename(path)}"


def collision_filename(repo: str, path: str, expected: str = "") -> str:
    """Return a stable fallback name when flattened source paths collide."""
    basename = os.path.basename(path)
    stem, ext = os.path.splitext(basename)
    source_id = hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
    content_id = expected[:12] if expected else "unknown"
    return f"{repo.replace('/', '_')}_{stem}__{source_id}_{content_id}{ext}"


def file_sha256(path: str) -> str | None:
    """Hash a local file, returning None when it cannot be read."""
    digest = hashlib.sha256()
    try:
        with open(path, "rb") as src:
            for chunk in iter(lambda: src.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError:
        return None
    return digest.hexdigest()


def e2_destination(dest_dir: str, repo: str, path: str, expected: str) -> tuple[str, bool]:
    """Choose a destination without treating a basename collision as a hit.

    The original layout is retained when its content matches the indexed hash.
    A source-path fingerprint is added only when that legacy name is occupied by
    different content.
    """
    legacy = os.path.join(dest_dir, safe_filename(repo, path))
    if not os.path.exists(legacy) or file_sha256(legacy) == expected:
        return legacy, os.path.exists(legacy)

    fallback = os.path.join(dest_dir, collision_filename(repo, path, expected))
    return fallback, os.path.exists(fallback) and file_sha256(fallback) == expected


def local_payloads(root: str) -> dict[str, str]:
    """Index local YXDB payloads by hash so earlier downloads can be reused."""
    payloads = {}
    if not os.path.isdir(root):
        return payloads
    for directory, _, filenames in os.walk(root):
        for filename in filenames:
            if not filename.lower().endswith(".yxdb"):
                continue
            path = os.path.join(directory, filename)
            digest = file_sha256(path)
            if digest:
                payloads.setdefault(digest, path)
    return payloads


def download_e2(index: dict, repo_filter: str | None, dry_run: bool) -> dict:
    dest_dir = os.path.join(DOWNLOADS_DIR, "e2")
    os.makedirs(dest_dir, exist_ok=True)

    total = 0
    skipped = 0
    downloaded = 0
    reused = 0
    failed = 0
    failures = []
    payloads = local_payloads(DOWNLOADS_DIR)

    for repo_entry in index["repos"]:
        repo = repo_entry["repo"]
        if repo_filter and repo != repo_filter:
            continue
        e2_files = repo_entry.get("e2_files", [])
        if not e2_files:
            continue
        # Use the immutable commit recorded by the index. A branch may move
        # between indexing and retrieval, yielding content with another hash.
        ref = repo_entry.get("last_checked_sha") or repo_entry.get("default_branch", "main")

        for f in e2_files:
            total += 1
            path = f["path"]
            expected = f.get("sha256", "").lower()
            dest, verified = e2_destination(dest_dir, repo, path, expected)

            if verified:
                skipped += 1
                continue

            cached = payloads.get(expected)
            if cached:
                if dry_run:
                    print(f"  [dry-run, local reuse] {repo}: {path}")
                else:
                    shutil.copyfile(cached, dest)
                    print(f"  [local reuse] {repo}: {path}")
                reused += 1
                continue

            if dry_run:
                print(f"  [dry-run] {repo}: {path}")
                continue

            # Handle archive-embedded paths (path contains !/, from .yxzp or .zip)
            if "!/" in path:
                archive_path, inner_name = path.split("!/", 1)
                data = download_raw(repo, archive_path, ref)
                if not data:
                    print(f"  FAIL (archive download): {repo}: {path}")
                    failed += 1
                    failures.append({"repo": repo, "path": path, "reason": "archive_download"})
                    continue
                try:
                    zf = zipfile.ZipFile(io.BytesIO(data))
                except zipfile.BadZipFile:
                    print(f"  FAIL (bad zip): {repo}: {path}")
                    failed += 1
                    failures.append({"repo": repo, "path": path, "reason": "bad_zip"})
                    continue
                if inner_name not in zf.namelist():
                    print(f"  FAIL (missing inner): {repo}: {path}")
                    failed += 1
                    failures.append({"repo": repo, "path": path, "reason": "missing_inner"})
                    continue
                try:
                    data = zf.read(inner_name)
                except (zipfile.BadZipFile, RuntimeError, OSError, EOFError):
                    print(f"  FAIL (unreadable inner): {repo}: {path}")
                    failed += 1
                    failures.append({"repo": repo, "path": path, "reason": "unreadable_inner"})
                    continue
            else:
                data = download_raw(repo, path, ref)
            if not data:
                print(f"  FAIL: {repo}: {path}")
                failed += 1
                failures.append({"repo": repo, "path": path, "reason": "download"})
                continue

            file_hash = hashlib.sha256(data).hexdigest()
            if expected and file_hash != expected:
                print(f"  HASH MISMATCH: {repo}: {path}")
                failed += 1
                failures.append({
                    "repo": repo,
                    "path": path,
                    "reason": "hash_mismatch",
                    "expected_sha256": expected,
                    "actual_sha256": file_hash,
                })
                continue

            with open(dest, "wb") as out:
                out.write(data)
            payloads.setdefault(file_hash, dest)
            downloaded += 1
            print(f"  {repo}: {path} ({len(data):,} bytes)")
            time.sleep(0.15)

    print(
        f"\nE2: {total} total, {downloaded} downloaded, {reused} locally reused, "
        f"{skipped} verified existing, {failed} failed"
    )
    return {
        "format": "e2",
        "source_entries": total,
        "downloaded": downloaded,
        "locally_reused": reused,
        "verified_existing": skipped,
        "failed": failed,
        "failures": failures,
    }


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
        archive_entries = [
            e for e in tree["tree"]
            if e["path"].lower().endswith(ARCHIVE_EXTENSIONS)
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

        # Also check inside archives (.yxzp/.zip) for E1 files
        for entry in archive_entries:
            zpath = entry["path"]
            size = entry.get("size", 0)
            if size and size > 200_000_000:
                continue

            zdata = download_raw(repo, zpath, branch)
            if not zdata:
                print(f"    FAIL (archive): {zpath}")
                failed += 1
                continue

            try:
                zf = zipfile.ZipFile(io.BytesIO(zdata))
            except zipfile.BadZipFile:
                print(f"    FAIL (bad zip): {zpath}")
                failed += 1
                continue

            inner_infos = [zi for zi in zf.infolist() if zi.filename.lower().endswith(".yxdb")]
            for zi in inner_infos:
                if zi.file_size > MAX_INNER_FILE_SIZE:
                    print(f"    SKIP (inner too large): {zpath}!/{zi.filename}")
                    continue
                name = zi.filename
                inner_data = zf.read(zi)
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Download YXDB files from the index")
    parser.add_argument("format", choices=["e1", "e2", "all"], help="Which format to download")
    parser.add_argument("--repo", help="Download from a single repo only (owner/name)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded")
    parser.add_argument("--report", help="Write a JSON retrieval report")
    args = parser.parse_args()

    if not os.path.exists(INDEX_FILE):
        print("index.json not found. Run: uv run gen_index.py", file=sys.stderr)
        sys.exit(1)

    index = load_index()

    reports = []
    if args.format in ("e2", "all"):
        print("=== Downloading E2 files ===")
        reports.append(download_e2(index, args.repo, args.dry_run))

    if args.format in ("e1", "all"):
        print("\n=== Downloading E1 files ===")
        download_e1(index, args.repo, args.dry_run)

    if args.report:
        report_dir = os.path.dirname(os.path.abspath(args.report))
        os.makedirs(report_dir, exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as out:
            json.dump({"reports": reports}, out, indent=2)
            out.write("\n")
    return 1 if any(report.get("failed", 0) for report in reports) else 0


if __name__ == "__main__":
    sys.exit(main())
