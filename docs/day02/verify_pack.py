"""Day 2 structural/evidence checks, stdlib only; no product validation."""
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DAY = ROOT / 'docs/day02'
REQUIRED = ['research-brief.md', 'competitor-matrix.csv', 'competitor-analysis.md',
            '../decisions/ADR-002-differentiation-gate.md', 'caregiver-workflow.md',
            'storyboard.md', 'interaction-acceptance.csv', 'day03-handoff.md',
            'review.md', 'status.json', 'evidence/sources.jsonl', 'evidence/search-log.jsonl']
errors = []
def check(condition, message):
    if not condition:
        errors.append(message)
def read_jsonl(name):
    records = []
    path = DAY / name
    if not path.exists():
        return records
    for number, line in enumerate(path.read_text().splitlines(), 1):
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError('record must be an object')
            records.append(value)
        except (ValueError, TypeError) as exc:
            errors.append(f'{name}:{number}: {exc}')
    return records

def read_csv(name, header):
    path = DAY / name
    if not path.exists():
        return []
    try:
        with path.open(newline='') as handle:
            reader = csv.DictReader(handle, strict=True)
            check(reader.fieldnames == header, f'{name}: header mismatch')
            rows = list(reader)
        for number, row in enumerate(rows, 2):
            check(None not in row and all(isinstance(v, str) and v.strip() for v in row.values()),
                  f'{name}:{number}: empty cell or inconsistent width')
        ids = [r.get('id') for r in rows]
        check(len(ids) == len(set(ids)), f'{name}: duplicate IDs')
        return rows
    except (csv.Error, OSError) as exc:
        errors.append(f'{name}: {exc}')
        return []

present = sum((DAY / name).is_file() and (DAY / name).stat().st_size > 0 for name in REQUIRED)
print(f'Required artifacts: {present}/{len(REQUIRED)} present and nonempty')
for name in REQUIRED:
    check((DAY / name).is_file() and (DAY / name).stat().st_size > 0, f'MISSING/EMPTY: {name}')
sources = read_jsonl('evidence/sources.jsonl')
ids = [r.get('id') for r in sources]
check(len(ids) == len(set(ids)), 'Duplicate source IDs')
by_id = {r.get('id'): r for r in sources}
for source in sources:
    sid = source.get('id')
    for key in ('id', 'url', 'fetched_at', 'retrieval_method', 'status', 'source_class'):
        check(bool(source.get(key)), f'{sid}: missing {key}')
    check(urlsplit(str(source.get('url', ''))).scheme in ('http', 'https'), f'{sid}: invalid URL scheme')
    try:
        timestamp = datetime.fromisoformat(source.get('fetched_at', '').replace('Z', '+00:00'))
        check(timestamp.tzinfo is not None, f'{sid}: timestamp needs timezone')
    except ValueError:
        errors.append(f'{sid}: invalid timestamp')
    if source.get('status') == 'retrieved':
        check(bool(source.get('title')) and isinstance(source.get('excerpts'), list) and
              any(str(x).strip() for x in source.get('excerpts', [])), f'{sid}: empty retrieved evidence')
retrieved = sum(r.get('status') == 'retrieved' for r in sources)
print(f'Source ledger: {len(sources)} records; {retrieved} retrieved; {len(sources)-retrieved} other outcomes')
queries = read_jsonl('evidence/search-log.jsonl')
check(len(queries) > 0, 'No search coverage recorded')
query_ids = [r.get('id') for r in queries]
check(len(query_ids) == len(set(query_ids)), 'Duplicate search IDs')
for query in queries:
    for key in ('id', 'query', 'recorded_at', 'retrieval_method', 'status', 'coverage_note'):
        check(bool(query.get(key)), f"Search {query.get('id')}: missing {key}")
    check(isinstance(query.get('source_ids'), list), f"Search {query.get('id')}: source_ids must be a list")
    for sid in query.get('source_ids', []):
        check(sid in by_id, f"Search {query.get('id')}: unknown source {sid}")
print(f'Search log: {len(queries)} records')

matrix_header = ['id','name','category','primary_user','source_grounding','revision_handling',
                 'acknowledgement_invalidation','targeted_rehearsal','caregiver_coordination',
                 'evidence_ids','evidence_level','limitations']
