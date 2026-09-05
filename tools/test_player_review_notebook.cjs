'use strict';
const {test}=require('node:test'),assert=require('node:assert/strict');
const {create}=require('./player_review_notebook.js');
const data={inputs_hash:'abc',checks:[{check_id:1,name:'Exact name',player:{item:'Flail',region:'Limgrave',place:'Carriage'}},{check_id:2,name:'Other',player:{item:'Other',region:'Other',place:'Other'}}]};
const form={RawNotes:'First line\n"quoted", second line',Reviewed:true,Reviewer:'255'};
const notebook=()=>create(data,{indexedDB:null});
function fakeIDB(fail=false,manual=null){
 const records=new Map();return {records,open(){const req={};queueMicrotask(()=>{req.result={createObjectStore(){},transaction(){const tx={objectStore:()=>({put(value,key){const finish=()=>{if(typeof fail==='function'?fail(key):fail)tx.onabort?.();else{records.set(key,structuredClone(value));tx.oncomplete?.();}};if(manual)manual.push(finish);else queueMicrotask(finish);},getAll(){const read={};queueMicrotask(()=>{read.result=[...records.values()].map(x=>structuredClone(x));read.onsuccess();});return read;}})};return tx;},close(){}};req.onupgradeneeded();req.onsuccess();});return req;}};
}
test('IndexedDB reload retains multiline notes and reviewed state',async()=>{
 const db=fakeIDB(),a=create(data,{indexedDB:db});await a.init();await a.save(1,form);
 const b=create(data,{indexedDB:db});await b.init();assert.equal(b.get(1).RawNotes,form.RawNotes);assert.equal(b.get(1).Reviewed,true);
});
test('storage failure retains input in export and reports not durable',async()=>{
 const statuses=[],a=create(data,{indexedDB:fakeIDB(true),onStatus:s=>statuses.push(s)});await a.init();assert.equal(await a.save(1,form),false);assert.equal(a.exportNotebook().reviews[0].form.RawNotes,form.RawNotes);assert.equal(statuses.at(-1).durable,false);
});
test('full corpus backup preserves 5000 large notes without storage dependency',async()=>{
 const checks=Array.from({length:5000},(_,i)=>({check_id:i,name:'Check '+i,player:{}})),a=create({inputs_hash:'large',checks},{indexedDB:null});
 await a.init();for(const c of checks)await a.save(c.check_id,{RawNotes:'notes\n'.repeat(100)});
 const exported=a.exportNotebook();assert.equal(exported.reviews.length,5000);const b=create({inputs_hash:'large',checks},{indexedDB:null});const p=b.previewImport(JSON.stringify(exported));assert.equal(p.rows.filter(r=>r.status==='new').length,5000);await b.applyImport(p);assert.equal(b.entries.size,5000);
});
test('conflicts remain untouched until explicit replacement, including edits after preview',async()=>{
 const a=notebook();await a.save(1,form);const backup=a.exportNotebook();const b=notebook();let p=b.previewImport(backup);await b.save(1,{RawNotes:'newer'});await b.applyImport(p);assert.equal(b.get(1).RawNotes,'newer');
 p=b.previewImport(backup);assert.equal(p.rows[0].status,'conflict');await b.applyImport(p);assert.equal(b.get(1).RawNotes,'newer');await b.applyImport(p,{1:'replace'});assert.equal(b.get(1).RawNotes,form.RawNotes);
});
test('older snapshot imports preserve original record and reject different name',async()=>{
 const a=notebook();await a.save(1,form);const backup=a.exportNotebook();backup.reviews[0].catalog_hash='older';
 const b=notebook(),p=b.previewImport(backup);assert.match(p.rows[0].reason,/Older catalog/);await b.applyImport(p);assert.equal(b.exportNotebook().reviews[0].imported_from[0].catalog_hash,'older');
 backup.reviews[0].original_name='Wrong';assert.equal(b.previewImport(backup).rows[0].status,'rejected');
});
test('reject duplicate, missing identity, malformed and unknown records individually',async()=>{
 const a=notebook();await a.save(1,form);const r=a.exportNotebook().reviews[0];
 for(const record of [{...r,check_id:99},{...r,catalog_hash:null},{...r,form:{RawNotes:42}}])assert.equal(a.previewImport({schema:'er-player-notebook-v1',reviews:[record]}).rows[0].status,'rejected');
 assert.ok(a.previewImport('bad json').errors.length);
 assert.ok(a.previewImport({schema:'er-player-notebook-v1',reviews:[r,r]}).rows.every(x=>x.status==='rejected'));
});
test('legacy reports require exact catalog hash and description; support batch',async()=>{
 const a=notebook(),r={schema:'er-player-review-v1',check_id:1,catalog_hash:'abc',catalog:data.checks[0].player,finding:'I found it here',evidence:'saw it',observation_scope:'player_report_not_adjudicated'};
 const p=a.previewImport([r]);assert.equal(p.rows[0].status,'new');await a.applyImport(p);assert.equal(a.get(1).Evidence,'saw it');
 assert.equal(a.previewImport({...r,catalog_hash:'old'}).rows[0].status,'rejected');assert.equal(a.previewImport({...r,catalog:{...r.catalog,place:'Elsewhere'}}).rows[0].status,'rejected');
});
test('defaults persist; saving draft does not alter catalog source confirmation',async()=>{
 const db=fakeIDB(),a=create(data,{indexedDB:db});await a.init();await a.saveDefaults({Reviewer:'255',Version:'v1',Context:'Vanilla'});await a.save(1,form);
 const b=create(data,{indexedDB:db});await b.init();assert.equal(b.getDefaults().Reviewer,'255');assert.equal(data.checks[0].player.need,undefined);
});

