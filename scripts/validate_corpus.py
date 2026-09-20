"""Run each reader/file in isolation and compare a reviewed, hash-keyed baseline.

This checks stability of each reader's output, not independent correctness.
Reader implementations can agree on an incorrect interpretation of a file.
"""

from __future__ import annotations

import argparse
import collections
import datetime
import decimal
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def canonical(value):
    """Retain value types and special values in deterministic JSON."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return {"float": value.hex() if math.isfinite(value) else str(value)}
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"bytes": bytes(value).hex()}
    if isinstance(value, (datetime.date, datetime.time, datetime.datetime)):
        return {type(value).__name__: value.isoformat()}
    if isinstance(value, decimal.Decimal):
        return {"decimal": str(value)}
    if isinstance(value, (list, tuple)):
        return [canonical(item) for item in value]
    if isinstance(value, dict):
        return {str(key): canonical(item) for key, item in value.items()}
    raise TypeError(f"unsupported result type: {type(value).__name__}")


def worker(reader: str, path: Path) -> dict:
    # Imports deliberately happen inside the isolated process, so a missing
    # extension is an infrastructure failure, not an accepted decode failure.
    if reader == "sigilyx":
        import sigilyx

        def decode():
            declared = sigilyx.record_count(str(path))
            frame = sigilyx.read_yxdb(str(path), spatial="raw")
            return declared, frame.height, frame.columns, frame.iter_rows()
    else:
        from openyxdb._openyxdb import Reader

        def decode():
            with Reader(str(path)) as source:
                declared = source.num_records
                columns = source.read_columns()
            lengths = {len(values) for values in columns.values()}
            if len(lengths) > 1:
                raise AssertionError("decoded columns have different lengths")
            return declared, next(iter(lengths), 0), list(columns), zip(*columns.values())

    try:
        declared, count, names, rows = decode()
    # SigilYX maps its ConversionError to Python TypeError. Keep imports and
    # result canonicalization outside this catch so harness failures cannot
    # become accepted decoder outcomes.
    except (ValueError, RuntimeError, OSError, TypeError) as exc:
        return {"status": "decode_error", "error_type": type(exc).__name__, "error": str(exc)}
    if count != declared:
        return {"status": "count_mismatch", "declared": declared, "rows": count}
    digest = hashlib.sha256()
    for row in rows:
        digest.update(json.dumps(canonical(row), ensure_ascii=True, separators=(",", ":")).encode())
        digest.update(b"\n")
    return {"status": "ok", "rows": count, "columns": names, "values_sha256": digest.hexdigest()}


def run_one(reader: str, path: Path, python: str, timeout: float, pythonpath: str | None) -> dict:
    env = os.environ.copy()
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    started = time.monotonic()
    try:
        result = subprocess.run(
            [python, str(Path(__file__).resolve()), "--worker", reader, str(path)],
            capture_output=True, text=True, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        outcome = {"status": "timeout", "timeout_seconds": timeout}
    except OSError as exc:
        outcome = {"status": "runner_error", "error": str(exc)}
    else:
        if result.returncode:
            outcome = {"status": "crash", "returncode": result.returncode, "error": result.stderr[-4000:]}
        else:
            try:
                outcome = json.loads(result.stdout)
            except (ValueError, TypeError):
                outcome = {"status": "runner_error", "error": "worker did not emit JSON", "output": result.stdout[-4000:]}
    return {**outcome, "seconds": round(time.monotonic() - started, 4)}


def signature(result: dict) -> dict:
    return {key: value for key, value in result.items() if key not in {"seconds", "paths"}}


def compare(results: dict, baseline: dict | None) -> list[str]:
    problems = []
    for key, result in results.items():
        expected = baseline.get(key) if baseline is not None else None
        if result["status"] not in {"ok", "decode_error"}:
            problems.append(f"{key}: {result['status']} cannot be accepted as a known failure")
        elif expected is not None:
            if signature(result) != signature(expected):
                problems.append(f"{key}: result changed from reviewed baseline")
        elif baseline is not None or result["status"] != "ok":
            problems.append(f"{key}: unreviewed {result['status']}")
    if baseline is not None:
        for key in baseline.keys() - results.keys():
            problems.append(f"{key}: baseline input missing from this run")
    return problems


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2], Path(sys.argv[3]))))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="Directories of .yxdb files (searched recursively)")
    parser.add_argument("--reader", action="append", choices=["sigilyx", "openyxdb"])
    parser.add_argument("--sigilyx-python", default=sys.executable)
    parser.add_argument("--openyxdb-python", default=sys.executable)
    parser.add_argument("--sigilyx-pythonpath")
    parser.add_argument("--openyxdb-pythonpath")
    parser.add_argument("--timeout", type=float, default=60)
    parser.add_argument("--baseline", type=Path, help="Previously reviewed report; never updated automatically")
    parser.add_argument("--output", required=True, type=Path, help="New report path (must not already exist)")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    if args.output.exists():
        parser.error("output already exists; choose a new report path")
    if any(not root.is_dir() for root in args.roots):
        parser.error("every corpus root must be an existing directory")
    inputs: dict[str, list[str]] = {}
    for root in args.roots:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.suffix.lower() == ".yxdb":
                paths = inputs.setdefault(file_hash(path), [])
                resolved = str(path.resolve())
                if resolved not in paths:
                    paths.append(resolved)
    if not inputs:
        parser.error("no .yxdb inputs found")
    baseline = json.loads(args.baseline.read_text())["results"] if args.baseline else None
    readers = list(dict.fromkeys(args.reader or ["sigilyx", "openyxdb"]))
    results = {}
    for digest, paths in sorted(inputs.items()):
        for reader in readers:
            result = run_one(reader, Path(paths[0]), getattr(args, f"{reader}_python"), args.timeout,
                             getattr(args, f"{reader}_pythonpath"))
            # Decode messages often include a full filename. Identity is already
            # represented by the content hash, so keep baselines relocatable.
            if "error" in result:
                result["error"] = result["error"].replace(paths[0], "<file>")
            results[f"{reader}:{digest}"] = {**result, "paths": paths}
            print(f"{reader}: {result['status']}: {Path(paths[0]).name}", flush=True)
    problems = compare(results, baseline)
    summary = {reader: dict(collections.Counter(value["status"] for key, value in results.items()
                                               if key.startswith(reader + ":"))) for reader in readers}
    report = {"format_version": 1, "unique_files": len(inputs), "paths": sum(map(len, inputs.values())),
              "summary": summary, "problems": problems, "results": results}
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    print(json.dumps(summary, indent=2))
    print(f"{len(problems)} baseline/validation problems; report: {args.output}")
    return bool(problems)


if __name__ == "__main__":
    raise SystemExit(main())
