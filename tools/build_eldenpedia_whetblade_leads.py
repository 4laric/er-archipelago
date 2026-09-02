#!/usr/bin/env python3
"""Bind all whetblade-family checks to pinned Eldenpedia acquisitions."""
from __future__ import annotations
import argparse, csv, importlib.util, json, re
from io import StringIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
ROOT=Path(__file__).resolve().parents[1]; AUDIT=ROOT/"greenfield"/"evidence"/"wiki-audit"
MANIFEST=AUDIT/"eldenpedia-whetblade-pages.tsv"; LEADS=AUDIT/"eldenpedia-whetblade-check-leads.tsv"; COVERAGE=AUDIT/"eldenpedia-whetblade-coverage.json"
PF=("source_id","page_id","revision_id","revision_timestamp","revision_sha1","title","canonical_url","revision_url","acquisition_rows","disposition")
LF=("lead_id","subject_kind","subject_id","claim_kind","normalized_value","source_ids","independence_families","disposition","game_version","exact_citations","summary","limitations")
PAGES={
"Black Whetblade":(4486,17421,"213746af22ea1f53437225fd2c1b71c156ef64c9"),
"Glintstone Whetblade":(9770,36707,"7ec89a8e5e58d562ac2965955e49f4aea38409ef"),
"Iron Whetblade":(11171,42092,"030a739643fffaf72cc1ccb695770f7afa8d3c2a"),
"Red-Hot Whetblade":(1302,5154,"6808c29303ee6f394aac41bc1ca700a048b166f5"),
"Sanctified Whetblade":(1237,70349,"c0a0dceb4e3a8f84e9b2a6c1d9d645db62eab0e5"),
"Whetstone Knife":(1992,82708,"cc065e9b7cc67a527d5d51ec0acfc4b8717e3a03")}
# AP id, flag, title, item id, exact source-local anchor.
BINDINGS=((7770042,65640,"Red-Hot Whetblade",8971,"Chamber Outside the Plaza"),(7770043,65660,"Sanctified Whetblade",8972,"Fortified Manor"),(7770014,60130,"Whetstone Knife",8590,"Twin Maiden Husks"),(7770584,400210,"Whetstone Knife",8590,"Gatefront Ruins"),(7770044,65680,"Glintstone Whetblade",8973,"Debate Parlor"),(7770045,65720,"Black Whetblade",8974,"Night's Sacred Ground"),(7770041,65610,"Iron Whetblade",8970,"Rampart Tower"))

def fetch():
 q={"action":"query","format":"json","formatversion":"2","titles":"|".join(PAGES),"prop":"revisions","rvprop":"ids|timestamp|sha1|content","rvslots":"main"}
 req=Request("https://eldenring.wiki.gg/api.php?"+urlencode(q),headers={"User-Agent":"er-archipelago-v060-evidence-audit/1.0"})
 with urlopen(req,timeout=60) as r:return json.load(r)["query"]["pages"]
def section(text):
 m=re.search(r"(?ims)^==\s*Acquisition\s*==\s*(.*?)(?=^==[^=]|\Z)",text)
 if not m:raise ValueError("missing Acquisition section")
 return m.group(1)
def locations():
 s=importlib.util.spec_from_file_location("_whetblade_data",ROOT/"greenfield"/"eldenring"/"data.py");m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m)
 return {i:(r,n,f) for r,cs in m.LOCATIONS.items() for n,i,f in cs}
def lots():
 with (ROOT/"greenfield"/"flag_lots.tsv").open(encoding="utf-8",newline="") as h:return {(int(r["flag"]),int(r["item_id"]),r["name"]) for r in csv.DictReader(h,delimiter="\t")}
def build(pages):
 by={p["title"]:p for p in pages}
 if set(by)!=set(PAGES):raise ValueError("page set changed")
 manifests=[];sections={}
 for title,(pid,rid,sha) in PAGES.items():
  p=by[title];rv=p["revisions"][0]
  if (p["pageid"],rv["revid"],rv["sha1"])!=(pid,rid,sha):raise ValueError(f"unregistered revision: {title}")
  sections[title]=section(rv["slots"]["main"]["content"])
  manifests.append({"source_id":f"wiki:eldenpedia:page-{pid}:revision-{rid}","page_id":str(pid),"revision_id":str(rid),"revision_timestamp":rv["timestamp"],"revision_sha1":sha,"title":title,"canonical_url":"https://eldenring.wiki.gg/wiki/"+title.replace(" ","_"),"revision_url":f"https://eldenring.wiki.gg/w/index.php?oldid={rid}","acquisition_rows":str(2 if title=="Whetstone Knife" else 1),"disposition":"lead_only"})
 cur,lot,leads=locations(),lots(),[]
 for apid,flag,title,itemid,anchor in BINDINGS:
  if anchor not in sections[title]:raise ValueError(f"missing anchor {anchor}")
  region,name,current_flag=cur[apid]
  if current_flag!=flag or f":: {title}" not in name or (flag,itemid,title) not in lot:raise ValueError(f"identity drift {apid}")
  pid,rid,_=PAGES[title];leads.append({"lead_id":f"eldenpedia-whetblade-page-{pid}-revision-{rid}-check-{apid}","subject_kind":"check","subject_id":str(apid),"claim_kind":"acquisition_identity","normalized_value":json.dumps({"anchor":anchor,"flag":flag,"item_id":itemid,"item_name":title,"project_region":region},sort_keys=True,separators=(",",":")),"source_ids":f"wiki:eldenpedia:page-{pid}:revision-{rid}","independence_families":"gameplay-wiki:eldenpedia","disposition":"lead_only","game_version":"unknown","exact_citations":f"eldenpedia:pageid-{pid}:revision-{rid}:#Acquisition:{anchor}","summary":f"Eldenpedia revision {rid} links {title} to {anchor}; that anchor and committed ItemLot identity select one AP check.","limitations":"Community-wiki acquisition lead cross-checked against committed lot data. It does not prove v1.17 behavior, access logic, route order, coordinates, or event predicates."})
 return sorted(manifests,key=lambda r:int(r["page_id"])),sorted(leads,key=lambda r:r["lead_id"]),{"ap_checks":7,"prior_union_checks":6,"new_union_checks":1,"union_after":7,"source_bindings":7,"explicit_refusals":0}
def render(rows,fields):
 o=StringIO(newline="");w=csv.DictWriter(o,fieldnames=fields,delimiter="\t",lineterminator="\n");w.writeheader();w.writerows(rows);return o.getvalue()
def main():
 p=argparse.ArgumentParser();p.add_argument("--capture",type=Path);a=p.parse_args();pages=json.loads(a.capture.read_text()) if a.capture else fetch()
 if isinstance(pages,dict):pages=pages["query"]["pages"]
 m,l,c=build(pages);MANIFEST.write_text(render(m,PF));LEADS.write_text(render(l,LF));COVERAGE.write_text(json.dumps(c,indent=2,sort_keys=True)+"\n");print(json.dumps(c,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