test('catalog updates retain exact identities and export unmatched recovery without old backup',async()=>{
 const db=fakeIDB(),a=create(data,{indexedDB:db});await a.init();await a.save(1,form);await a.save(2,{RawNotes:'old second'});
 const changed={...data,inputs_hash:'new',checks:[data.checks[0]]},b=create(changed,{indexedDB:db});await b.init();
 assert.equal(b.get(1).RawNotes,form.RawNotes);assert.equal(b.exportNotebook().reviews[0].imported_from[0].catalog_hash,'abc');
 assert.ok(b.exportNotebook().recovery_records.some(x=>x.record.check_id===2));
 const c=create(changed,{indexedDB:null});await c.applyImport(c.previewImport(b.exportNotebook()));assert.ok(c.recoveryRecords.some(x=>x.record.check_id===2));
});
test('conflicting old catalog versions remain recoverable and are not arbitrarily selected',async()=>{
 const db=fakeIDB(),a=create(data,{indexedDB:db});await a.init();await a.save(1,{RawNotes:'one'});
 const b=create({...data,inputs_hash:'second'},{indexedDB:db});await b.init();await b.save(1,{RawNotes:'two'});
 const c=create({...data,inputs_hash:'third'},{indexedDB:db});await c.init();assert.equal(c.get(1),undefined);assert.equal(c.recoveryRecords.length,2);
 assert.equal(c.previewImport(c.exportRecoveryNotebook(0)).rows[0].status,'new');
 const latest=create({...data,inputs_hash:'second'},{indexedDB:db});await latest.init();assert.equal(latest.get(1).RawNotes,'two');
});
test('Saved is emitted only when all queued writes finish',async()=>{
 const callbacks=[],statuses=[],a=create(data,{indexedDB:fakeIDB(false,callbacks),onStatus:s=>statuses.push(s)});await a.init();statuses.length=0;
 const first=a.save(1,{RawNotes:'first'}),second=a.save(1,{RawNotes:'latest'});await new Promise(r=>setImmediate(r));callbacks.shift()();await first;
 assert.equal(a.hasPendingChanges,true);assert.equal(statuses.at(-1).durable,false);
 await new Promise(r=>setImmediate(r));callbacks.shift()();await second;assert.equal(a.hasPendingChanges,false);assert.equal(statuses.at(-1).durable,true);
});

test('an unrelated successful write does not hide another record storage failure',async()=>{
 let broken=true;const statuses=[],a=create(data,{indexedDB:fakeIDB(key=>broken&&key==='abc:1'),onStatus:s=>statuses.push(s)});await a.init();
 await a.save(1,form);await a.save(2,{RawNotes:'fine'});assert.equal(a.hasPendingChanges,true);assert.equal(statuses.at(-1).durable,false);
 broken=false;await a.save(1,form);assert.equal(a.hasPendingChanges,false);assert.equal(statuses.at(-1).durable,true);
});
