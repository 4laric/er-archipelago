// Exercise shipped navigation and state changes, with the same offline DOM harness as CI.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {El, makeDocument, text} = require('./wizard_dom_shim.js');
const html = fs.readFileSync(path.join(__dirname, '../wizard/wizard.html'), 'utf8');
const head = html.split('<script id="wizard-core">')[0];
const doc = makeDocument([...new Set([...head.matchAll(/\bid="([\w-]+)"/g)].map(m => m[1]))]);
for (const id of ['er-options-metadata', 'er-region-census', 'er-pool-composition']){
  const match = html.match(new RegExp('<script id="' + id + '"[^>]*>([\\s\\S]*?)</script>'));
  assert.ok(match, id); doc.getElementById(id).textContent = match[1];
}
const sandbox = {document:doc, window:{scrollTo(){}}, navigator:{clipboard:{writeText:async()=>{}}},
  location:{protocol:'https:',origin:'https://example.invalid',pathname:'/er/wizard.html'},
  URL, Option:function(t,v){const e=new El('option');e.textContent=t;e.value=v;return e;},
  console, JSON, Math, Object, Array, Set, Map, Number, String, Boolean, Date, RegExp, Error,
  isNaN, parseInt, parseFloat, encodeURIComponent, decodeURIComponent, Blob:function(){},
  fetch:()=>{}, setTimeout, clearTimeout, module:{}};
const ctx = vm.createContext(sandbox);
for (const match of html.matchAll(/<script(?![^>]*type="application\/json")[^>]*>([\s\S]*?)<\/script>/g)){
  let src=match[1];
  if (src.includes('function renderStep()')){
    const i=src.lastIndexOf('})();'); assert.ok(i>=0);
    src=src.slice(0,i)+'\nglobalThis.probe={meta,state,refresh,confineShare,parseWizardYaml,importWizardYaml,ERW};\n'+src.slice(i);
  }
  vm.runInContext(src,ctx,{timeout:20000});
}
const P=sandbox.probe; assert.ok(P);
const main=doc.getElementById('main');
const go = title => {
  const nav=main.kids.find(n=>n.className==='stepnav');
  const button=nav.kids.find(n=>n.innerHTML===title); assert.ok(button,title); button.fire('click');
};
const rows = () => doc.querySelectorAll('[data-option]');
const row = key => rows().find(n=>n.getAttribute('data-option')===key);
const visible = node => {let n=node;while(n){if(n.hidden)return false;n=n.parent;}return true;};
go('Options');
const search=doc.getElementById('settings-search');
search.value='confine_foreign_progression'; search.fire('input');
assert.ok(visible(row('confine_foreign_progression')), 'YAML-key search finds incoming confinement');
assert.equal(row('confine_foreign_progression').parent.open,true, 'search opens advanced tuning');
assert.equal(visible(row('num_regions')),false);
assert.equal(doc.getElementById('settings-empty').hidden,true);
search.value='xyz-no-such-option'; search.fire('input');
assert.equal(doc.getElementById('settings-empty').hidden,false);
search.value='natural_progression'; search.fire('input');
assert.equal(doc.getElementById('settings-empty').hidden,true);
assert.ok(text(doc.getElementById('settings-legacy-results')).includes('Deprecated mode'));
assert.equal(row('natural_progression'),undefined,'legacy search gives guidance, not a dead control');
doc.getElementById('settings-clear').fire('click');
const offered=new Set(rows().map(n=>n.getAttribute('data-option')));
for(const o of P.meta.options){
  if(o.compatibility_only) assert.equal(offered.has(o.key),false,o.key);
  else assert.ok(offered.has(o.key),'unreachable setting '+o.key);
}
doc.getElementById('settings-changed').fire('click');
assert.equal(doc.getElementById('settings-empty').hidden,false, 'defaults have no changed rows');
P.state.values.confine_foreign_progression=0; P.refresh();
assert.ok(visible(row('confine_foreign_progression')));
assert.equal(visible(row('num_regions')),false);
assert.equal(row('confine_foreign_progression').querySelector('.modbadge').hidden,false);
assert.equal(P.confineShare(),0);
const slider=row('confine_foreign_progression').querySelectorAll('input').find(n=>n.type==='range');
slider.value='35'; slider.fire('input'); assert.equal(P.confineShare(),35);
assert.ok(text(row('confine_foreign_progression')).includes('35%'));
assert.equal(doc.getElementById('settings-search'),search,'changing a setting preserves the search control');
P.state.values.progression_sharing='open'; P.refresh(); assert.equal(P.confineShare(),0);
assert.ok(P.ERW.inactiveReason(P.meta,P.state,'confine_foreign_progression'));
P.state.values.progression_sharing='balanced'; P.state.values.multiworld_scope='surface';
P.refresh(); assert.equal(P.confineShare(),100);
assert.ok(P.ERW.inactiveReason(P.meta,P.state,'confine_foreign_progression'));
P.state.values={};
assert.ok(!P.ERW.buildYaml(P.meta,P.state).includes('  natural_progression:'));
// An older complete export may omit the formerly hidden confinement key.
const old=P.ERW.buildYaml(P.meta,P.state).replace(/^  confine_foreign_progression:.*\n/m,'')+
  '  natural_progression: true\n  global_scadutree_blessing: off\n';
P.importWizardYaml(old);
assert.equal(P.state.values.natural_progression,true);
assert.equal(P.ERW.getVal(P.meta,P.state,'confine_foreign_progression'),100);
const notice=doc.getElementById('legacy-notice');
assert.equal(notice.hidden,false); assert.ok(text(notice).includes('natural_progression'));
assert.ok(P.ERW.buildYaml(P.meta,P.state).includes('  natural_progression: true'));
assert.equal(P.state.values.global_scadutree_blessing,'off','default-valued legacy key is preserved and explained');
go('Advanced');
assert.ok(text(main).includes('Deprecated settings & older YAMLs'));
for(const key of ['natural_progression','leyndell_runes_required','global_scadutree_blessing','merchant_bell_logic','flask_upgrades_on_progression_surface']){
  assert.ok(text(main).includes(key)); assert.equal(row(key),undefined,'deprecated key is guidance only');
}
go('Finish'); assert.ok(text(main).includes('Your changes'));
assert.ok(text(main).includes('Natural Progression'));
const useLocks=doc.querySelectorAll('.legacy-remove').find(n=>n.getAttribute('data-legacy-key')==='natural_progression');
useLocks.fire('click');
assert.equal(P.ERW.getVal(P.meta,P.state,'natural_progression'),false);
assert.ok(!P.ERW.buildYaml(P.meta,P.state).includes('  natural_progression:'));
console.log('Wizard UX: discoverability, changed filters, incoming overrides, legacy import preservation and review pass.');
