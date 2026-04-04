# YXDB-Sources

A comprehensive index of public `.yxdb` files found on GitHub — both the original E1 format and the newer AMP-engine E2 format.

## What Is YXDB?

YXDB (`.yxdb`) is the native binary data format used by [Alteryx](https://www.alteryx.com/). There are two variants:

- **E1** — The original format, produced by the classic Alteryx engine.
- **E2** — A newer variant produced by Alteryx's AMP (Alteryx Multi-threaded Processing) engine.

Both share the `.yxdb` extension but are distinct formats.

## Current Index

| | Repositories | Files |
|---|---:|---:|
| **E1** | 170 | 2,407 |
| **E2** | 57 | 207 |
| **Total unique repos** | 203 | 2,614 |

*1,388 GitHub repositories scanned. 24 repos contain both E1 and E2 files.*

Source listings:
- [E1-Sources.md](E1-Sources.md) — Index of repositories containing E1 files with per-repo counts.
- [E2-Sources.md](E2-Sources.md) — Full index of E2 files with per-file paths, sizes, and SHA-256 hashes. Repos archived on Software Heritage.
- [index.json](index.json) — Machine-readable index of all repositories and files.

## Methodology

1. **Discover** — Search GitHub for repos containing `.yxdb` or `.yxzp` files using repository search queries and code-search queries (for adjacent Alteryx file extensions like `.yxmd`, `.yxmc`, `.yxzp`) via the `gh` CLI. Alteryx-owned repos are filtered out.

2. **Check** — For each candidate repo, resolve the current HEAD commit SHA. If the SHA matches the last check, skip entirely (no API calls for tree enumeration or downloads). This makes weekly re-runs cheap.

3. **Download & classify** — For repos with new commits, enumerate the git tree for `.yxdb`/`.yxzp` files, download each one, and classify as E1 or E2. E2 files are saved locally and recorded in the index.

4. **Archive** — Repos containing E2 files are submitted to the [Software Heritage Foundation](https://www.softwareheritage.org/) for permanent, independent archival. E1 files are common enough that archival is not necessary.

## Usage

### Prerequisites

- Python 3.13+
- [`gh` CLI](https://cli.github.com/) installed and authenticated (`gh auth login`)

### Scan

```bash
# Full run: discover new repos + check for updates + download
uv run scripts/scan.py

# Discovery only (no downloads — just find new candidate repos)
uv run scripts/scan.py --discover-only

# Re-check known repos only (skip discovery search)
uv run scripts/scan.py --check-only
```

### Archive E2 repos to Software Heritage

```bash
uv run scripts/archive.py            # submit all unarchived repos
uv run scripts/archive.py --status   # check submission status
uv run scripts/archive.py --dry-run  # show what would be submitted
uv run scripts/archive.py --force    # re-submit all repos
```

Set `SWH_API_TOKEN` in `.env` for higher rate limits (1,200/hr vs 120/hr anonymous).

### Download files

```bash
uv run scripts/download.py e2              # download all 207 E2 files
uv run scripts/download.py e1              # download all 2,407 E1 files
uv run scripts/download.py all             # download everything
uv run scripts/download.py e2 --repo OWNER/NAME   # single repo
uv run scripts/download.py e2 --dry-run    # preview
```

E2 files download directly from paths in `index.json`. E1 files require tree enumeration per repo (only counts are indexed).

### Generate the index

```bash
uv run scripts/gen_index.py          # regenerate index.json from known_repos.json
```

### View status

```bash
uv run scripts/report.py
```

### Rate limiting

The scanner is designed to be respectful to GitHub:
- Uses `gh` CLI (which handles auth tokens automatically)
- 2-second pause between search API calls
- 0.15–0.3 second pause between file downloads
- Automatic 65-second back-off on rate limit errors
- Repos at the same commit SHA are skipped entirely

### What gets committed

- `data/known_repos.json` — The ledger of every repo checked, with commit SHAs and E2 file hashes
- `data/swh_submissions.json` — Software Heritage submission log
- `index.json` — Machine-readable index of all YXDB sources
- `E2-Sources.md` / `E1-Sources.md` — Human-readable source listings
- `downloads/` — Downloaded E2 files (**git-ignored**)
- `data/sources.json` — Transient download resume state (**git-ignored**)

## Repo structure

```
YXDB-Sources/
├── README.md              # This file — project overview
├── E1-Sources.md          # E1 file source listing
├── E2-Sources.md          # E2 file source listing
├── index.json             # Machine-readable index (both E1 + E2)
├── LICENSE                # MIT (code) + CC BY 4.0 (docs)
├── scripts/
│   ├── scan.py            # Weekly scan orchestrator
│   ├── download.py        # Bulk file downloader
│   ├── archive.py         # Software Heritage archival submissions
│   ├── gen_index.py       # Generate index.json from known_repos.json
│   ├── detect.py          # Format detection + metadata extraction
│   ├── github.py          # GitHub API + download helpers
│   ├── state.py           # Persistent state management
│   ├── report.py          # Status report generator
│   └── seed_known_repos.py # One-time seed from existing provenance
├── data/
│   ├── known_repos.json   # Committed — the repo/commit/file ledger
│   └── swh_submissions.json # Committed — SWH submission log
└── downloads/             # Git-ignored — downloaded YXDB files
```

## License

- **Code** (`.py` files): [MIT](LICENSE)
- **Documentation/Data** (`README.md`, `E1-Sources.md`, `E2-Sources.md`, `index.json`): [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)

If you reference the source listings or index data, please credit this project. The referenced repositories are owned by their respective authors and subject to their own licenses.
