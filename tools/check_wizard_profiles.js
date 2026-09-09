// Run against the actual embedded metadata and pure wizard core.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(require('node:path').join(__dirname,'../wizard/wizard.html'),'utf8');
const context = {module:{exports:{}}};
vm.runInNewContext(html.match(/<script id="wizard-core">([\s\S]*?)<\/script>/)[1],context);
const api=context.module.exports;
const meta=api.loadMeta(JSON.parse(html.match(/<script id="er-options-metadata"[^>]*>([\s\S]*?)<\/script>/)[1]));
const groups=api.profiles(meta);
assert.equal(groups.length,6);
for(const group of groups){
  assert.ok(group.picks.length >= 2,group.id);
  for(const pick of group.picks){
    const state=api.newState();
    state.values.death_link=true;
    state.values.maximum_enemy_difficulty=33;
    api.applyProfile(meta,state,pick);
    assert.equal(api.activeProfile(meta,state,group).id,pick.id);
    assert.equal(state.values.death_link,true);
    assert.equal(state.values.maximum_enemy_difficulty,33);
    assert.equal(api.getVal(meta,state,'vanilla_placement'),'off');
    for(const [key,value] of Object.entries(pick.values)){
      const option=meta.byKey[key];
      if(option.choices) assert.ok(option.choices.some(c=>c.name===value),key);
      if(option.valid_keys){
        for(const item of Array.isArray(value)?value:Object.keys(value)) assert.ok(option.valid_keys.includes(item),key+':'+item);
      }
    }
  }
}
const state=api.newState();
api.setVal(meta,state,'num_regions',7);
assert.equal(api.activeProfile(meta,state,groups.find(g=>g.id==='size')),null);
api.setVal(meta,state,'ending_condition','region_locks');
assert.ok(api.inactiveReason(meta,state,'goal_great_runes'));
api.setVal(meta,state,'ending_condition','great_runes');
assert.equal(api.inactiveReason(meta,state,'goal_great_runes'),'');
assert.ok(api.inactiveReason(meta,state,'death_link_amnesty_inbound'));
api.setVal(meta,state,'death_link',true);
assert.equal(api.inactiveReason(meta,state,'death_link_amnesty_inbound'),'');
for(const key of ['flask_upgrades_on_progression_surface','global_scadutree_blessing','merchant_bell_logic']){
  if(!meta.byKey[key]?.compatibility_only) continue;
  assert.ok(!api.buildYaml(meta,state).includes('  '+key+':'));
  state.values[key]=meta.byKey[key].default;
  assert.ok(api.buildYaml(meta,state).includes('  '+key+':'));
}
console.log('Wizard profiles: valid values, independent changes, Custom state, dependencies and legacy roundtrip pass.');

const independent=api.newState();
for(const group of groups) api.applyProfile(meta,independent,group.picks[0]);
for(const group of groups) assert.equal(api.activeProfile(meta,independent,group).id,group.picks[0].id);
const content=groups.find(g=>g.id==='content');
assert.equal(content.picks.length,4);
api.applyProfile(meta,independent,content.picks.find(p=>p.id==='base-gear'));
assert.equal(api.getVal(meta,independent,'enable_dlc'),false);
assert.equal(api.getVal(meta,independent,'enable_dlc_gear'),true);
assert.equal(api.getVal(meta,independent,'dlc_only'),false);
