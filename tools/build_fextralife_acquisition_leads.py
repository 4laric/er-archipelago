#!/usr/bin/env python3
"""Bind repeated checks to pinned Fextralife acquisition text and current map-lot flags."""
from __future__ import annotations
import argparse, csv, importlib.util, json, re
from collections import Counter, defaultdict
from io import StringIO
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; AUDIT=ROOT/"greenfield/evidence/wiki-audit"; CLAIMS=ROOT/"greenfield/evidence/v060-current/claims.tsv"
LEADS=AUDIT/"fextralife-acquisition-check-leads.tsv"; MANIFEST=AUDIT/"fextralife-acquisition-pages.tsv"; REPORT=AUDIT/"fextralife-acquisition-coverage.json"
FIELDS=("lead_id","subject_kind","subject_id","claim_kind","normalized_value","source_ids","independence_families","disposition","game_version","exact_citations","summary","limitations")
MFIELDS=("source_id","page_id","revision_id","revision_timestamp","revision_sha1","title","canonical_url","revision_url","acquisition_rows","disposition")
MAP_LOT="ItemLotParam_map.getItemFlagId"
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return m
def norm(s):return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
def page_key(s):return norm(re.sub(r"\((\d+)\)",r"\1",s))
def item(n):return re.sub(r"^\[[^]]+\]\s*","",n.split(" :: ",1)[1].split(" - ",1)[0]).replace("[","").replace("]","")
def anchor(n):
 if " - " not in n:return ""
 s=n.split(" - ",1)[1];s=re.split(r", may be sweep| \[f",s)[0];s=re.sub(r"\s*\(region unconfirmed\)|\s*\(\d+\)$","",s);s=re.sub(r"^(near|around|at|in|from|outside|behind|below|above)\s+","",s,flags=re.I);return norm(s)
def content(p):
 s=p["revisions"][0]["slots"]["main"];return s.get("content",s.get("*",""))
def acquisition(c):
 m=re.search(r"(?ims)Where to (?:find|Find).*?(?=^==[^=]|\Z)",c);return m.group(0) if m else ""
def render(rows,fields):
 out=StringIO(newline="");w=csv.DictWriter(out,fieldnames=fields,delimiter="\t",lineterminator="\n");w.writeheader();w.writerows(rows);return out.getvalue()
def reserved(k):return k.startswith(("smithing stone ","somber smithing stone ","ancient dragon smithing stone","somber ancient dragon smithing stone","ghost glovewort ","grave glovewort ")) or k in {"scadutree fragment","revered spirit ash"}
def build(capture):
 data=mod("_data",ROOT/"greenfield/eldenring/data.py"); checks=defaultdict(list)
 vague={norm(x) for x in data.LOCATIONS}|{"altus plateau","liurnia of the lakes","weeping peninsula","volcano manor","consecrated snowfield","crumbling farum azula","realm of shadow","lands between"}
 for region,entries in data.LOCATIONS.items():
  for name,ap,flag in entries:checks[norm(item(name))].append((ap,flag,region,name,anchor(name)))
 detections={}
 with CLAIMS.open(encoding="utf-8",newline="") as h:
  for r in csv.DictReader(h,delimiter="\t"):
   if r["claim_kind"]=="detection" and r["active"]=="true":
    v=json.loads(r["value"])
    if isinstance(v,dict):detections[int(r["subject_id"])]=v
 existing={}
 with (AUDIT/"fextralife-item-pages.tsv").open(encoding="utf-8",newline="") as h:
  for r in csv.DictReader(h,delimiter="\t"):existing[r["source_id"]]=r
 emitted={};new_sources={};stats=Counter(requested_titles=len(capture.get("requested_titles",[])),resolved_pages=len(capture["pages"]),missing_pages=len(capture.get("missing_titles",[])))
 for p in capture["pages"]:
  k=page_key(p["title"]); candidates=checks.get(k,[])
  if not candidates:stats["refused_no_exact_item"]+=1;continue
  if reserved(k):stats["refused_upgrade_material_lane"]+=len(candidates);continue
  revision=p["revisions"][0]; text=acquisition(content(p))
  if not text:stats["refused_no_acquisition_section"]+=len(candidates);continue
  nt=norm(text);matches=[]
  for candidate in candidates:
   ap,flag,_region,_name,phrase=candidate;det=detections.get(ap,{})
   if phrase in vague or len(phrase)<6 or len(phrase.split())<2 or det.get("flag")!=flag or det.get("mechanism")!=MAP_LOT:stats["refused_weak_anchor_or_detection"]+=1;continue
   if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",nt):matches.append(candidate)
   else:stats["refused_anchor_absent"]+=1
  counts=Counter(x[4] for x in matches)
  for ap,flag,region,_name,phrase in matches:
   if counts[phrase]!=1:stats["refused_ambiguous_anchor"]+=1;continue
   pid,rid=int(p["pageid"]),int(revision["revid"]);sid=f"wiki:fextralife:page-{pid}:revision-{rid}"
   if sid in existing:
    if existing[sid]["revision_sha1"]!=revision["sha1"]:raise ValueError(f"revision mismatch: {sid}")
   else:new_sources[sid]={"source_id":sid,"page_id":str(pid),"revision_id":str(rid),"revision_timestamp":revision["timestamp"],"revision_sha1":revision["sha1"],"title":p["title"],"canonical_url":"https://eldenring.wiki.fextralife.com/"+p["title"].replace(" ","_"),"revision_url":"https://eldenring.wiki.fextralife.com/"+p["title"].replace(" ","_")+f"?oldid={rid}","acquisition_rows":str(sum(line.lstrip().startswith("*") for line in text.splitlines())),"disposition":"lead_only"}
   value={"acquisition_anchor":phrase,"flag":flag,"item_name":p["title"],"region":region}
   if re.search(r"\(\d+\)",p["title"]):stats["matched_numbered_alias_checks"]+=1
   emitted[ap]={"lead_id":f"fextralife-acquisition-page-{pid}-revision-{rid}-check-{ap}","subject_kind":"check","subject_id":str(ap),"claim_kind":"identity_region","normalized_value":json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")),"source_ids":sid,"independence_families":"gameplay-wiki:fextralife","disposition":"lead_only","game_version":"unknown","exact_citations":f"fextralife:pageid-{pid}:revision-{rid}:where-to-find:{phrase};project:check:{ap}/detection;flag-{flag}","summary":f"Fextralife revision {rid} places {p['title']} at {phrase}; that exact anchor selects one current AP map-lot flag ({flag}) in {region}.","limitations":"Community-wiki acquisition lead disambiguated by an exact multiword anchor and matching v1.17 map-lot flag evidence. It does not prove access, route order, coordinates, completeness, event timing, or absence of another acquisition."}
 rows=sorted(emitted.values(),key=lambda x:x["lead_id"]);manifest=sorted(new_sources.values(),key=lambda x:x["source_id"]);stats["matched_checks"]=len(rows);stats["new_pinned_pages"]=len(manifest);stats["reused_pinned_pages"]=len({r["source_ids"] for r in rows}&set(existing));return rows,manifest,dict(sorted(stats.items()))
def main():
 p=argparse.ArgumentParser();p.add_argument("capture",type=Path);a=p.parse_args();rows,m,stats=build(json.loads(a.capture.read_text(encoding="utf-8")));LEADS.write_text(render(rows,FIELDS),encoding="utf-8");MANIFEST.write_text(render(m,MFIELDS),encoding="utf-8");REPORT.write_text(json.dumps(stats,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(stats,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
