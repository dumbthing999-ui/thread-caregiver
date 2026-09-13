"""Bounded public HTTP retrieval; no credentials, full pages not persisted."""
import json,re,sys,urllib.request,datetime,concurrent.futures
from html.parser import HTMLParser
from pathlib import Path
ROOT=Path(__file__).resolve().parent
class Text(HTMLParser):
 def __init__(self): super().__init__(); self.parts=[]; self.skip=0
 def handle_starttag(self,t,a):
  if t in ('script','style','noscript'): self.skip+=1
 def handle_endtag(self,t):
  if t in ('script','style','noscript'): self.skip=max(0,self.skip-1)
 def handle_data(self,d):
  if not self.skip and d.strip(): self.parts.append(re.sub(r'\s+',' ',d.strip()))
def fetch(item):
 sid,url,cls=item; now=datetime.datetime.now(datetime.timezone.utc).isoformat()
 r=dict(id=sid,url=url,title='',fetched_at=now,retrieval_method='stdlib urllib HTTP GET + HTMLParser',status='failed',source_class=cls,excerpts=[])
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=35) as f:
   html=f.read(1500000).decode('utf-8',errors='replace');r['http_status']=f.status;r['final_url']=f.url
  p=Text();p.feed(html)
  title=re.search(r'<title[^>]*>(.*?)</title>',html,re.S|re.I);r['title']=re.sub('<[^>]+>','',title.group(1)).strip() if title else url
  hits=[s for s in p.parts if re.search(r'acknow|revis|version|chang|contradic|source|quiz|teach.back|checklist|task|caregiver|discharge|question|calendar|assign',s,re.I) and 25<len(s)<900]
  r['excerpts']=list(dict.fromkeys(hits))[:22];r['status']='retrieved' if r['excerpts'] else 'no_relevant_text'
 except Exception as e:r['error']=str(e)
 return r
if __name__=='__main__':
 items=json.loads(sys.argv[1])
 with (ROOT/'sources.jsonl').open('a') as f:
  for r in concurrent.futures.ThreadPoolExecutor(max_workers=5).map(fetch,items):
   f.write(json.dumps(r,ensure_ascii=False)+'\n');f.flush();print(json.dumps(r,ensure_ascii=False))
