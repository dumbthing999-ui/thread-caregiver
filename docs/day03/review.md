# Day 3 Critical Review & Architecture Assessment

## 1. Scope & Verification Review

Day 3 transitions THREAD from competitor analysis and workflow design into concrete, runnable feasibility spikes and system contracts.

### Empirical Test Execution Summary
The unified test runner executed 13 discrete test cases across three feasibility spikes:
- **Spike A (Exact Provenance & Text Anchoring)**: 7 tests passed (0 failures). Verified exact character offset resolution `[start:end]`, line/column computation, repeated-string prefix disambiguation, and rejection of modified/paraphrased quotes and binary corrupted files.
- **Spike B (Bounded Model Schema & Deterministic Gate)**: 4 tests passed (0 failures). Validated that candidate extractions missing exact anchors are blocked, medication instructions are strictly confined to read-only quotations (blocking clinical administration tasks), and adversarial prompt injections are neutralized.
- **Spike C (Revisions, History & Authoritative Rejection)**: 2 tests passed (0 failures). Verified multi-revision lifecycle without automatic last-upload-wins, fine-grained invalidation upon explicit replacement, atomic service-side stale write rejection (`STALE_REVISION_ERROR`), idempotency deduplication, and immutable audit persistence.

Total Spikes Execution Time: **0.005s** (100% passing, 0 warnings).

---

## 2. Critical Evaluation of Assumptions

### 2.1 Character Offsets vs Layout Fragility
- *Assumption*: Text extraction can reliably produce 1:1 character coordinates between parsed tokens and displayed document text.
- *Finding*: Plain UTF-8 text and markdown documents exhibit 100% deterministic character indexing. However, for complex multi-column PDFs with arbitrary font encodings or ligatures, naive text extraction can introduce whitespace discrepancies.
- *Remediation / Narrowing*: Day 3 narrows the supported ingest boundary to UTF-8 text, Markdown, and text-stream PDFs with extractable standard font dictionaries. Scanned bitmap documents and OCR are explicitly excluded.

### 2.2 Rehearsal Invalidation vs User Friction
- *Assumption*: Invalidating caregiver comprehension upon document replacement improves safety without causing excessive fatigue.
- *Finding*: Blanket invalidation of all tasks upon any document update frustrates caregivers. Fine-grained dependency tracking is essential: changing an appointment time must invalidate only the transport task and appointment acknowledgement, leaving unchanged items (e.g. clinic office phone number) intact.

### 2.3 Authoritative Concurrency Control
- *Assumption*: Client-side button disabling is insufficient in multi-caregiver environments.
- *Finding*: Confirmed. In companion-panel or multi-device setups, two caregivers can view the same screen simultaneously. Server-side optimistic locking (`If-Match: rev_id`) is strictly required to prevent stale writes from being committed.

---

## 3. Product Contract & Ethical Boundaries

1. **Non-Clinical Boundary**:
   THREAD does NOT prescribe, calculate dosages, or track drug administration. Medication summaries are strictly read-only verbatim quotations.
2. **Synthetic Personas**:
   All test fixtures (`s01_v1.txt`, `s01_v2.txt`, `s02_conflicting_a.txt`, `s04_medication_boundary.txt`, `s05_injection_control.txt`) use fictional names ("Pat Taylor", "Morgan Reed", "Alex Chen", "Jordan Casey") and synthetic medical text.
3. **No External Actions**:
   No network requests to external APIs or remote repository pushes were performed.

---

## 4. Day 4 Handoff & Readiness

Day 3 provides concrete empirical evidence that THREAD's core differentiators (source-anchored provenance, version-aware fine-grained invalidation, and deterministic nonclinical task gating) are technically feasible and robust against concurrency conflicts.

### Recommended Day 4 Scope:
1. Formalize API schema contracts using FastAPI / Pydantic models.
2. Build the SQLite-backed persistent audit store.
3. Implement the end-to-end evaluation harness against the synthetic case corpus.