matrix = read_csv('competitor-matrix.csv', matrix_header)
source_pattern = r'\bS\d+\b'
products = set()
baselines = 0
for row in matrix:
    baseline = row.get('evidence_level') == 'design_baseline'
    cited = set(re.findall(source_pattern, row.get('evidence_ids') or ''))
    if baseline:
        baselines += 1
    else:
        check(bool(cited), f"{row.get('id')}: no product evidence")
        good = [by_id[s] for s in cited if s in by_id and by_id[s].get('status') == 'retrieved'
                and by_id[s].get('source_class', '').startswith('primary')]
        if good:
            products.add(row.get('name', '').strip().casefold())
        else:
            check(False, f"{row.get('id')}: no retrieved primary evidence")
    for sid in cited:
        check(sid in by_id, f"{row.get('id')}: unknown source {sid}")
    for column in matrix_header[4:9]:
        cell = row.get(column) or ''
        refs = set(re.findall(source_pattern, cell))
        check(baseline or bool(refs), f"{row.get('id')}/{column}: missing per-cell evidence reference")
        check(refs <= cited, f"{row.get('id')}/{column}: reference absent from evidence_ids")
        check(bool(re.search(r'advertised|documented|not_documented|unknown|design_baseline', cell)),
              f"{row.get('id')}/{column}: missing evidence qualifier")
check(len(products) >= 6, 'INCOMPLETE: fewer than six distinct products with retrieved primary evidence')
check(baselines >= 1, 'INCOMPLETE: plain-document/shared-checklist baseline missing')
print(f'Competitor matrix: {len(matrix)} rows; {len(products)} distinct evidenced products; {baselines} baseline')

scope = (ROOT / 'docs/day01/scope-and-acceptance.md').read_text()
valid_refs = set(re.findall(r'^\| ((?:FR|INV)-\d+) \|', scope, re.M))
interaction_header = ['id','criterion','fr_ids','inv_ids','edge_case','evidence_required','status']
criteria = read_csv('interaction-acceptance.csv', interaction_header)
check(len(criteria) >= 18, 'Interaction coverage: fewer than 18 criteria')
for row in criteria:
    check(row.get('status') == 'NOT_IMPLEMENTED', f"{row.get('id')}: implementation status must remain NOT_IMPLEMENTED")
    for field, prefix in [('fr_ids', 'FR'), ('inv_ids', 'INV')]:
        refs = set(re.findall(rf'{prefix}-\d+', row.get(field) or ''))
        check(bool(refs) and refs <= valid_refs, f"{row.get('id')}: invalid or missing {field}")
print(f'Interaction criteria: {len(criteria)} records; future obligations only')

markdown = [DAY / name for name in REQUIRED if name.endswith('.md') and (DAY / name).exists()]
markdown.append(ROOT / 'README.md')
link_count = 0
for path in markdown:
    body = path.read_text()
    for ref in re.findall(r'\b(?:FR|INV)-\d+\b', body):
        check(ref in valid_refs, f'{path.name}: unknown requirement {ref}')
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', body):
        parsed = urlsplit(target.strip('<>'))
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        link_count += 1
        check((path.parent / unquote(parsed.path)).resolve().exists(), f'{path.name}: broken local link {target}')
print(f'Local Markdown file links: {link_count} checked')

beats = []
if (DAY / 'storyboard.md').exists():
    for line in (DAY / 'storyboard.md').read_text().splitlines():
        cells = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(cells) == 5 and cells[2].isdigit() and cells[3].isdigit():
            beats.append((cells[1], int(cells[2]), int(cells[3])))
position = 0
for act, start, duration in beats:
    check(start == position and duration > 0, f'Storyboard gap/overlap or invalid duration at {start}')
    position = start + duration
check(bool(beats) and position == 180, 'Storyboard must cover exactly 180 contiguous seconds')
check(len({x[0] for x in beats}) == 3, 'Storyboard must have three acts')
print(f'Storyboard: {len(beats)} timed beats; {sum(x[2] for x in beats)} seconds')

if (DAY / 'status.json').exists():
    try:
        status = json.loads((DAY / 'status.json').read_text())
        expected = dict(required_artifacts_present=present, source_records=len(sources),
                        retrieved_source_records=retrieved, search_records=len(queries),
                        competitor_rows=len(matrix), distinct_retrieved_products=len(products),
                        baseline_rows=baselines, interaction_criteria=len(criteria),
                        storyboard_beats=len(beats), storyboard_seconds=sum(x[2] for x in beats))
        check(status.get('counts') == expected, 'status.json: counts do not match actual files')
        check(status.get('planned_agent_hours') == 4, 'status.json: planned budget mismatch')
        check(status.get('actual_productive_agent_hours') is None, 'status.json: no measured productive hours available')
        check(status.get('research_verdict') in ('go','narrow','pivot'), 'status.json: missing research verdict')
    except (ValueError, TypeError) as exc:
        errors.append(f'status.json: {exc}')
for error in errors:
    print('ERROR: ' + error)
print('Overall: ' + ('INCOMPLETE' if errors else 'PASS (document structure and evidence references only)'))
raise SystemExit(bool(errors))
