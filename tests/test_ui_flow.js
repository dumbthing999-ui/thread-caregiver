// Controller integration tests with a minimal DOM adapter and a real isolated HTTP service.
// These exercise the shipped UI script, not browser layout or accessibility conformance.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {spawn} = require('node:child_process');
const {once} = require('node:events');
const path = require('node:path');
const root = path.resolve(__dirname, '..');

async function run() {
  const server = spawn('python3', ['-u', '-c', "from app.server import run_server; s=run_server(port=0); print('TEST_PORT:'+str(s.server_port), flush=True); s.serve_forever()"], {cwd:root, env:{...process.env, PYTHONDONTWRITEBYTECODE:'1'}, stdio:['ignore','pipe','pipe']});
  let logs='';server.stderr.on('data', d=>{logs+=d.toString();});
  try {
    const port = await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(new Error('Test server did not start')),10000);
      server.on('error',reject); server.stdout.on('data',chunk=>{const match=String(chunk).match(/TEST_PORT:(\d+)/);if(match){clearTimeout(timer);resolve(Number(match[1]));}});
    });
    const origin=`http://127.0.0.1:${port}`;
    const html=await (await fetch(origin)).text();
    class Element {
      constructor(id){this.id=id;this.textContent='';this.innerHTML='';this.disabled=false;this.hidden=false;this.open=false;this.children=[];this.classList={toggle(){}};}
      setAttribute(k,v){this[k]=v;} removeAttribute(k){delete this[k];} addEventListener(){}
      focus(){document.activeElement=this;} showModal(){this.open=true;} close(){this.open=false;}
      append(){} click(){} remove(){}
    }
    const elements=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element(m[1])]));
    elements.get('progress').children=Array.from({length:4},()=>new Element('step'));
    const classes=new Map(['.appointment','.transport'].map(x=>[x,new Element(x)]));
    const dialogs=[...elements.values()].filter(x=>x.id.endsWith('Dialog'));
    const document={activeElement:null,body:new Element('body'),getElementById:id=>{assert.ok(elements.has(id),`UI references missing element ${id}`);return elements.get(id);},querySelector:selector=>selector==='dialog[open]'?dialogs.find(d=>d.open):classes.get(selector),querySelectorAll:()=>dialogs,addEventListener(){},createElement:()=>new Element('created')};
    let failNext=false;
    const context=vm.createContext({document,window:{addEventListener(){}},console,Blob,URL,setTimeout,fetch:async(url,opts)=>{if(failNext){failNext=false;throw new Error('simulated disconnect');}return fetch(origin+url,opts);}});
    vm.runInContext(fs.readFileSync(path.join(root,'app/ui.js'),'utf8'),context);
    const call=code=>vm.runInContext(code,context);
    const action=name=>call(`dispatch(${JSON.stringify(name)})`);
    const get=id=>elements.get(id);

    assert.match(get('nextAction').textContent,/Create a local handoff/);
    await action('next');
    assert.equal(get('createDialog').open,true,'The default entry point must be a user handoff, not the scripted demo');
    await action('close');
    assert.equal(call('state.phase'),0);
    await action('demo');
    assert.match(get('modeTag').textContent,/Judge demo/);
    await action('next');await action('close');
    assert.equal(call('state.phase'),1);
    const cid=call('state.main.id');
    let snapshot=await (await fetch(origin+`/api/v1/cases/${cid}`)).json();
    assert.equal(snapshot.documents.length,1,'Opening source must not silently import replacement');
    await action('next'); // actual source review
    await action('source');
    assert.match(get('sourceText').innerHTML,/<mark>Follow-up appointment: Thursday at 10:00\.<\/mark>/);
    await action('close');
    await action('next'); // owner
    assert.equal(call('state.phase'),3);
    snapshot=await (await fetch(origin+`/api/v1/cases/${cid}`)).json();
    assert.equal(snapshot.acknowledgements.length,0,'Ownership must not silently acknowledge');
    await action('next'); // acknowledge
    assert.equal(call('state.phase'),4);
    assert.match(get('taskState').textContent,/Wording reviewed/);
    await action('retry');
    assert.match(get('checkResults').innerHTML,/No duplicate event/);
    await action('next'); // compare imports new note
    assert.equal(call('state.phase'),5);
    snapshot=await (await fetch(origin+`/api/v1/cases/${cid}`)).json();
    assert.equal(snapshot.links.length,0,'Adding new note must not link replacement');
    await action('next'); // confirmation dialog, no mutation
    assert.equal(get('confirmDialog').open,true);
    await action('close');
    assert.equal(call('state.phase'),5,'Cancelled confirmation must not advance');
    await action('next');await action('confirm');
    assert.equal(call('state.phase'),6);
    assert.match(get('taskState').textContent,/Needs re-review/);
    const before=call('state.main.history.length');
    await action('stale');
    assert.equal(call('state.main.history.length'),before);
    assert.match(get('checkResults').innerHTML,/STALE_REVISION_ERROR/);
    await action('next');
    assert.equal(call('state.phase'),7);
    assert.match(get('ackStatus').textContent,/Updated wording acknowledged/);
    snapshot=await (await fetch(origin+`/api/v1/cases/${cid}`)).json();
    assert.equal(snapshot.acknowledgements.length,2);
    assert.equal(Object.values(snapshot.task_projections).filter(p=>p.validity==='STALE').length,1);
    const exported=await (await fetch(origin+`/api/v1/cases/${cid}/export`)).json();
    assert.equal(exported.execution_mode,'ROLE_SIMULATION');
    await action('conflict');
    assert.equal(call('state.view'),'conflict');
    assert.notEqual(call('state.conflict.id'),cid);
    assert.match(get('conflictA').textContent,/Wednesday at 11:00/);
    assert.match(get('conflictB').textContent,/Thursday at 15:30/);
    await action('return');
    assert.equal(call('state.main.id'),cid);
    assert.equal(call('state.phase'),7);
    failNext=true;await action('retry');
    assert.equal(call('state.connected'),false);
    assert.equal(get('nextAction').disabled,true);
    assert.match(get('notice').textContent,/Cannot reach/);
    await action('reconnect');
    assert.equal(call('state.connected'),true);
    assert.equal(call('state.phase'),7,'Network errors must not advance workflow');
    // Source and event text must never be interpolated as active markup.
    assert.equal(call('esc("<img src=x onerror=alert(1)>")'),'&lt;img src=x onerror=alert(1)&gt;');
    await action('reset');await action('close');
    assert.equal((await fetch(origin+`/api/v1/cases/${cid}`)).status,200);
    await action('reset');await action('confirm');
    assert.equal(call('state.phase'),0);
    assert.equal((await fetch(origin+`/api/v1/cases/${cid}`)).status,404);
    assert.equal((await fetch(origin+`/api/v1/cases/${call('state.conflict.id')}`)).status,200);
    console.log('PASS: guided UI controller against real HTTP service; source inspection, separate ownership/acknowledgement, explicit replacement, stale rejection, exact retry, updated review, isolated conflict, offline recovery, safe text and scoped reset.');
  } catch(error) {console.error(logs);throw error;}
  finally {server.kill('SIGTERM');await once(server,'exit');}
}
run().catch(error=>{console.error(error);process.exitCode=1;});
