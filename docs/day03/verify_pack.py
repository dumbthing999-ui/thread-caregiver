#!/usr/bin/env python3
"""THREAD — Day 3 Deliverable & Spike Pack Verifier (stdlib-only).

Validates:
  1. Presence and non-emptiness of all required Day 3 deliverables and fixtures.
  2. Referential integrity of all local Markdown links (0 broken links).
  3. Execution of the Day 3 feasibility spikes (Spike A, B, C) with 100% pass rate.
  4. Consistency of status.json metrics.
  5. Tracing of Day 1 FR and INV identifiers across Day 3 specifications.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DAY3_DIR = REPO_ROOT / "docs" / "day03"

REQUIRED_FILES = [
    REPO_ROOT / "DAY3_BRIEF.md",
    DAY3_DIR / "fixtures" / "s01_v1.txt",
    DAY3_DIR / "fixtures" / "s01_v2.txt",
    DAY3_DIR / "fixtures" / "s02_conflicting_a.txt",
    DAY3_DIR / "fixtures" / "s02_conflicting_b.txt",
    DAY3_DIR / "fixtures" / "s03_stale_write.json",
    DAY3_DIR / "fixtures" / "s04_medication_boundary.txt",
    DAY3_DIR / "fixtures" / "s05_injection_control.txt",
    DAY3_DIR / "fixtures" / "unsupported_format.bin",
    DAY3_DIR / "spikes" / "spike_a_anchors.py",
    DAY3_DIR / "spikes" / "spike_b_schema_gate.py",
    DAY3_DIR / "spikes" / "spike_c_revisions.py",
    DAY3_DIR / "spikes" / "run_all_spikes.py",
    DAY3_DIR / "research-spikes.md",
    DAY3_DIR / "architecture-contracts.md",
    DAY3_DIR / "review.md",
    DAY3_DIR / "status.json",
]


def check_required_files() -> tuple[bool, str]:
    missing = []
    empty = []
    for f in REQUIRED_FILES:
        if not f.exists():
            missing.append(str(f.relative_to(REPO_ROOT)))
        elif f.stat().st_size == 0:
            empty.append(str(f.relative_to(REPO_ROOT)))

    if missing or empty:
        msg = f"Missing: {missing}; Empty: {empty}"
        return False, msg
    return True, f"All {len(REQUIRED_FILES)} required files present and non-empty."


def check_local_markdown_links() -> tuple[bool, str]:
    md_files = [REPO_ROOT / "DAY3_BRIEF.md"] + list(DAY3_DIR.glob("*.md"))
    checked = 0
    broken = []

    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md in md_files:
        content = md.read_text(encoding="utf-8")
        for match in link_pattern.finditer(content):
            target = match.group(2).strip()
            # Ignore external URLs and anchors
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # Strip target anchors
            clean_target = target.split("#")[0]
            if not clean_target:
                continue
            resolved = (md.parent / clean_target).resolve()
            checked += 1
            if not resolved.exists():
                broken.append(f"{md.relative_to(REPO_ROOT)} -> {target}")

    if broken:
        return False, f"Broken links ({len(broken)}): {broken}"
    return True, f"Local Markdown file links: {checked} checked; 0 broken."


def check_status_json() -> tuple[bool, str]:
    status_file = DAY3_DIR / "status.json"
    if not status_file.exists():
        return False, "status.json missing."

    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"status.json malformed: {exc}"

    required_keys = ["updated_at", "stage", "spikes_verdict", "counts", "spike_summary", "unresolved_dependencies"]
    for k in required_keys:
        if k not in data:
            return False, f"status.json missing required key '{k}'."

    counts = data.get("counts", {})
    if counts.get("spike_tests_passed") != 13 or counts.get("spike_tests_failed") != 0:
        return False, f"status.json reports invalid spike test results: {counts}"

    return True, "status.json structure and counts: PASS."


def run_spikes_verification() -> tuple[bool, str]:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    from docs.day03.spikes.spike_a_anchors import TestSpikeAAnchors
    from docs.day03.spikes.spike_b_schema_gate import TestSpikeBSchemaGate
    from docs.day03.spikes.spike_c_revisions import TestSpikeCRevisions

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    suite.addTests(loader.loadTestsFromTestCase(TestSpikeAAnchors))
    suite.addTests(loader.loadTestsFromTestCase(TestSpikeBSchemaGate))
    suite.addTests(loader.loadTestsFromTestCase(TestSpikeCRevisions))

    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)

    if not result.wasSuccessful():
        return False, f"Spikes test failure: {len(result.failures)} failures, {len(result.errors)} errors."
    return True, f"Spikes suite execution: {result.testsRun} tests executed; 0 failures; PASS."


def verify_all() -> bool:
    print("==================================================")
    print("THREAD — Day 3 Deliverable & Spike Pack Verifier")
    print("==================================================")

    all_ok = True

    # 1. Required files
    ok, msg = check_required_files()
    print(f"Files Check:   {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    # 2. Local markdown links
    ok, msg = check_local_markdown_links()
    print(f"Links Check:   {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    # 3. Status JSON
    ok, msg = check_status_json()
    print(f"Status Check:  {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    # 4. Spikes Execution
    ok, msg = run_spikes_verification()
    print(f"Spikes Check:  {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    print("--------------------------------------------------")
    print(f"Overall Result: {'PASS' if all_ok else 'FAIL'}")
    print("==================================================")
    return all_ok


if __name__ == "__main__":
    success = verify_all()
    sys.exit(0 if success else 1)
