#!/usr/bin/env python3
"""THREAD — Day 4 Specification & Red Baseline Pack Verifier (stdlib-only).

Validates:
  1. Presence and non-emptiness of all required Day 4 deliverables, contracts, and test artifacts.
  2. Referential integrity of all local Markdown links (0 broken links across Day 4 documentation).
  3. Integrity and schema of contracts/day04/contract.json (19 records, 16 operations, FR/INV tracing).
  4. Consistency and completeness of docs/day04/status.json.
  5. Exact red-baseline reproducibility via tests/day04/run_red_suite.py --check-baseline (exit 0).
  6. Explicit confirmation that raw red test suite exhibits 12 assertion failures (exit 1).

IMPORTANT: A passing result from this verifier certifies specification and red-baseline
integrity only. It does NOT represent passing product implementation.
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DAY4_DIR = REPO_ROOT / "docs" / "day04"
CONTRACTS_DIR = REPO_ROOT / "contracts" / "day04"
TESTS_DIR = REPO_ROOT / "tests" / "day04"

REQUIRED_FILES = [
    REPO_ROOT / "DAY4_BRIEF.md",
    CONTRACTS_DIR / "contract.json",
    DAY4_DIR / "day03-audit.md",
    DAY4_DIR / "system-specification.md",
    DAY4_DIR / "api-contract.md",
    DAY4_DIR / "state-and-invariants.md",
    DAY4_DIR / "security-and-boundaries.md",
    REPO_ROOT / "docs" / "decisions" / "ADR-003-system-contract.md",
    TESTS_DIR / "red-manifest.json",
    TESTS_DIR / "run_red_suite.py",
    TESTS_DIR / "test_contract_gaps.py",
    DAY4_DIR / "red-test-plan.md",
    DAY4_DIR / "evidence" / "red-results.json",
    DAY4_DIR / "evidence" / "red-tests.txt",
    DAY4_DIR / "day05-handoff.md",
    DAY4_DIR / "contract-review.md",
    DAY4_DIR / "review.md",
    DAY4_DIR / "status.json",
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
        return False, f"Missing: {missing}; Empty: {empty}"
    return True, f"All {len(REQUIRED_FILES)} required Day 4 artifacts present and non-empty."


def check_local_markdown_links() -> tuple[bool, str]:
    md_files = [
        REPO_ROOT / "DAY4_BRIEF.md",
        REPO_ROOT / "docs" / "decisions" / "ADR-003-system-contract.md",
    ] + sorted(DAY4_DIR.glob("*.md"))

    checked = 0
    broken = []
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

    for md in md_files:
        content = md.read_text(encoding="utf-8")
        for match in link_pattern.finditer(content):
            target = match.group(2).strip()
            # Ignore external web links, mailto, or pure in-page anchors
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            clean_target = target.split("#")[0]
            if not clean_target:
                continue
            resolved = (md.parent / unquote(clean_target)).resolve()
            checked += 1
            if not resolved.exists():
                broken.append(f"{md.relative_to(REPO_ROOT)} -> {target}")

    if broken:
        return False, f"Broken Markdown links ({len(broken)}): {broken}"
    return True, f"Local Markdown file links: {checked} checked; 0 broken."


def check_contract_json() -> tuple[bool, str]:
    contract_file = CONTRACTS_DIR / "contract.json"
    if not contract_file.exists():
        return False, "contract.json missing."

    try:
        data = json.loads(contract_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"contract.json malformed JSON: {exc}"

    if data.get("contract_version") != "0.1.0":
        return False, f"Unexpected contract_version: {data.get('contract_version')}"

    records = data.get("records", {})
    if len(records) != 19:
        return False, f"Expected 19 records in contract.json, found {len(records)}"

    operations = data.get("operations", [])
    if len(operations) != 16:
        return False, f"Expected 16 operations in contract.json, found {len(operations)}"

    # Verify FR and INV coverage across operations
    all_frs = {f"FR-{i:02d}" for i in range(1, 13)}
    all_invs = {f"INV-{i:02d}" for i in range(1, 12)}

    covered_frs = set()
    covered_invs = set()
    for op in operations:
        covered_frs.update(op.get("fr_ids", []))
        covered_invs.update(op.get("inv_ids", []))

    missing_frs = all_frs - covered_frs
    missing_invs = all_invs - covered_invs

    if missing_frs:
        return False, f"Contract operations do not trace all FRs. Missing: {sorted(missing_frs)}"
    if missing_invs:
        return False, f"Contract operations do not trace all INVs. Missing: {sorted(missing_invs)}"

    return True, f"contract.json valid: 19 records, 16 operations, all 12 FRs and 11 INVs traced."


def check_status_json() -> tuple[bool, str]:
    status_file = DAY4_DIR / "status.json"
    if not status_file.exists():
        return False, "status.json missing."

    try:
        data = json.loads(status_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"status.json malformed: {exc}"

    required_keys = ["updated_at", "stage", "specification_verdict", "red_baseline_verdict", "counts", "unresolved_dependencies"]
    for k in required_keys:
        if k not in data:
            return False, f"status.json missing required key '{k}'."

    counts = data.get("counts", {})
    if counts.get("red_suite_total_tests") != 17:
        return False, f"status.json red_suite_total_tests != 17: {counts.get('red_suite_total_tests')}"
    if counts.get("red_suite_assertion_failures") != 12:
        return False, f"status.json red_suite_assertion_failures != 12: {counts.get('red_suite_assertion_failures')}"
    if counts.get("red_suite_positive_controls_passed") != 5:
        return False, f"status.json red_suite_positive_controls_passed != 5: {counts.get('red_suite_positive_controls_passed')}"

    return True, "status.json valid: counts and structure verified."


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", text)


def check_red_baseline() -> tuple[bool, str]:
    runner = TESTS_DIR / "run_red_suite.py"
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", NO_COLOR="1", PYTHON_COLORS="0")

    # 1. Baseline integrity check (--check-baseline) must exit 0
    proc = subprocess.run(
        [sys.executable, str(runner), "--check-baseline"],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return False, f"--check-baseline exited {proc.returncode}; output:\n{proc.stdout}\n{proc.stderr}"
    
    clean_stdout = strip_ansi(proc.stdout)
    if "Red-baseline integrity: MATCH" not in clean_stdout:
        return False, f"--check-baseline did not report MATCH; output:\n{clean_stdout}"

    # 2. Raw red suite execution must exit 1 (proving intentional known failures exist)
    proc_raw = subprocess.run(
        [sys.executable, str(runner)],
        cwd=str(REPO_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    if proc_raw.returncode != 1:
        return False, f"Raw red suite unexpectedly exited {proc_raw.returncode} (expected 1 for known gaps)."
    
    clean_raw = strip_ansi(proc_raw.stdout + proc_raw.stderr)
    if not re.search(r"FAILED\s*\(\s*failures=12\s*\)", clean_raw):
        return False, f"Raw red suite did not report exactly 12 failures; output:\n{clean_raw}"

    return True, "Red suite baseline: exactly 12 failures, 5 controls pass; baseline integrity MATCH confirmed."


def verify_all() -> bool:
    print("==================================================")
    print("THREAD — Day 4 Specification & Red Pack Verifier")
    print("==================================================")

    all_ok = True

    # 1. Files
    ok, msg = check_required_files()
    print(f"Files Check:       {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    # 2. Markdown Links
    ok, msg = check_local_markdown_links()
    print(f"Links Check:       {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    # 3. Contract JSON
    ok, msg = check_contract_json()
    print(f"Contract Check:    {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    # 4. Status JSON
    ok, msg = check_status_json()
    print(f"Status Check:      {'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    # 5. Red Baseline Integrity
    ok, msg = check_red_baseline()
    print(f"Red Baseline Check:{'PASS' if ok else 'FAIL'} — {msg}")
    all_ok = all_ok and ok

    print("--------------------------------------------------")
    print(f"Overall Result:     {'PASS' if all_ok else 'FAIL'}")
    print("NOTICE: Red-baseline MATCH confirms reproducible contract gaps;")
    print("        it does NOT represent passing product implementation.")
    print("==================================================")
    return all_ok


if __name__ == "__main__":
    success = verify_all()
    sys.exit(0 if success else 1)
