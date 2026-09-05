/* Local observations: importing never changes catalog confirmation. */
(function(root){
'use strict';
const SCHEMA='er-player-notebook-v1';
const fields=['Finding','Item','Region','Route','Evidence','Version','Context','RawNotes','Reviewer'];
const legacy={finding:'Finding',observed_item:'Item',observed_place:'Region',route:'Route',evidence:'Evidence',versions:'Version',environment:'Context',raw_notes:'RawNotes',reviewer:'Reviewer'};
function cleanForm(value){
 if(!value||typeof value!=='object'||Array.isArray(value))throw Error('Missing review fields');
 const form={};for(const key of fields){if(value[key]!==undefined&&typeof value[key]!=='string')throw Error('Invalid '+key);form[key]=value[key]||'';}
 if(value.Reviewed!==undefined&&typeof value.Reviewed!=='boolean')throw Error('Invalid reviewed status');
 form.Reviewed=value.Reviewed===true;return form;
}
function create(data,options={}){
 const catalog=new Map(data.checks.map(c=>[c.check_id,c])),entries=new Map(),origins=new Map(),recoveryRecords=[],defaults={Reviewer:'',Version:'',Context:''};
 let db=null,queue=Promise.resolve(),writeVersion=0;const dirty=new Map();let changed=new Set(),defaultsChanged=false;
 function retain(r,reason){if(!recoveryRecords.some(x=>JSON.stringify(x.record)===JSON.stringify(r)))recoveryRecords.push({record:JSON.parse(JSON.stringify(r)),reason});}
 const notify=(durable,message)=>options.onStatus?.({durable,message});
 function record(id,form){const c=catalog.get(id);if(!c)throw Error('Unknown location');return {check_id:id,original_name:c.name,catalog_hash:data.inputs_hash,form:cleanForm(form),imported_from:origins.get(id)||[]};}
 function validate(r){const c=catalog.get(r?.check_id);if(!c)throw Error('Location not in this catalog');if(typeof r.catalog_hash!=='string'||!r.catalog_hash)throw Error('Missing catalog snapshot');if(r.original_name!==c.name)throw Error('Location name does not match');return cleanForm(r.form);}
 function write(id,value){
  const version=++writeVersion;dirty.set(id,version);
  queue=queue.catch(()=>{}).then(()=>new Promise(resolve=>{
   if(!db){notify(false,'Kept in memory only. Download a notebook backup before leaving this page.');resolve(false);return;}
   try{const tx=db.transaction('notebooks','readwrite');tx.objectStore('notebooks').put(value,id);
    tx.oncomplete=()=>{if(dirty.get(id)===version)dirty.delete(id);notify(dirty.size===0,dirty.size?'Some changes are still pending or could not be stored. Keep this tab open or download a backup.':'Saved on this device. Download a backup to share or move devices.');resolve(true);};
    tx.onerror=tx.onabort=()=>{notify(false,'Device storage failed. Your input is still here; download a notebook backup before leaving.');resolve(false);};
   }catch{notify(false,'Device storage unavailable. Your input is still here; download a notebook backup.');resolve(false);}
  }));return queue;
 }
 async function init(){
  const factory=options.indexedDB===undefined?root.indexedDB:options.indexedDB;
  try{
   if(!factory)throw Error('unavailable');
   db=await new Promise((resolve,reject)=>{const req=factory.open('er-player-review-notebooks',1);req.onupgradeneeded=()=>req.result.createObjectStore('notebooks');req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);req.onblocked=()=>reject(Error('blocked'));});
   db.onversionchange=()=>{db.close();db=null;notify(false,'Storage changed in another tab. Download a backup before leaving.');};
   const saved=await new Promise((resolve,reject)=>{const tx=db.transaction('notebooks','readonly'),req=tx.objectStore('notebooks').getAll();req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);tx.onabort=()=>reject(tx.error);});
   const candidates=new Map();
   for(const r of saved){
    if(r?.kind==='defaults'){if(!defaultsChanged)for(const k of Object.keys(defaults))if(typeof r[k]==='string')defaults[k]=r[k];continue;}
    if(r?.kind==='recovery'){retain(r.record,r.reason);continue;}
    try{validate(r);if(!candidates.has(r.check_id))candidates.set(r.check_id,[]);candidates.get(r.check_id).push(r);}
    catch(e){retain(r,e.message);}
   }
   let migrated=0;
   for(const [id,versions] of candidates){
    const current=versions.find(r=>r.catalog_hash===data.inputs_hash);
    const distinct=new Set(versions.map(r=>JSON.stringify(cleanForm(r.form))));
    const selected=current||(distinct.size===1?versions[0]:null);
    for(const r of versions)if(r!==current)retain(r,selected?'Earlier catalog notes; retained for recovery.':'Several earlier versions disagree. Choose which notes to restore.');
    if(selected&&!changed.has(id)){
     entries.set(id,validate(selected));
     origins.set(id,selected===current?(selected.imported_from||[]):[selected]);
     if(selected!==current)migrated++;
    }
   }
   notify(true,(migrated?migrated+' notes carried forward by exact location ID and name. ':'')+
    (recoveryRecords.length?recoveryRecords.length+' earlier or unmatched records are available in recovery downloads. ':'')+
    'Saved on this device. Use one editing tab and download backups regularly.');
  }catch{db=null;notify(false,'Device storage unavailable. Notes stay in memory; download a notebook backup before leaving.');}
  return api;
 }
 function previewImport(text){
  const result={rows:[],errors:[],recoveryRecords:[]};let input;
  try{input=typeof text==='string'?JSON.parse(text):text;}catch{result.errors.push('This is not valid JSON. Paste plain notes into a location form instead.');return result;}
  let records;
  if(input?.schema===SCHEMA&&Array.isArray(input.reviews)){
   records=input.reviews;
   if(input.recovery_records!==undefined&&!Array.isArray(input.recovery_records)){result.errors.push('Malformed recovery records');return result;}
   result.recoveryRecords=input.recovery_records||[];
   if(result.recoveryRecords.some(x=>!x||typeof x!=='object'||!x.record||typeof x.record!=='object'||typeof x.reason!=='string')){result.errors.push('Malformed recovery record');return result;}
  }
  else if(input?.schema==='er-player-review-v1')records=[input];
  else if(Array.isArray(input))records=input;
  else{result.errors.push('Choose a notebook backup or an array of player review files.');return result;}
  const counts=new Map();for(const r of records)counts.set(r?.check_id,(counts.get(r?.check_id)||0)+1);
  for(const r of records){const row={id:r?.check_id,status:'rejected',reason:''};
   try{
    if(counts.get(row.id)!==1)throw Error('Repeated location in this import; separate conflicting notes first');
    let normalized=r;
    if(r?.schema==='er-player-review-v1'){
     const c=catalog.get(row.id);if(!c)throw Error('Location not in this catalog');
     if(r.catalog_hash!==data.inputs_hash)throw Error('Legacy review is from another catalog snapshot');
     if(!r.catalog||['item','region','place'].some(k=>r.catalog[k]!==c.player[k]))throw Error('Original location description does not match');
     if(r.observation_scope!=='player_report_not_adjudicated')throw Error('Unknown observation scope');
     const f={};for(const [key,dest]of Object.entries(legacy))f[dest]=r[key]===undefined?'':r[key];
     if(r.reviewed!==undefined)f.Reviewed=r.reviewed;
     normalized={check_id:row.id,original_name:c.name,catalog_hash:r.catalog_hash,form:f};
    }else if(input?.schema!==SCHEMA)throw Error('Unknown review format');
    row.form=validate(normalized);row.source=JSON.parse(JSON.stringify(normalized));
    const old=entries.get(row.id);row.status=!old?'new':JSON.stringify(cleanForm(old))===JSON.stringify(row.form)?'same':'conflict';
    row.reason=row.status==='conflict'?'This location already has different notes. Keep yours or explicitly replace them.':'';
    if(normalized.catalog_hash!==data.inputs_hash)row.reason+=' Older catalog snapshot: exact location ID and name still match. Original source is retained.';
   }catch(e){row.reason=e.message;}
   result.rows.push(row);
  }return result;
 }
 async function applyImport(preview,decisions={}){
  let imported=0,kept=0;
  if(preview.errors.length)return {imported,kept};
  for(const item of preview.recoveryRecords||[]){
   retain(item.record,item.reason);
   await write('recovery:'+JSON.stringify(item.record),{kind:'recovery',record:item.record,reason:item.reason});
  }
  for(const row of preview.rows){
   if(!['new','same','conflict'].includes(row.status)){kept++;continue;}
   const current=entries.get(row.id),different=current&&JSON.stringify(cleanForm(current))!==JSON.stringify(row.form);
   if(different&&decisions[row.id]!=='replace'||row.status==='conflict'&&decisions[row.id]!=='replace'||row.status==='same'&&!different){kept++;continue;}
   if(different){
    const previous=record(row.id,current),reason='Notes before an explicitly approved replacement.';
    retain(previous,reason);
    await write('recovery:'+JSON.stringify(previous),{kind:'recovery',record:previous,reason});
   }
   origins.set(row.id,[...(origins.get(row.id)||[]),row.source]);
   await api.save(row.id,row.form);imported++;
  }return {imported,kept};
 }
 const api={entries,recoveryRecords,get hasPendingChanges(){return dirty.size>0;},init,get:id=>entries.get(id),getDefaults:()=>({...defaults}),
  async saveDefaults(value){for(const k of Object.keys(defaults)){if(typeof value[k]!=='string')throw Error('Invalid default '+k);defaults[k]=value[k];}defaultsChanged=true;return write('defaults',{kind:'defaults',...defaults});},
  async save(id,form){const r=record(id,form);entries.set(id,r.form);changed.add(id);notify(false,'Saving on this device…');return write(data.inputs_hash+':'+id,r);},
  exportNotebook:()=>({schema:SCHEMA,catalog_hash:data.inputs_hash,observation_scope:'player_report_not_adjudicated',exported_at:new Date().toISOString(),defaults:{...defaults},recovery_records:JSON.parse(JSON.stringify(recoveryRecords)),reviews:[...entries].sort((a,b)=>a[0]-b[0]).map(([id,form])=>record(id,form))}),
  exportRecoveryNotebook:index=>({schema:SCHEMA,observation_scope:'player_report_not_adjudicated',reviews:(index===undefined?recoveryRecords:[recoveryRecords[index]]).filter(Boolean).map(x=>JSON.parse(JSON.stringify(x.record)))}),
  previewImport,applyImport};
 return api;
}
const exported={create,cleanForm,SCHEMA};root.PlayerReviewNotebook=exported;if(typeof module!=='undefined')module.exports=exported;
})(typeof globalThis!=='undefined'?globalThis:this);
