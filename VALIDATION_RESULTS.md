# E2 validation results

Verified on 2026-09-19 using freshly built local SigilYX and OpenYXDB extensions.
Changes remain uncommitted and unpublished.

## Corpus and outcomes

The complete indexed E2 corpus contains 219 source entries, 201 local paths,
and 183 unique SHA-256 payloads. Each unique payload was decoded once per reader
in an isolated process with a 30-second timeout, using public default read
behavior (SigilYX spatial values requested as raw bytes).

| Reader | Decoded | Explicit decode errors | Crashes | Timeouts | Count mismatches |
| --- | ---: | ---: | ---: | ---: | ---: |
| SigilYX | 167 | 16 | 0 | 0 | 0 |
| OpenYXDB | 167 | 16 | 0 | 0 | 0 |

Both readers reject the same 16 payloads at the same record numbers. The
slowest isolated process in these runs took 7.985 seconds for SigilYX and
9.895 seconds for OpenYXDB, including interpreter startup and value hashing.
Those are observed validation timings, not library performance guarantees.

A subsequent combined run against the persisted baseline completed with exit
status 0 and zero baseline/validation problems. It reproduced all 366 reader/file
outcomes, including successful value digests. Its local report is
`downloads/release-validation-2026-09-19.json`.

The [reviewed baseline](data/e2-reader-baseline.json) pins each reader's success
count, column names, value digest, or exact error type and message by file hash.
It also records the tested extension artifact hashes. Future changes to these
outcomes require review. Instructions: [VALIDATION.md](VALIDATION.md).

## Known unsupported inputs

Record numbers are zero-based. Eleven payloads have competing complete Int32
interpretations; five do not match the supported schema encoding. These are
unsupported by the current readers, not proven corrupt source files. Duplicate
paths for the same payload share one baseline entry.

| Representative local filename | Record | Reason |
| --- | ---: | --- |
| `ChrisDataBlog_AoC_2024_day6_map.yxdb` | 5 | Ambiguous Int32 framing |
| `SeanAdams10_AdventOfCodePython_tmpGrid.yxdb` | 5 | Ambiguous Int32 framing |
| `relee713_alteryx_Task2Output.yxdb` | 68 | Ambiguous Int32 framing |
| `shouryajain72-code_Shourya-Alteryx_practice.yxdb` | 48789 | Ambiguous Int32 framing |
| `habramsohn_MSBA-Portfolio_Task3Output.yxdb` | 4537 | Ambiguous Int32 framing |
| `habramsohn_MSBA-Portfolio_Task2Output.yxdb` | 41 | Ambiguous Int32 framing |
| `AkimasaKajitani_AdventOfCode_temp2.yxdb` | 205 | Ambiguous Int32 framing |
| `rdabhane47_alteryx-amazon-cleanup_amazon_cleaned.yxdb` | 32 | Ambiguous Int32 framing |
| `vaishnavi-gawali_Analyzing-Sales-Data-using-Alteryx_Order Data Complete Backup.yxdb` | 0 | Ambiguous Int32 framing |
| `etiennebert_Forest_Club_to_Halt_Deforestation_C-2_HILDA_V_2_1_State_GTAP_AEZ_limited.yxdb` | 4 | No exact schema match |
| `AkimasaKajitani_AdventOfCode_ForP2macro_2.yxdb` | 37 | Ambiguous Int32 framing |
| `rahulnarang45_Alteryx-Realworld-ProblemCaseStatements_q4_output1.yxdb` | 0 | No exact schema match |
| `AkimasaKajitani_AdventOfCode_temp__0b92615a8704_baeec5eff8c7.yxdb` | 10 | Ambiguous Int32 framing |
| `etiennebert_Forest_Club_to_Halt_Deforestation_C-2_HILDA_V_2_1_Transition_GTAP_AEZ_limited.yxdb` | 10 | No exact schema match |
| `Muruganandanj_BANK-CUSTOMER-CHURN-ALTERYX_PREDCITIONS.yxdb` | 0 | No exact schema match |
| `doriantino_Audit_Fraude_Bancaire_Alteryx_TOTAL VN.yxdb` | 0 | No exact schema match |

## Scope and limits

- SigilYX: 226 Rust unit tests, 4 integration tests, and 4 doctests passed;
  59 fixture-dependent tests were ignored. Its E2 eager/streaming corpus test
  passed for all 201 paths, including exact expected errors for unsupported
  hashes.
- OpenYXDB: the current shared-corpus Python suite passed 271 tests with one
  skip, including 219 E2 checks. The broader mounted-corpus suite passed 1,259
  tests before the final ambiguity-only correction; the shared E2 suite was
  rerun after that correction.
- YXDB-Sources: 17 unit tests passed, covering retrieval integrity, scanner
  retry behavior, baseline enforcement, and isolated worker outcomes.
- Decoder regressions cover mixed Int32 widths, value-distinct complete parses,
  a failed uniform parse hiding a valid alternative, invalid scalar prefixes
  and widths, unresolved blob references, and bounded malformed-record handling.
- The corpus verifies full read completion and declared record counts. Successful
  value digests establish a repeatable regression baseline; they do not prove
  semantic correctness independently of these implementations.
- No original CSV was available in the inspected Amazon source repository.
  The Amazon file now raises on record 32 because competing interpretations
  produce different prices. This is intentional, even though earlier code
  appeared to load it successfully.
- Edward's reported file was not available. These changes do not establish that
  the reported issue is fixed.
- This pass covers E2 corpus reads. E1 was not rerun through the shared digest
  runner. Source discovery was bounded; unresolved upstream refs and the
  deferred refresh of previously known repositories are documented in
  [CORPUS_STATUS.md](CORPUS_STATUS.md).

The local raw reports are git-ignored under `downloads/`:
`sigilyx-validation-complete-2026-09-19.json` and
`openyxdb-validation-verified-2026-09-19.json`.
