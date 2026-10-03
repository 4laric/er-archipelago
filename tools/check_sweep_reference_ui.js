/* Execute the real page script and inspect its rendered markup and event handlers.
   This is a DOM harness, not a browser visual/layout check. No packages required. */
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const html = fs.readFileSync(process.argv[2], 'utf8');
const payload = html.match(/<script id="sweep-payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const nodes = new Map();
class Node {
  constructor(id){this.id=id;this.value='';this.textContent='';this.innerHTML='';this.handlers={};this.options=[];}
  addEventListener(event, handler){this.handlers[event]=handler;}
  add(option){this.options.push(option);}
  scrollIntoView(){this.scrolled=true;}
}
for (const id of ['sweep-payload','search','region','rung','status','groups','stamp']) nodes.set(id,new Node(id));
nodes.get('sweep-payload').textContent=payload;nodes.get('rung').value='bosses';
const context={
  document:{getElementById(id){
    if(!nodes.has(id)&&id.startsWith('boss-')&&nodes.get('groups').innerHTML.includes('id="'+id+'"')) nodes.set(id,new Node(id));
    return nodes.get(id)||null;
  }},
  location:{pathname:'/er-archipelago-sweep-reference.html',hash:''},
  window:{addEventListener(event,handler){this[event]=handler;}},
  Option:function(text,value){this.text=text;this.value=value;}, console
};
vm.createContext(context);vm.runInContext(script,context);
const data=JSON.parse(payload), count=()=>Number(nodes.get('status').textContent.split(' ')[0]);
assert.equal(count(),data.groups.length);
assert.equal(nodes.get('region').options.length,new Set(data.groups.map(g=>g.region)).size);
const search=nodes.get('search'), region=nodes.get('region'), rung=nodes.get('rung'), groups=nodes.get('groups');
search.value='Mohg, the Omen';search.handlers.input();assert.equal(count(),1);
assert(groups.innerHTML.includes('m35_00'));assert(groups.innerHTML.includes('candidate checks'));
assert(!groups.innerHTML.includes('Morgott, the Omen King'));
const unaudited=data.groups.find(g=>!g.arena_audited);
assert(unaudited,'The production corpus must exercise the unaudited-arena disclosure');
search.value=unaudited.boss;search.handlers.input();assert(groups.innerHTML.includes('Arena region unverified'));
search.value='Mohg, the Omen';search.handlers.input();
const sewer=data.groups.find(g=>g.boss==='Mohg, the Omen'), check=data.checks[sewer.checks[0]];
assert(groups.innerHTML.includes('er-archipelago-check-browser.html#q='));
search.value=check.name;search.handlers.input();assert(count()>0);assert(groups.innerHTML.includes('class="badge">match'));
search.value='No boss or check has this phrase';search.handlers.input();assert.equal(count(),0);
assert(groups.innerHTML.includes('No matching sweeps'));
search.value='';region.value='Leyndell';region.handlers.change();assert(count()>1);
rung.value='none';rung.handlers.change();assert.equal(count(),0);assert(groups.innerHTML.includes('Dungeon Sweep is off'));
context.location.hash='#boss-'+sewer.flag;context.window.hashchange();
assert.equal(rung.value,'bosses');assert.equal(region.value,'Leyndell');
assert.equal(nodes.get('boss-'+sewer.flag).open,true);assert.equal(nodes.get('boss-'+sewer.flag).scrolled,true);
// Hosted aliases must retain same-release check links.
context.location.pathname='/er/beta/sweeps.html';search.value='Mohg, the Omen';search.handlers.input();
assert(groups.innerHTML.includes('checks.html#q='));assert(!groups.innerHTML.includes('er-archipelago-check-browser.html#q='));
console.log('[ok] sweep reference: default corpus, boss/check search, region/rung filters, empty results, arena links and shareable sweeps');
