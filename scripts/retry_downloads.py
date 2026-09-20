"""
Retry downloading E2 files that are tracked in known_repos.json but missing from downloads/.

One-shot script - run after scan.py to fill gaps from earlier runs.
"""

import hashlib
import io
import os
import time
import zipfile

from detect import detect_format, extract_e2_metadata
from download import e2_destination
from github import download_raw
from state import load_known_repos

DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), "..", "downloads")


def main():
    known = load_known_repos()
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)

    e2_repos = {r: v for r, v in known.items() if v.get("e2_files")}
    missing = []
    for repo, info in sorted(e2_repos.items()):
        ref = info.get("last_checked_sha") or info.get("default_branch", "main")
        for ef in info["e2_files"]:
            dest, verified = e2_destination(
                DOWNLOADS_DIR, repo, ef["path"], ef.get("sha256", "").lower()
            )
            if not verified:
                missing.append((repo, ref, ef, dest))

    if not missing:
        print("All E2 files are present. Nothing to retry.")
        return

    print(f"Missing E2 files: {len(missing)}")
    print()

    recovered = 0
    still_missing = 0

    for i, (repo, ref, ef, dest) in enumerate(missing, 1):
        path = ef["path"]

        # Handle files inside .yxzp archives
        if "!/" in path:
            yxzp_path, inner_name = path.split("!/", 1)
            print(f"  [{i}/{len(missing)}] {repo}/{yxzp_path} -> {inner_name} ... ", end="", flush=True)
            data = download_raw(repo, yxzp_path, ref)
            if not data:
                print("DOWNLOAD FAIL (yxzp)")
                still_missing += 1
                time.sleep(0.5)
                continue
            try:
                zf = zipfile.ZipFile(io.BytesIO(data))
                inner_data = zf.read(inner_name)
            except (zipfile.BadZipFile, KeyError, RuntimeError, OSError, EOFError) as exc:
                print(f"ZIP ERROR: {exc}")
                still_missing += 1
                time.sleep(0.5)
                continue
            file_data = inner_data
        else:
            print(f"  [{i}/{len(missing)}] {repo}/{path} ... ", end="", flush=True)
            file_data = download_raw(repo, path, ref)

        if not file_data:
            print("DOWNLOAD FAIL")
            still_missing += 1
            time.sleep(0.5)
            continue

        fmt = detect_format(file_data)
        if fmt != "E2":
            print(f"NOT E2 (got {fmt}) - ledger left unchanged")
            still_missing += 1
            time.sleep(0.3)
            continue

        # Verify hash if we have one
        file_hash = hashlib.sha256(file_data).hexdigest()
        expected = ef.get("sha256")
        if expected and file_hash != expected:
            print(f"HASH MISMATCH (got {file_hash[:12]}..., expected {expected[:12]}...)")
            still_missing += 1
            continue

        with open(dest, "wb") as f:
            f.write(file_data)

        meta = extract_e2_metadata(file_data)
        fields = meta["field_count"] if meta else "?"
        print(f"OK ({len(file_data):,} bytes, {fields} fields)")
        recovered += 1
        time.sleep(0.3)

    print()
    print(f"Recovered: {recovered}")
    print(f"Still missing: {still_missing}")


if __name__ == "__main__":
    main()
