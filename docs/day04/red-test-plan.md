# Day 4 red tests — actual gaps in unchanged Day 3 spikes

The local run records **17 tests: 12 assertion failures, 5 passing positive controls, zero errors and zero skips**. These failures expose unresolved Day 1 contract gaps. This is a red baseline, not product acceptance, remote vulnerability testing, a running web service or clinical validation. Day 3 code and its existing tests are preserved unchanged; their earlier passing results describe the narrower original test set.

Run the actual assertions from the repository root:

```bash
python3 tests/day04/run_red_suite.py --record
```

The measured command exits **1** while the known gaps remain. It writes [structured outcomes](evidence/red-results.json) and [full unittest output](evidence/red-tests.txt). Both include actual test results; JSON also records an actual UTC timestamp, full test IDs, source/test/manifest SHA-256 hashes, invocation, raw suite exit code and baseline-check exit code. Timestamps are run metadata, not productive agent-hours.

For an explicit integrity check of this known failing baseline:

```bash
python3 tests/day04/run_red_suite.py --check-baseline
```

This command exits **0 only if exactly the manifest's 12 known tests fail with assertions, all five named controls pass, all expected tests run, and there are no errors, skips, expectedFailure markers or unexpected successes**. It prints “Red-baseline integrity: MATCH (not product PASS).” An additional failure, missing test, error or newly passing red assertion makes this integrity check fail. Newly passing product behavior should be reviewed and the baseline deliberately retired or updated; do not change expected results merely to hide failures.

The explicit [manifest](../../tests/day04/red-manifest.json) is the test registry. The [test module](../../tests/day04/test_contract_gaps.py) exercises actual public Day 3 Python entry points without mocked substitutes, network, external model, new dependencies or deliberately false assertions. One import test creates a temporary synthetic PDF-envelope file inside the owned tests directory and removes it afterward. The runner disables bytecode writing. No patient data is involved.

## Failure registry and repair evidence required

All test names below have prefix `test_contract_gaps.ContractGaps.`. Full IDs are stored in the manifest and measured JSON. Requirements follow the authoritative [Day 1 contract](../day01/scope-and-acceptance.md); several explanatory IDs inside the historical Day 3 source are inaccurate and are not treated as requirement definitions.

| Test method | Observed failure | Contract | Required future repair evidence |
| --- | --- | --- | --- |
| test_value_must_be_supported_by_its_quote | Friday field is accepted with exact Thursday quotation | FR-02; INV-01, INV-09 | Reject unsupported value or derive bounded display value from verified source; retain exact quote |
| test_empty_instruction_cannot_publish_supported | Empty fields list becomes a supported instruction | FR-02, FR-03; INV-01, INV-02 | Require supported fields before publication; expose unresolved/blocked output |
| test_clinical_category_cannot_spawn_transport | Clinical-treatment category can support an actionable transport task | FR-04; INV-08, INV-09 | Explicit eligible category/task matrix; reject invalid category or task dependency |
| test_allowed_task_label_cannot_hide_treatment_action | ARRANGE_TRANSPORT label accepts “Change the treatment now.” | FR-04; INV-08, INV-09 | Bounded deterministic task wording/arguments that cannot carry a clinical instruction |
| test_duplicate_revision_cannot_overwrite_source_identity | Reusing r1 replaces its document identity and version | FR-01, FR-06; INV-01 | Immutable identity binding; reject nonidentical reuse without changing old record |
| test_replacement_requires_existing_old_endpoint | Revision links to a nonexistent predecessor | FR-05; INV-04 | Validate both endpoints and relation before any mutation |
| test_replacement_cannot_point_to_itself | A new revision can replace itself and becomes superseded | FR-05; INV-04 | Reject self links atomically; later cycle checks also needed |
| test_idempotency_key_cannot_mask_different_operation | Key used for acknowledgement makes completion silently return without conflict | FR-07; INV-07 | Bind idempotency to scoped actor/operation/target and request fingerprint; reject changed request |
| test_idempotency_key_cannot_mask_different_payload | Same completion key with changed note returns prior task without reporting collision | FR-07; INV-07 | Compare canonical request payload and return explicit conflict for mismatched retry |
| test_history_payload_cannot_be_mutated_by_reader | Frozen event contains a mutable dict; reader rewrites stored status | FR-06; INV-01, INV-05 | Deeply immutable records or detached read views plus append-only persisted history |
| test_plain_ascii_pdf_is_rejected_by_text_only_importer | UTF-8-decodable PDF envelope is ingested as plain text | FR-01; INV-01 | Detect and reject unsupported PDF input before publication; encoding alone is insufficient |
| test_service_cannot_create_prohibited_clinical_task | Direct service method accepts MODIFY_TREATMENT | FR-04; INV-08, INV-09 | Authoritative task creation gate enforces boundaries even when extraction gate is bypassed |

The clinical-category case deliberately supplies a mismatched clinical category and appointment quotation; it establishes that the gate trusts category compatibility too broadly, not that all real transport related to treatment is clinically actionable. The PDF envelope is an unsupported-format negative fixture, not proof that a valid PDF parser exists. The idempotency assertions adopt the explicit Day 4 design requirement that a reused key with a different request yields a conflict; they do not require a particular HTTP status from today's in-memory classes.

## Positive controls and limits

The five controls verify exact-anchor resolution, accepted supported transport, blocked missing quotation, one event for an identical acknowledgement retry, and rejection of a fresh stale acknowledgement after explicit replacement. Their full IDs are under `test_contract_gaps.PositiveControls` in the manifest. They distinguish working narrow paths from demonstrated gaps, without extrapolating to whole-system correctness.

This set is intentionally bounded. It does not establish actual cross-session authorization, real parallel database transactions, persistence/restart behavior, complete conflict detection, immutable storage against all mutation paths, dependency-aware unchanged-content handling, rehearsal lifecycle, accessible UI, export fidelity or isolation. Actor names in these spikes are strings, not authenticated identities. No service endpoint or case-membership policy exists here to meaningfully test an actual authenticated cross-case attack. Those remain required implementation and testing work, not passing controls.

Future repairs must retain these assertions or replace them with demonstrably equivalent stronger contract tests. Do not edit the Day 3 historical implementation during this specification-first stage. Move eventual implementation into its intended module and explicitly rebind tests after review. The reviewer should inspect the assertions and measured traces, then separately accept the Day 4 specification and red-baseline reproducibility; neither decision is a product release gate.
