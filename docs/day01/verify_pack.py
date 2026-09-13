"""Local-only Day 1 document checks; no application or network execution."""
import csv
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = [
    "README.md", "AGENTS.md", "docs/day01/problem-brief.md",
    "docs/day01/scope-and-acceptance.md",
    "docs/decisions/ADR-001-project-selection.md",
    "docs/day01/eligibility-and-rules.md",
    "docs/day01/organizer-email-draft.md", "docs/day01/interview-guide.md",
    "docs/day01/risk-register.csv", "docs/day01/backlog.csv",
    "docs/day01/review.md",
]
errors = []
missing = [p for p in REQUIRED if not (ROOT / p).is_file()]
print(f"Required deliverables: {len(REQUIRED) - len(missing)}/{len(REQUIRED)} present")
for name in missing:
    errors.append(f"MISSING: {name}")

link_count = 0
broken = []
for name in REQUIRED:
    path = ROOT / name
    if path.suffix != ".md" or not path.is_file():
        continue
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
        url = urlsplit(target)
        if url.scheme or url.netloc or not url.path:
            continue
        link_count += 1
        if not (path.parent / unquote(url.path)).resolve().exists():
            broken.append(f"{name} -> {target}")
print(f"Local Markdown file links: {link_count} checked; {len(broken)} broken")
errors.extend(f"BROKEN LINK: {item}" for item in broken)

schemas = {
    "docs/day01/risk-register.csv": (
        ["id", "description", "severity", "evidence_status", "mitigation", "trigger", "owner_role"],
        "R", 10,
    ),
    "docs/day01/backlog.csv": (["task_id", "output", "status", "evidence"], "D1", 1),
}
for name, (header, prefix, minimum) in schemas.items():
    with (ROOT / name).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle, strict=True))
    data = rows[1:]
    issues = []
    if rows[0] != header:
        issues.append("header mismatch")
    if len(data) < minimum:
        issues.append("too few records")
    if any(len(row) != len(header) or any(not cell.strip() for cell in row) for row in data):
        issues.append("wrong width or empty field")
    ids = [row[0] for row in data]
    if ids != [f"{prefix}-{i:02d}" for i in range(1, len(data) + 1)]:
        issues.append("IDs not unique and sequential")
    if prefix == "R" and any(row[2] not in {"low", "medium", "high", "critical"} for row in data):
        issues.append("invalid severity")
    print(f"{name}: {len(data)} records; {len(header)} columns; " + ("FAIL" if issues else "PASS"))
    errors.extend(f"CSV ERROR: {name}: {issue}" for issue in issues)

scope = (ROOT / "docs/day01/scope-and-acceptance.md").read_text(encoding="utf-8")
for prefix, count in [("FR", 12), ("INV", 11)]:
    found = re.findall(rf"^\| ({prefix}-\d+) \|", scope, re.MULTILINE)
    expected = [f"{prefix}-{i:02d}" for i in range(1, count + 1)]
    ok = found == expected
    print(f"{prefix} definition IDs: {len(found)}; " + ("PASS" if ok else "FAIL"))
    if not ok:
        errors.append(f"Invalid {prefix} definition sequence")

for error in errors:
    print(error)
print("Overall: " + ("INCOMPLETE" if errors else "PASS (document structure only)"))
raise SystemExit(1 if errors else 0)
