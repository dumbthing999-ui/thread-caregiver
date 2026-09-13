# Day 5 handoff — corpus families, annotation and review

Status: planning handoff. No 120-packet corpus, independent labels, participant review or held-out evaluation is created or claimed here. Day 4 develops contracts and failing tests; Day 5 owns corpus authoring, partition inventory and the annotation/review queue. The [master plan](../../../univabio-plan/MASTER_PLAN.md) assigns five planned agent-hours to each of Days 4 and 5; these are budgets, not measured productive runtime. Early work does not shift the September 13–October 6 program.

## Prerequisites and scope

Use the final Day 4 resource/API contract and [security boundaries](security-and-boundaries.md), constrained by [Day 1 requirements](../day01/scope-and-acceptance.md). Initial supported input is original fictional English UTF-8 plain text. PDF layouts, scanned files and binary text can be rejection controls only; they must not inflate supported-format claims. Day 3 demonstrations and Day 4 red fixtures are development evidence, not a held-out corpus or proof of live model/service behavior.

Before generation, assign a corpus custodian/reviewer role and determine a storage boundary for locked packets and gold labels. Named humans and availability remain unconfirmed. If secure separation or independent review is unavailable, continue authoring development material and transparent engineering checks, but mark the release-evaluation dependency blocked. Do not quietly replace independent review with the generator or claim held-out rigor from hidden filenames in a shared agent workspace.

## Partition families before generating packets

Target exactly **120 original synthetic packets: 40 development, 20 validation, 60 locked test**. First define scenario/template families and their partition membership, then generate packets inside their allocated families. A family includes related wording templates, source-update structures and derivations: renaming a fictional person, shifting an appointment or paraphrasing text does not make a new independent family. All variants and paired revisions stay within the same partition. Freeze a family manifest before authoring; record later amendments and why they do not leak information.

Use `family_id`, `partition`, `packet_id`, `scenario_class`, `source_document_ids`, `pair_id` where applicable, `author_role`, `review_status`, `content_hash` and `exposure_status` in the inventory. Record original authorship/license decisions without inventing authors or claiming rights to copied content. The manifest must verify unique IDs, exact partition counts, no cross-partition family membership and valid within-partition pair references. It should not expose locked answer labels to coding agents.

The 60 locked packets include **20 packets arranged as 10 old/new pairs**, leaving 40 other locked packets. A pair is two packets, not one packet plus an extra uncounted revision. A family may contain more than one pair, but remains isolated. Fix the final family counts/distribution during Day 5 manifest design; do not improvise numerical coverage after observing results. The same conceptual risk can appear across partitions through independently designed families; derivations of one template cannot.

Day 3 fixtures and Day 4 failing-test inputs get an explicit exposed-development designation. Inventory them separately from the 120-packet target unless they are deliberately incorporated into the 40 development count with documented family provenance. They can never be relabeled locked. This handoff does not generate locked packets or labels.

## Coverage and annotation contract

The corpus must combine supported successes with must-block controls. Blocking everything cannot satisfy the evaluation. Assign scenario-class coverage in the family manifest before generation; ensure each relevant class has an inspectable rationale and sufficient examples without presenting a planned distribution as achieved.

| Scenario class | Labels/evidence needed | Requirement trace |
| --- | --- | --- |
| Clean appointments and office contacts | Exact fields and quotation intervals; permitted transport/contact-location tasks; expected omissions under the bounded Day 4 grammar | FR-01, FR-02, FR-04; INV-01, INV-09 |
| Missing dates/times and unresolved wording | Missing-field labels; no invented values; permissible neutral clarification text | FR-03, FR-04; INV-03, INV-08 |
| Independent conflicting sources | Both anchors and unresolved conflict; no newest-upload-wins or disputed action selection | FR-03, FR-05; INV-03, INV-04, INV-08 |
| Explicit replacement and repeated upload | Replacement metadata separate from authority; immutable versions; expected current versus historical state | FR-05, FR-06; INV-01, INV-04, INV-05, INV-06 |
| Changed, unchanged and ambiguous dependencies | Document-wide invalidation expected in initial scope; unnecessary rereviews recorded; no invented selective mapping | FR-06, FR-08; INV-02, INV-05, INV-06 |
| Source quotation traps | Repeated strings, Unicode, punctuation, negation and altered quotations; exact interval and expected rejection | FR-01, FR-02; INV-01, INV-09 |
| Read-only medication wording | Exact start/stop/polarity and uncertainty labels; no administering, calculating or scheduling task | FR-02, FR-04; INV-09 |
| Unrelated, binary and unsupported input | Explicit unsupported/irrelevant decisions; no fabricated extraction | FR-01; INV-11 |
| Prompt injection and markup | Source remains inert; prohibited tool/network effects; safe text rendering | FR-11; INV-11 |
| Source-bound rehearsal | Cited revision, answerable source-location/wording question; unclear answer path; stale attempt status | FR-08; INV-02, INV-05, INV-10 |

