"""Compute Day 2 counts from artifacts; does not assert verification passed."""
import csv
import json
import re
import runpy
from datetime import datetime, timezone
from pathlib import Path

DAY = Path(__file__).resolve().parents[1]
REQUIRED = ['research-brief.md', 'competitor-matrix.csv', 'competitor-analysis.md',
            '../decisions/ADR-002-differentiation-gate.md', 'caregiver-workflow.md',
            'storyboard.md', 'interaction-acceptance.csv', 'day03-handoff.md',
            'review.md', 'status.json', 'evidence/sources.jsonl', 'evidence/search-log.jsonl']
def jsonl(name):
    p = DAY / name
    return [json.loads(line) for line in p.read_text().splitlines()] if p.exists() else []
def rows(name):
    p = DAY / name
    if not p.exists():
        return []
    with p.open(newline='') as handle:
        return list(csv.DictReader(handle))
sources = jsonl('evidence/sources.jsonl')
queries = jsonl('evidence/search-log.jsonl')
matrix = rows('competitor-matrix.csv')
criteria = rows('interaction-acceptance.csv')
by_id = {s['id']: s for s in sources}
products = set()
for row in matrix:
    if row['evidence_level'] == 'design_baseline':
        continue
    for sid in re.findall(r'\bS\d+\b', row['evidence_ids']):
        source = by_id.get(sid, {})
        if source.get('status') == 'retrieved' and source.get('source_class', '').startswith('primary'):
            products.add(row['name'].strip().casefold())
beats = []
if (DAY / 'storyboard.md').exists():
    for line in (DAY / 'storyboard.md').read_text().splitlines():
        cells = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(cells) == 5 and cells[2].isdigit() and cells[3].isdigit():
            beats.append(int(cells[3]))
p = DAY / 'status.json'
status = json.loads(p.read_text()) if p.exists() else {}
status.update({
    'updated_at': datetime.now(timezone.utc).isoformat(),
    'selected_model': 'gpt-6-astra',
    'requested_reasoning': 'medium',
    'execution_note': 'Model fields preserve the Day 2 requested configuration, not independent runtime attestation. This continuation uses Codex with delegated research, design and review under the latest user authorization; exact serving model identifiers are not exposed by the tools.',
    'planned_agent_hours': 4,
    'actual_productive_agent_hours': None,
    'research_verdict': status.get('research_verdict', 'narrow'),
    'verification_scope': 'Document structure and evidence references only; no product or clinical tests.',
    'unresolved_dependencies': [
        'Entrant eligibility, team and guardian conditions remain unconfirmed.',
        'Organizer deadline, video and code PDF clarification remains pending; draft not sent.',
        'No adult interviews, usability observations or clinical review performed.',
        'Competitor descriptions are claims; behavior and full revision-to-rehearsal coverage untested.',
        'Day 3 PDF anchors, model schema and revision feasibility are not run.',
        'Independent human review and eventual evaluation access remain pending.'
    ],
    'counts': {
        'required_artifacts_present': sum((DAY / n).exists() and (DAY / n).stat().st_size > 0 for n in REQUIRED if n != 'status.json') + 1,
        'source_records': len(sources),
        'retrieved_source_records': sum(s.get('status') == 'retrieved' for s in sources),
        'search_records': len(queries),
        'competitor_rows': len(matrix),
        'distinct_retrieved_products': len(products),
        'baseline_rows': sum(r['evidence_level'] == 'design_baseline' for r in matrix),
        'interaction_criteria': len(criteria),
        'storyboard_beats': len(beats),
        'storyboard_seconds': sum(beats)
    }
})
p.write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps(status['counts'], indent=2))
