'use strict';
// UI state is kept per tab; service-issued case/document IDs never reuse the shared demo fixtures.
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const quoteOf = doc => doc?.text.split(/\r?\n/).find(line => line.startsWith('Follow-up appointment:')) || '';
const timeOf = doc => quoteOf(doc).replace(/^Follow-up appointment:\s*/, '').replace(/\.$/, '');
const state = {phase:0, busy:false, connected:true, main:null, conflict:null, view:'main', confirmation:null, returnFocus:null, checks:[]};
const active = () => state.view === 'conflict' ? state.conflict : state.main;
const messages = [
  ['START WITH THE SOURCE','A handoff starts with a shared understanding.','Meet Morgan, helping Pat arrange transport. Open the fictional note, then see what happens when the appointment changes.','Open fictional example','You control each step. Nothing runs automatically.'],
  ['01 · READ THE ORIGINAL','First, see the wording behind the task.','The appointment is quoted directly from the fictional note. Open the source to see it in context, then record your review.','I’ve reviewed this source','Review records the wording you saw. It is not clinical approval.'],
  ['02 · SHARE THE RESPONSIBILITY','Make it clear who is arranging the ride.','Take responsibility as Morgan. This assigns the transport task; it does not mark a ride as arranged.','I’ll arrange transport','You are acting as a simulated caregiver in this local demo.'],
  ['02 · RECORD YOUR REVIEW','Responsibility and review are separate.','You own the transport task. Acknowledge the exact wording you reviewed so the handoff records which source it depends on.','Acknowledge this wording','An acknowledgement is not task completion.'],
  ['03 · A NEW NOTE ARRIVES','What happens when the appointment changes?','Add the fictional update and compare it with the earlier note. Adding a note does not automatically make it authoritative.','Compare the new note','The earlier acknowledgement stays tied to the original source.'],
  ['03 · CHECK THE RELATIONSHIP','Is this intended to replace the earlier note?','Compare both quotations below. Only record a replacement if that is the claimed relationship; a later upload alone is not enough.','Record claimed replacement','A claimed replacement does not authenticate the source or its author.'],
  ['04 · RE-REVIEW NEEDED','The old acknowledgement is no longer current.','The source changed. Review the new wording and reconfirm transport responsibility before acknowledging the updated handoff.','Review and acknowledge update','Whole-document re-review: unchanged content may need review too.'],
  ['HANDOFF UPDATED','The review now points to the updated wording.','Morgan has acknowledged the new source. The earlier acknowledgement is still in history and remains stale. Transport has not been marked completed.','View the recorded history','Explore the evidence below to test old writes and duplicate requests.']
];
const eventLabels = {SOURCE_ADDED:'Source note added',REVIEW_RECORDED:'Source wording reviewed',TASK_CREATED:'Coordination task created',OWNER_CONFIRMED:'Morgan took responsibility',ACKNOWLEDGED:'Wording acknowledged',REPLACEMENT_LINKED:'Claimed replacement recorded',INVALIDATED:'Earlier review needs updating',COMPLETED:'Coordination task completed',ISSUE_OPENED:'Conflicting wording flagged',REHEARSAL_CREATED:'Source practice created',REHEARSAL_ATTEMPTED:'Source practice recorded'};

