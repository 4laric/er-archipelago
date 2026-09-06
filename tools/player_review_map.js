// This is a catalog map, not the live save. Pins are recorded positions to review.
let mapOpen=params().get('p_map')==='1', mapKey='m60', mapBox=null;
let launch={id:Number(params().get('check')),name:params().get('expected_name'),from:params().get('from')};
function sameName(a,b){return a.split(', may be sweep-granted')[0]===b.split(', may be sweep-granted')[0]}
function identityMismatch(c){return launch.from==='f6'&&launch.id===c.check_id&&launch.name&&!sameName(launch.name,c.name)}
function pointXY(point){
 const c=DATA.player_maps?.[point.map]?.calibration;if(!c)return null;
 const b=c.world_bounds,i=c.image;
 return [i.margin+(point.x-b.gx_min)/(b.gx_max-b.gx_min)*i.draw_w,
 i.margin+(1-(point.z-b.gz_min)/(b.gz_max-b.gz_min))*i.draw_h];
}
function chooseCheck(c){
 saveDraft();current=c;draw();show(c);history.replaceState(null,'',link(c.check_id));
}
function showOnMap(c){
 mapOpen=true;const point=c.player.positions?.[0];
 if(point){mapKey=point.map;const xy=pointXY(point);mapBox=[xy[0]-120,xy[1]-120,240,240]}
 else mapBox=null;
 renderPlayerMap();el('pMapPanel').scrollIntoView({block:'start'});
 history.replaceState(null,'',link(c.check_id));
}
function renderPlayerMap(){
 el('pMapPanel').hidden=!mapOpen;
 el('pMapToggle').textContent=mapOpen?'Hide map':'Find locations on a map';
 el('pMapToggle').setAttribute('aria-expanded',String(mapOpen));
 if(!mapOpen)return;
 const data=DATA.player_maps?.[mapKey],slot=el('pMapDrawing');
 if(!data){slot.textContent='Map not available in this build.';return}
 el('pMapWorld').value=mapKey;slot.innerHTML=data.svg;
 const svg=slot.querySelector('svg');if(!svg)return;
 svg.setAttribute('role','group');svg.setAttribute('aria-label','Location pins; use the location list as a text alternative');
 const full=svg.viewBox.baseVal;
 const fullBox=[full.x,full.y,full.width,full.height];
 if(mapBox)svg.setAttribute('viewBox',mapBox.join(' '));
 const layer=document.createElementNS('http://www.w3.org/2000/svg','g');svg.append(layer);
 const candidates=visible.filter(c=>c!==current);if(current)candidates.push(current);
 let plotted=0,missing=0,other=0;
 for(const c of candidates){
  const points=c.player.positions||[];if(!points.length){missing++;continue}
  const here=points.filter(p=>p.map===mapKey);if(!here.length){other++;continue}plotted++;
  for(const point of here){
   const xy=pointXY(point);if(!xy)continue;
   const pin=document.createElementNS('http://www.w3.org/2000/svg','circle');
   pin.setAttribute('cx',xy[0]);pin.setAttribute('cy',xy[1]);
   pin.setAttribute('r',current===c?7:4);
   pin.setAttribute('fill',current===c?'#fff':c.player.need==='confirmed'?'#8dc89c':'#f0bf64');
   pin.setAttribute('stroke','#111');pin.setAttribute('stroke-width','1');
   pin.style.cursor='pointer';
   const title=document.createElementNS('http://www.w3.org/2000/svg','title');
   title.textContent=c.player.item+' — '+c.player.place;pin.append(title);
   pin.onclick=()=>{chooseCheck(c);el('pDetail').scrollIntoView({block:'start'})};layer.append(pin);
  }
 }
 el('pMapCount').textContent=plotted+' locations on this map · '+other+' on the other map · '+missing+' without an outdoor pin. Indoor locations are still in the list.';
 if(current&&!current.player.positions?.length)el('pMapCount').textContent+=' The selected location has no pin.';
 el('pMapFit').onclick=()=>{mapBox=null;renderPlayerMap()};
 function move(dx,dy,scale){
  const b=mapBox||fullBox,w=b[2]*scale,h=b[3]*scale;
  if(w<40||w>fullBox[2]*2)return;
  mapBox=[b[0]+(b[2]-w)/2+dx*b[2],b[1]+(b[3]-h)/2+dy*b[3],w,h];renderPlayerMap();
 }
 el('pMapIn').onclick=()=>move(0,0,.65);el('pMapOut').onclick=()=>move(0,0,1/.65);
 for(const [id,x,y] of [['Left',-.25,0],['Right',.25,0],['Up',0,-.25],['Down',0,.25]])
 el('pMap'+id).onclick=()=>move(x,y,1);
}
el('pMapToggle').onclick=()=>{mapOpen=!mapOpen;renderPlayerMap();history.replaceState(null,'',link(current?.check_id))};
el('pMapWorld').onchange=()=>{mapKey=el('pMapWorld').value;mapBox=null;renderPlayerMap()};
