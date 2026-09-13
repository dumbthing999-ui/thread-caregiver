# Day 4 — system specification and red contract tests

The user authorized progression after Day 3 and permits delegated agents. Read the [master plan](../univabio-plan/MASTER_PLAN.md), [Day 1 requirements](docs/day01/scope-and-acceptance.md), [Day 2 decision](docs/decisions/ADR-002-differentiation-gate.md), and actual [Day 3 spikes](docs/day03/spikes/run_all_spikes.py). Work remains local to this workspace; the master plan is read-only. Preserve peer work and prior test suites.

Objective: a reviewed data model, API and state contract, with reproducible failing tests against the existing spikes. The scheduled Day 4 date remains September 16, 2026; five planned agent-hours are a budget, not elapsed productive work. Early preparation does not shift the September 13–October 6 program.

Required artifacts:

1. `docs/day04/day03-audit.md`: independent inspection separating the 13 passing spike tests from untested or contradicted claims.
2. `contracts/day04/contract.json`: versioned machine-readable record, command, error and state registry; explicitly a project format rather than an OpenAPI/schema-validation claim.
3. `docs/day04/system-specification.md`: modules, data relationships, precise source anchors, deterministic publication gates and persistence constraints.
4. `docs/day04/api-contract.md`: exact request/response protocol, case authorization, concurrency, retries, failure responses and examples.
5. `docs/day04/state-and-invariants.md`: evidence/coordination/rehearsal transitions, conflict and replacement behavior, event history and requirement traceability.
6. `docs/day04/security-and-boundaries.md`: input, identity, isolation, export/reset, logging and untrusted-source constraints.
7. `docs/decisions/ADR-003-system-contract.md`: explicit narrowing and implementation cuts.
8. `tests/day04/`: runnable red tests against unchanged Day 3 code, positive controls and a strict expected-failure manifest; no skips or forced failures.
9. `docs/day04/red-test-plan.md` and measured `docs/day04/evidence/` results: distinguish red-test integrity from product correctness.
10. `docs/day04/day05-handoff.md`: family-isolated synthetic corpus plan and unfulfilled human comprehension/review checkpoints.
11. `docs/day04/review.md`, `status.json`, `verify_pack.py`: actual findings, computed counts and stdlib verification. Update README only from real acceptance evidence.

Acceptance: earlier tests still pass; every required artifact is substantive; references resolve; all FR-01–12 and INV-01–11 are traced; red tests fail for documented assertions rather than import/runtime errors; positive controls pass; independent contract review issues are resolved or explicitly left as implementation blockers. A green documentation verifier must never label the deliberately red product obligations implemented.

Day 4 does not implement the production API, database, UI or complete evaluation corpus. Text PDF fidelity, live model schema behavior, transaction concurrency, authorization and clinical/user benefit cannot be inherited from the Day 3 unit-test count. No packages, deployment, publication, organizer message or registration are needed.
