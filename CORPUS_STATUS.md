# Corpus Status

Status as of 2026-09-19. For reader execution and baseline comparison, see [VALIDATION.md](VALIDATION.md).

## Indexed E2 coverage

- 219 indexed source entries from 64 repositories.
- 183 unique indexed SHA-256 payloads.
- `downloads/e2/`: 201 files, 183 unique hashes, all 183 indexed hashes present, no unindexed hashes.
- `/mnt/tank/Data/YXDB/e2/`: 200 files, 182 unique hashes, all present hashes indexed, one indexed hash missing.
- Missing mounted-corpus hash: `baeec5eff8c7702b0d944151f06d75b27391196fb1c84afce73f41cb5d81117d`.
- Repository-local copy: `downloads/e2/AkimasaKajitani_AdventOfCode_temp__0b92615a8704_baeec5eff8c7.yxdb`.

The difference between 219 source entries and 183 unique hashes is expected: multiple indexed paths contain identical payloads. The difference between 201 local files and 183 unique hashes is also duplicate content, not additional corpus breadth.

## Retrieval run

Command:

```bash
python scripts/download.py e2 --report downloads/e2-retrieval-report.json
```

Result: 206 source entries were verified in place, 12 were restored from identical local payloads, one 210,153-byte payload was downloaded from its indexed immutable commit, and zero retrievals failed. Downloads and the JSON run report are intentionally git-ignored.

## Bounded discovery and check run

Discovery was intentionally bounded to the first result page for each of the 25 repository-search queries and 3 code-search queries:

```bash
python scripts/scan.py --discover-only --search-pages 1 --report downloads/discovery-report.json
```

This found 882 candidate repositories, including 121 not present in the prior ledger. It was not a complete pagination of GitHub results.

The first 30 new candidates in sorted order were checked from the saved discovery report, then all 99 candidates not yet in the ledger were checked. The second run retried the 8 unresolved candidates from the first run:

```bash
python scripts/scan.py --candidates-from downloads/discovery-report.json --limit 30 --report downloads/check-report.json
python scripts/scan.py --candidates-from downloads/discovery-report.json --new-only --report downloads/check-remaining-report.json
```

Across both runs, all 121 new candidates were attempted. 81 had no YXDB or supported archive input, 7 had supported archives, and 33 could not resolve their default-branch ref. One new E1 file and no new E2 payloads were found. The 88 completed checks increased the ledger from 1,730 to 1,818 repositories. The previously known 1,730 repositories were not refreshed in this bounded run.

The 33 ref failures remained unresolved after a final retry and are recorded by name in the git-ignored `downloads/check-unresolved-report.json`. They are:

```text
Angaluri1308/Alteryx
Au2mater/AlteryxExampleToolsV2
Costcoedward/Alteryx_Training_1
DragosGG4/Alteryx
Karthick-07/Alteryx
Kritikagoyal123/alteryx-retail-data-tableau-project
MahimaSahani/Alteryx-Practice-Workflows
RaymondSentabule/Data-Blending-with-Alteryx
SneakyShady/Alteryx-Challenges
TheCodeLibrary-Chapter1/Alteryx-Workflow
WesleyM2510/skills_alteryx
Yunyun0120/i5Dki0pKuRk3uqcbCTRy8WoM_EW0JipUII_e8pKzzMa8bU5vFj2t0NrI9VTwYxzpzE9L
brak99/Open-Yxdb
chuckmcmurray/alteryxdesigner
darshitkumbhani/Data-Analysis-Visualisation-of-Crime-Data
dgula27/Alteryx-Designer-Core
dmettam/Alteryx_Projects
joseatamy/-UCCw1l1CXFhBOriYXdbdrdnw
jsaumya/Alteryx-Challenges
kannanbsc/Online-training
keerthanakomati/Alteryx-Designer-Core-Certification
lramey/Open_AlteryxYXDB
nick-the-data-guy/hyperion_migration_project
pawansharma191103/Alteryx-Designer-Core-Certification
pedrodrfaria/Alteryx-Macros
radheshyamdhangar/alteryx-app
rahul02500/Alteryx-Training
sharmisthaanand234/Alteryx-Training
shyamagrawal33/alteryx-fraud-project
unnita/Alteryx-Training-program
vipul2710/Alteryx-Projects
yexingzhen/YXZprojexting
zhi-java/yxdbbpmeav
```
