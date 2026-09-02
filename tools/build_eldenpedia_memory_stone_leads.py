#!/usr/bin/env python3
"""Add the two missing Memory Stone acquisition bindings from a pinned revision."""
from __future__ import annotations
import argparse,csv,importlib.util,json,re
from io import StringIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];A=ROOT/"greenfield"/"evidence"/"wiki-audit"
M=A/"eldenpedia-memory-stone-pages.tsv";L=A/"eldenpedia-memory-stone-check-leads.tsv";C=A/"eldenpedia-memory-stone-coverage.json"
PID,RID,SHA=6480,100680,"4f64ec6ea32191ef7a2cd67d727d0b8665d4e3ef";SID=f"wiki:eldenpedia:page-{PID}:revision-{RID}"
PF=("source_id","page_id","revision_id","revision_timestamp","revision_sha1","title","canonical_url","revision_url","acquisition_rows","disposition")
LF=("lead_id","subject_kind","subject_id","claim_kind","normalized_value","source_ids","independence_families","disposition","game_version","exact_citations","summary","limitations")
B=((7770020,60420,"Testu's Rise"),(7770021,60430,"Seluvis's Rise"))
def fetch():
 q={"action":"query","format":"json","formatversion":"2","revids":str(RID),"prop":"revisions","rvprop":"ids|timestamp|sha1|content","rvslots":"main"};r=Request("https://eldenring.wiki.gg/api.php?"+urlencode(q),headers={"User-Agent":"er-archipelago-v060-evidence-audit/1.0"})
 with urlopen(r,timeout=60) as h:return json.load(h)["query"]["pages"][0]
def locations():
 s=importlib.util.spec_from_file_location("_memory_stone_data",ROOT/"greenfield"/"eldenring"/"data.py");m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return {i:(r,n,f) for r,cs in m.LOCATIONS.items() for n,i,f in cs}
def build(p):
 rv=p["revisions"][0]
 if (p["pageid"],p["title"],rv["revid"],rv["sha1"])!=(PID,"Memory Stone",RID,SHA):raise ValueError("unregistered revision")
 text=rv["slots"]["main"]["content"]
 if len(re.findall(r"\[\[(?:Testu's Rise|Seluvis's Rise)\]\]",text))!=2:raise ValueError("source anchors changed")
 cur=locations();lots={(int(r["flag"]),int(r["item_id"]),r["name"]) for r in csv.DictReader(open(ROOT/"greenfield"/"flag_lots.tsv"),delimiter="\t")};leads=[]
 for apid,flag,anchor in B:
  region,name,current=cur[apid]
  if current!=flag or ":: Memory Stone -" not in name or (flag,10030,"Memory Stone") not in lots:raise ValueError(f"identity drift {apid}")
  leads.append({"lead_id":f"eldenpedia-memory-stone-revision-{RID}-check-{apid}","subject_kind":"check","subject_id":str(apid),"claim_kind":"acquisition_identity","normalized_value":json.dumps({"anchor":anchor,"flag":flag,"item_id":10030,"item_name":"Memory Stone","project_region":region},sort_keys=True,separators=(",",":")),"source_ids":SID,"independence_families":"gameplay-wiki:eldenpedia","disposition":"lead_only","game_version":"unknown","exact_citations":f"eldenpedia:pageid-{PID}:revision-{RID}:#Acquisition:{anchor}","summary":f"Eldenpedia revision {RID} lists a Memory Stone at {anchor}; that unique tower and committed ItemLot identity select one AP check.","limitations":"Community-wiki acquisition lead cross-checked against committed lot data. It does not prove v1.17 behavior, access logic, route order, or puzzle requirements."})
 manifest=[{"source_id":SID,"page_id":str(PID),"revision_id":str(RID),"revision_timestamp":rv["timestamp"],"revision_sha1":SHA,"title":"Memory Stone","canonical_url":"https://eldenring.wiki.gg/wiki/Memory_Stone","revision_url":f"https://eldenring.wiki.gg/w/index.php?oldid={RID}","acquisition_rows":"8","disposition":"lead_only"}]
 return manifest,leads,{"ap_checks":9,"prior_union_checks":7,"new_union_checks":2,"union_after":9,"source_bindings":2,"explicit_refusals":0}
def render(rows,fields):o=StringIO(newline="");w=csv.DictWriter(o,fieldnames=fields,delimiter="\t",lineterminator="\n");w.writeheader();w.writerows(rows);return o.getvalue()
def main():
 x=argparse.ArgumentParser();x.add_argument("--capture",type=Path);a=x.parse_args();p=json.loads(a.capture.read_text()) if a.capture else fetch();p=p["query"]["pages"][0] if "query" in p else p;m,l,c=build(p);M.write_text(render(m,PF));L.write_text(render(l,LF));C.write_text(json.dumps(c,indent=2,sort_keys=True)+"\n");print(json.dumps(c,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