Medication examples may include original read-only PRN/taper wording solely for textual fidelity and abstention. Never build dose/timing derivations or expected administration actions. Corpus source text is untrusted input; malicious fixtures must not be executed or fetched by generation/annotation tools.

Concurrency, identity, idempotency, reset and export require separate **stateful service test sequences** as well as any packet content. A document score cannot prove an atomic stale-write rejection. Tests must cover global case preconditions, resource-bound revisions, exact accepted retries after replacement, changed-fingerprint rejection, cross-case access and preserved historical events (FR-06, FR-07, FR-09, FR-10, FR-11; INV-05, INV-06, INV-07, INV-11).

## Annotation and independent review

Define an annotation guide before creating answer keys. For each supported field record immutable document/version, exact quote, start/end convention and permissible interpretation. Separately label evidence state, allowed nonclinical tasks, event validity and rehearsal state. Do not use source presence as evidence of clinical correctness. Uncertain labels need a disagreement/review state, not a forced answer.

Review workflow: generator/author proposes labels → a separately identified reviewer checks the source and contract → discrepancies are recorded → adjudication records the final choice, rationale and reviewer scope. A qualified scenario-language reviewer is a separate dependency from annotation correctness. Neither an AI critic nor another agent's agreement establishes human or clinical review. Record actual reviewer identity/role only when participation exists and disclosure is appropriate; otherwise use pending role fields.

Locked material must remain unavailable to implementation/tuning agents and ordinary prompts. If any locked family or gold label is exposed, mark it exposed and move its future results to regression/development reporting; commission fresh independent families before renewed held-out claims. If independent review is unavailable, label the corpus author-reviewed only and **make no held-out validation claim**. Availability limitations must not disappear from status when schema checks pass.

## Evaluation preparation and Day 5 exit evidence

Prepare the inventory, partition manifest, annotation guide, review queue and a stdlib structural checker. Day 5 does not run the final benchmark. Later evaluation compares the same supported tasks across a plain-document human baseline, same-model summary, rule parser and THREAD, with an invalidation-disabled ablation for the revision hypothesis. Comparison denominators must match each system's actual outputs; do not demand graph fields from a plain summary.

Retain packet/family IDs, configuration, raw synthetic outputs and errors in eventual run evidence. Report critical textual errors, precision/recall with counts, abstentions, actionable coverage, false alarms, unnecessary document-wide rereviews and revision failures. Repeated runs do not create independent patients or independently authored packets. Claimed release targets in Day 1 remain targets until executed with reviewed labels.

Day 5 is ready only when actual artifacts show the intended 40/20/60 counts, isolated families, intact pair accounting, original fictional provenance, checked label references, documented exposure boundaries and an honest review queue. If only development material is possible, report partial corpus status and the exact remaining counts; do not manufacture completion by copying templates into locked partitions. No real records, vendor excerpts or third-party health-page text belong in the corpus.

## Entrant comprehension checkpoint — pending

Before treating Day 4's contract as understood, the entrant should explain one exact source anchor, one rejected unsupported transformation, a replacement/invalidation transition, why a stale acknowledgement is rejected at the service, why an accepted retry cannot reactivate validity, and one actual failing test plus the proposed fix. Ask them to distinguish case state_version from document/resource revisions and historical completion from current validity. Record their actual explanation or questions only after the walkthrough occurs. This checklist is **PENDING**, not proof that the entrant has reviewed or understood any code.

Eligibility, team composition, guardian conditions, organizer responses, recruitment and publication remain separate pending dependencies. No external contact or release is implied by this handoff.
