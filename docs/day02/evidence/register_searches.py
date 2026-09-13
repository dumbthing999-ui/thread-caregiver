"""Register observed search calls, without treating snippets as direct pages."""
import json,datetime
from pathlib import Path
p=Path(__file__).resolve().parent
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
queries=[
('Q01','caregiver care plan changes acknowledgement invalidation revision teach back software',5,'exa',['S04','S05','S20','S21'],'Plan versioning and task publication leads; two primary pages subsequently 403.'),
('Q02','EHRTutor discharge education teach back caregiver',5,'exa',['S03'],'EHRTutor paper discovered; no outcome claims adopted.'),
('Q03','family caregiver coordination shared tasks calendar Lotsa Helping Hands ianacare',4,'exa',['S06','S07'],'Family calendar/task alternatives.'),
('Q04','"care plan" "acknowledgement" "changes" software',4,'parallel',['S08','S09'],'Competitive counterevidence: staff sign-off and update prompts.'),
('Q05','"caregiver" "invalidate" "acknowledgement"',3,'exa',[],'Off-topic emotional invalidation results; no market absence inference. Broadened terms via Q04 and Q06.'),
('Q06','patient education revision changes targeted teach back software discharge',4,'exa',['S10','S01'],'MayaRED change-focused teaching is strong counterevidence.')]
with (p/'search-log.jsonl').open('a') as f:
 for sid,q,n,backend,ids,note in queries:
  f.write(json.dumps(dict(id=sid,query=q,recorded_at=now,retrieval_method='web_search',status='success_via_fallback',served_by=backend,backend_limitation='ddgs package missing; automatic public search fallback used',returned_results=n,source_ids=ids,coverage_note=note))+'\n')
with (p/'sources.jsonl').open('a') as f:
 for sid,url,title,excerpt in [
 ('S20','https://alayacare.com/care-planning/','Care Planning | AlayaCare','Update plans at reassessment, keep a full version history for audits, and report on goals and outcomes to show client progress over time.'),
 ('S21','https://support.alisonline.com/hc/en-us/articles/4411800089741-How-to-Add-or-Review-a-Care-Plan','How to Add or Review a Care Plan','This updates the resident\'s Active Care Plan and pushes the new tasks to the Care Tracking lists for your caregivers.')]:
  f.write(json.dumps(dict(id=sid,url=url,title=title,fetched_at=now,timestamp_note='Registration clock immediately after search batches; exact provider fetch time unavailable',retrieval_method='web_search result excerpt',status='snippet-only',source_class='primary_site_search_snippet',excerpts=[excerpt]))+'\n')
 f.write(json.dumps(dict(id='S00',url='https://www.corti.ai/agents/patient-discharge-education-agent',title='Initial extraction route failure (also requested Saana)',fetched_at=now,retrieval_method='web_extract',status='failed',source_class='retrieval_diagnostic',excerpts=[],error='DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content.'))+'\n')
print('Registered six observed queries and three source/route records.')
