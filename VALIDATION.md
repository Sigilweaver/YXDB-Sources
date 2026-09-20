# Reader corpus validation

The reviewed E2 baseline is [data/e2-reader-baseline.json](data/e2-reader-baseline.json).
It covers 183 unique payloads with 167 successful reads and 16 explicit decode
errors per reader. See [VALIDATION_RESULTS.md](VALIDATION_RESULTS.md) for the
verification scope and remaining unsupported cases.

Run both freshly built readers against the same immutable inputs. Each file is
identified by SHA-256; duplicate content is decoded once per reader. Each decode
runs in a separate process with a timeout, so a crash or pathological record does
not prevent the rest of the corpus from being checked.

```sh
python scripts/validate_corpus.py /mnt/tank/Data/YXDB/e2 downloads \
  --sigilyx-python /path/to/sigilyx/venv/bin/python \
  --openyxdb-python /path/to/openyxdb/venv/bin/python \
  --timeout 60 --output /tmp/yxdb-results.json
```

Use directories containing only the intended corpus files. The roots are
searched recursively. `--reader sigilyx` or `--reader openyxdb` selects one reader.
Optional `--sigilyx-pythonpath` and `--openyxdb-pythonpath` point to local package
directories when testing freshly built extensions without installing them.
Confirm build provenance before running; the runner cannot prove an installed
extension matches a source checkout.

The report records declared/decoded count mismatches, decode errors, timeouts,
crashes, column names, and a deterministic digest of successful decoded values.
The digest preserves value types, nulls, negative zero, and non-finite floats.
It is a regression check within each reader, not an independent correctness
oracle or a promise of equivalent representation between different readers.
Check semantic correctness against known values, original source data, or a
trusted producer in addition to this report.

For the first run, decode errors cause a nonzero exit status. Review each failure
and its reproducer before accepting that report as a baseline. Known unsupported
inputs may raise; unexplained hangs, crashes, and count mismatches cannot be
accepted as known failures. Do not classify an input as corrupt solely because
these readers reject it.

```sh
python scripts/validate_corpus.py /mnt/tank/Data/YXDB/e2 downloads \
  --baseline /path/to/reviewed-baseline.json --output /tmp/yxdb-next.json
```

For the complete indexed E2 corpus and checked-in baseline, use freshly built
reader environments:

```sh
python scripts/validate_corpus.py downloads/e2 \
  --sigilyx-python /path/to/sigilyx/venv/bin/python \
  --openyxdb-python /path/to/openyxdb/venv/bin/python \
  --baseline data/e2-reader-baseline.json --output /tmp/yxdb-release-check.json
```

Baseline checks require exact per-hash outcomes, including error type/message
for known failures and value digests for successful files. Changed failures,
new inputs, missing inputs, and newly successful files require review. Paths and
timings can change without invalidating a baseline. Reports are never overwritten
or automatically promoted to baselines. Use identical reader selections when
comparing runs.

A release can retain documented unsupported inputs, provided they raise clearly.
Require a completed corpus run, no unreviewed changes in results, and independent
value regressions for decoder changes. Strict errors are the default contract;
returning invented nulls or silently skipping records is not a successful read.