async function request(path, {method='GET', body, headers={}, expect}={}) {
  let response;
  try {response = await fetch(path, {method, headers:{'Content-Type':'application/json', ...headers}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});}
  catch {state.connected=false; throw new Error('Cannot reach the local service. Your last view may be out of date. Reconnect before continuing.');}
  const data = await response.json();
  if (expect) {
    if(response.status !== expect.status || data.error?.code !== expect.code) throw new Error(`The service check did not return ${expect.code}. No successful protection check was recorded.`);
  } else if(!response.ok) {
    const error = new Error(data.error?.message || data.error || 'The request was not accepted.');
    error.code=data.error?.code; throw error;
  }
  state.connected=true;
  return data;
}
async function post(ctx, suffix, body, headers={}) {
  const data = await request(`/api/v1/cases/${encodeURIComponent(ctx.id)}${suffix}`, {method:'POST', body, headers});
  if(data.etag) ctx.etag=data.etag;
  return data;
}
async function sync(ctx) {
  ctx.snapshot=await request(`/api/v1/cases/${encodeURIComponent(ctx.id)}`);
  ctx.etag=ctx.snapshot.etag;
  ctx.history=(await request(`/api/v1/cases/${encodeURIComponent(ctx.id)}/history`)).events;
}
function notify(message, type='success') {
  $('notice').textContent=message; $('notice').className=`notice ${type}`; $('notice').hidden=false;
}
function modal(id) {state.returnFocus=document.activeElement; $(id).showModal();}
function closeModal() {const dialog=document.querySelector('dialog[open]'); if(dialog) dialog.close(); state.returnFocus?.focus();}
function render() {
  const ctx=active(); const m=state.main; const phase=state.phase; const conflict=state.view==='conflict';
  const next=messages[phase];
  $('nextEyebrow').textContent=conflict?'SEPARATE FICTIONAL EXAMPLE':next[0];
  $('nextTitle').textContent=conflict?'When sources disagree, leave the question open.':next[1];
  $('nextDescription').textContent=conflict?'Both notes remain visible. The next step is a neutral clarification question, not choosing an appointment.':next[2];
  $('nextAction').textContent=state.busy?'Working…':conflict?'Return to the handoff':next[3]+' →';
  $('nextFoot').textContent=conflict?'No appointment is selected and no message is sent.':next[4];
  const step=phase<2?0:phase<4?1:phase<6?2:3;
  $('stepLabel').textContent=conflict?'CONFLICT CONTROL':`0${step+1} / 04`;
  [...$('progress').children].forEach((li,i)=>{li.removeAttribute('aria-current'); li.className=i<step?'done':''; if(i===step)li.setAttribute('aria-current','step');});
  $('nextAction').disabled=state.busy||!state.connected;
  $('sourceButton').disabled=!m||state.busy;
  $('historyButton').disabled=!ctx;
  $('exportButton').disabled=!ctx||state.busy||!state.connected;
  $('resetButton').disabled=!ctx||state.busy||!state.connected;
  $('staleButton').disabled=!m?.linked||state.busy||!state.connected||conflict;
  $('retryButton').disabled=!m?.ack||state.busy||!state.connected||conflict;
  $('conflictButton').disabled=state.busy||!state.connected;
  document.body.classList.toggle('busy',state.busy);
  $('offline').hidden=state.connected;
  $('connectionStatus').textContent=!state.connected?'Offline · Saved view may be out of date':ctx?'Local service connected · Roles simulated':'Local demo · Open an example to connect';
  const currentDoc=m?.linked?m.doc2:m?.doc1;
  $('appointmentTime').textContent=currentDoc?timeOf(currentDoc):'Your source, in context.';
  $('appointmentCaption').textContent=currentDoc?'Fictional follow-up · Transport coordination only':'Open the fictional example to inspect its exact wording.';
  $('appointmentQuote').hidden=!currentDoc; $('appointmentQuote').textContent=quoteOf(currentDoc);
  $('sourceCaption').textContent=currentDoc?`${currentDoc.filename} · ${currentDoc.source_version}`:'Original wording stays inspectable.';
  $('sourceState').textContent=!m?'Example not opened':m.linked?'Claimed replacement':m.review?'Exact quote reviewed':'Original note';
  $('sourceState').className='pill '+(m?.review?'green':'neutral');
  $('changeCard').hidden=!m?.doc2||conflict;
  if(m?.doc2){$('oldTime').textContent=timeOf(m.doc1);$('newTime').textContent=timeOf(m.doc2);$('oldQuote').textContent=quoteOf(m.doc1);$('newQuote').textContent=quoteOf(m.doc2);$('changeState').textContent=m.linked?'Replacement linked':'Not linked yet';$('changeExplanation').textContent=m.linked?'Whole-document re-review is required. Earlier acknowledgements are preserved as history, not carried forward.':'A later upload does not automatically replace the earlier note. Record the claimed relationship explicitly.';}
  const task=m?.updatedTask||m?.task; const projection=task&&m.snapshot?.task_projections[task.task_id];
  const owned=!!projection?.assigned_actor_id;
  const stale=projection?.validity==='STALE';
  $('taskState').textContent=stale?'Needs re-review':projection?.status==='ACKNOWLEDGED'?'Wording reviewed':owned?'Morgan owns this':'Not assigned';
  $('taskState').className='pill '+(stale?'amber':owned?'green':'neutral');
  $('ownerAvatar').textContent=owned?'M':'?'; $('ownerName').textContent=owned?'Morgan · Transport coordinator':'No one assigned yet';
  $('ownerDescription').textContent=stale?'Previous responsibility is tied to the earlier note.':owned?'Responsible for arranging transport. Not marked complete.':'Review the source before taking responsibility.';
  $('ackStatus').className='review-status'+(stale?' stale':'');
  $('ackStatus').textContent=stale?'Earlier acknowledgement: needs re-review. Its original event is still in history.':m?.updatedAck?'Updated wording acknowledged. The earlier acknowledgement remains historical.':m?.ack?'Morgan acknowledged the original wording. This does not mean the ride is arranged.':'Acknowledgement is separate from arranging the ride.';
  $('conflictCard').hidden=!conflict;
  document.querySelector('.appointment').hidden=conflict; document.querySelector('.transport').hidden=conflict;
  if(conflict){$('conflictA').textContent=quoteOf(ctx.doc_a);$('conflictB').textContent=quoteOf(ctx.doc_b);$('conflictQuestion').textContent=ctx.issue.question_template;}
  const history=ctx?.history||[];
  $('eventCount').textContent=history.length;
  $('activity').innerHTML=history.length?history.slice(-4).reverse().map(e=>`<li>${esc(eventLabels[e.event_type]||e.event_type)}<small>${esc(e.actor_id)} · Event ${esc(e.case_sequence)}</small></li>`).join(''):'<li class="empty-activity">Your first action will appear here. Earlier events stay in history when a source changes.</li>';
  $('checkResults').innerHTML=state.checks.length?state.checks.map(message=>`<li>${esc(message)}</li>`).join(''):'<li>No service checks run yet.</li>';
}
function showSource(doc) {
  if(!doc)return;
  const ctx=active();
  const span=ctx?.snapshot?.spans.find(s=>s.document_id===doc.document_id && s.exact_quote===quoteOf(doc));
  $('sourceDialogTitle').textContent=doc.filename;
  $('sourceMeta').textContent=`Source ${doc.source_version} · ${doc.document_id}${span?` · Characters ${span.start_char}–${span.end_char} (end exclusive)`: ' · Not yet reviewed'}`;
  // Server offsets count Unicode code points, not JavaScript UTF-16 code units.
  const chars=Array.from(doc.text);
  $('sourceText').innerHTML=span?esc(chars.slice(0,span.start_char).join(''))+'<mark>'+esc(span.exact_quote)+'</mark>'+esc(chars.slice(span.end_char).join('')):esc(doc.text);
  modal('sourceDialog');
}
function showHistory() {
  const ctx=active(); if(!ctx)return;
  $('fullHistory').innerHTML=(ctx.history||[]).map(e=>`<article class="history-event"><strong>${esc(eventLabels[e.event_type]||e.event_type)}</strong><p>${esc(e.actor_id)} · ${esc(e.created_at)} · Event ${esc(e.case_sequence)}</p><details><summary>Inspect recorded event</summary><pre>${esc(JSON.stringify(e,null,2))}</pre></details></article>`).join('')||'<p>No events recorded yet.</p>';
  modal('historyDialog');
}
async function review(ctx, doc) {
  return post(ctx,'/source-reviews',{document_id:doc.document_id,expected_source_version:doc.source_version,category:'APPOINTMENT_QUOTE',field_name:'appointment_wording',exact_quote:quoteOf(doc),actor_id:'Morgan'});
}
async function createTransport(ctx,instruction) {
  return (await post(ctx,'/tasks',{task_type:'ARRANGE_TRANSPORT',instruction_id:instruction.instruction_id,description:'Arrange transport for the quoted appointment.',actor_id:'Morgan'})).task;
}
async function takeOwnership(ctx,task) {await post(ctx,`/tasks/${task.task_id}/owner`,{expected_task_revision:task.task_revision,actor_id:'Morgan'});}
async function acknowledge(ctx,task,key) {return post(ctx,'/acknowledgements',{task_id:task.task_id,expected_task_revision:task.task_revision,actor_id:'Morgan'},{'If-Match':ctx.etag,'Idempotency-Key':key});}
async function nextStep() {
  if(state.view==='conflict'){state.view='main';return;}
  const m=state.main;
  switch(state.phase){
    case 0: {
      // Retain IDs after each accepted step so a later error does not restart a shared case.
      if(!state.main){const result=await request('/api/v1/sessions',{method:'POST',body:{fictional_only:true}});state.main={id:result.case_id,etag:result.etag,history:[]};}
      const ctx=state.main;
      if(!ctx.doc1){const fixture=await request('/api/v1/fixtures/s01_v1.txt');ctx.doc1=(await post(ctx,'/documents',{filename:'Original note.txt',text:fixture.content,actor_id:'Morgan'})).document;}
      await sync(ctx);state.phase=1;showSource(ctx.doc1);break;
    }
    case 1: if(!m.review)m.review=await review(m,m.doc1);await sync(m);state.phase=2;notify('The exact source wording is recorded. You can now take responsibility for transport.');break;
    case 2: if(!m.task)m.task=await createTransport(m,m.review.instruction);await takeOwnership(m,m.task);await sync(m);state.phase=3;notify('Transport responsibility assigned to Morgan. Acknowledgement is the next, separate action.');break;
    case 3: if(!m.ack)m.ack=await acknowledge(m,m.task,'original-ack-01');await sync(m);state.phase=4;notify('Original wording acknowledged. This is a review event, not a completed transport arrangement.');break;
    case 4: if(!m.doc2){const fixture=await request('/api/v1/fixtures/s01_v2.txt');m.doc2=(await post(m,'/documents',{filename:'Updated note.txt',text:fixture.content,actor_id:'Morgan'})).document;}await sync(m);state.phase=5;notify('New note added for comparison. No replacement relationship has been recorded.','warning');break;
    case 5: state.confirmation='replacement';$('confirmTitle').textContent='Record a claimed replacement?';$('confirmDescription').textContent=`This will link “${m.doc2.filename}” as replacing “${m.doc1.filename}”. The earlier review will need updating. This records your claim; it does not authenticate a clinician or resolve other conflicting sources.`;$('confirmAction').textContent='Record replacement';modal('confirmDialog');break;
    case 6: if(!m.updatedReview)m.updatedReview=await review(m,m.doc2);if(!m.updatedTask)m.updatedTask=await createTransport(m,m.updatedReview.instruction);await takeOwnership(m,m.updatedTask);if(!m.updatedAck)m.updatedAck=await acknowledge(m,m.updatedTask,'updated-ack-01');await sync(m);state.phase=7;notify('Updated wording acknowledged. The old review remains in the history.');break;
    case 7: showHistory();break;
  }
}
async function confirmAction() {
  const kind=state.confirmation;state.confirmation=null;closeModal();
  if(kind==='replacement'){
    const m=state.main;
    if(!m.linked){m.linked=await post(m,'/replacement-links',{prior_document_id:m.doc1.document_id,new_document_id:m.doc2.document_id,expected_prior_source_version:m.doc1.source_version,expected_new_source_version:m.doc2.source_version,actor_id:'Morgan'},{'If-Match':m.etag});}
    await sync(m);state.phase=6;notify('Replacement recorded. The previous acknowledgement is now stale; its history is preserved.','warning');
  }else if(kind==='reset'){
    const ctx=active();await post(ctx,'/reset',{});
    if(state.view==='conflict'){state.conflict=null;state.view='main';}else{state.main=null;state.phase=0;state.checks=[];}
    notify('This example was reset. Other cases were not changed.');
  }
}
async function testStale() {
  const m=state.main;await sync(m);const before=m.history.length;
  await request(`/api/v1/cases/${m.id}/acknowledgements`,{method:'POST',body:{task_id:m.task.task_id,expected_task_revision:m.task.task_revision,actor_id:'Morgan'},headers:{'If-Match':m.etag,'Idempotency-Key':'stale-check-01'},expect:{status:409,code:'STALE_REVISION_ERROR'}});
  await sync(m);if(m.history.length!==before)throw new Error('The rejected request changed the event count. The check has not passed.');
  const message='Old acknowledgement rejected: HTTP 409 STALE_REVISION_ERROR. Event count unchanged.';state.checks.push(message);notify(message);
}
async function testRetry() {
  const m=state.main;await sync(m);const before=m.history.length;
  const retry=await acknowledge(m,m.task,'original-ack-01');await sync(m);
  if(retry.acknowledgement.ack_id!==m.ack.acknowledgement.ack_id||m.history.length!==before)throw new Error('The retry did not return the same event without duplication. Check failed.');
  const message='Exact retry returned the same acknowledgement. No duplicate event was added.';state.checks.push(message);notify(message);
}
async function openConflict() {
  if(!state.conflict){const data=await request('/api/v1/demo/init-conflicting-path',{method:'POST',body:{isolated:true}});state.conflict={...data,id:data.case_id,history:[]};}
  await sync(state.conflict);state.view='conflict';notify('Separate conflict example opened. Your main handoff is preserved.','warning');
}
async function exportCase() {
  const ctx=active();const data=await request(`/api/v1/cases/${ctx.id}/export`);
  const link=document.createElement('a');const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));link.href=url;link.download=`thread-${ctx.id}.json`;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);notify('Case JSON exported with source versions, history and simulation labels.');
}
async function dispatch(action) {
  if(action==='close'){closeModal();return;}
  if(action==='about'){modal('aboutDialog');return;}
  if(action==='history'){showHistory();return;}
  if(action==='handoff'||action==='return'){state.view='main';render();$('main').focus();return;}
  if(action==='source'){showSource(state.main?.linked?state.main.doc2:state.main?.doc1);return;}
  if(action==='source-old'){showSource(state.main?.doc1);return;}
  if(action==='source-new'){showSource(state.main?.doc2);return;}
  if(action==='conflict-a'||action==='conflict-b'){showSource(action==='conflict-a'?state.conflict?.doc_a:state.conflict?.doc_b);return;}
  if(state.busy)return;
  if(action==='reset'){if(!active())return;state.confirmation='reset';$('confirmTitle').textContent='Reset this fictional example?';$('confirmDescription').textContent='This removes this example’s source notes and event history from the local service. Any JSON file you already downloaded remains on your device.';$('confirmAction').textContent='Reset example';modal('confirmDialog');return;}
  state.busy=true;render();
  try {
    if(action==='next')await nextStep();
    else if(action==='confirm')await confirmAction();
    else if(action==='stale')await testStale();
    else if(action==='retry')await testRetry();
    else if(action==='conflict')await openConflict();
    else if(action==='export')await exportCase();
    else if(action==='reconnect'){if(active())await sync(active());else await request('/api/v1/fixtures/s01_v1.txt');notify('Connected. The current service view is loaded.');}
  }catch(error){notify(error.message,'error');}
  finally{state.busy=false;render();}
}
document.addEventListener('click',event=>{const button=event.target.closest('[data-action]');if(button&&!button.disabled)dispatch(button.dataset.action);});
window.addEventListener('offline',()=>{state.connected=false;render();});
window.addEventListener('online',()=>{notify('Connection may be available again. Use Reconnect to refresh the service state.','warning');});
document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('close',()=>state.returnFocus?.focus()));
render();
