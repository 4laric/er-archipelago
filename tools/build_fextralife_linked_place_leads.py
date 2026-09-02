#!/usr/bin/env python3
"""Bind repeated checks where a Fextralife acquisition link names the AP place anchor."""
from __future__ import annotations
import argparse,csv,importlib.util,json,re
from collections import Counter,defaultdict
from io import StringIO
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];AUDIT=ROOT/"greenfield/evidence/wiki-audit";CLAIMS=ROOT/"greenfield/evidence/v060-current/claims.tsv";OUT=AUDIT/"fextralife-linked-place-check-leads.tsv";REPORT=AUDIT/"fextralife-linked-place-coverage.json"
FIELDS=("lead_id","subject_kind","subject_id","claim_kind","normalized_value","source_ids","independence_families","disposition","game_version","exact_citations","summary","limitations");MAP_LOT="ItemLotParam_map.getItemFlagId"
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s.loader;s.loader.exec_module(m);return m
def norm(s):return re.sub(r"[^a-z0-9]+"," ",s.lower()).strip()
def item(n):return re.sub(r"^\[[^]]+\]\s*","",n.split(" :: ",1)[1].split(" - ",1)[0]).replace("[","").replace("]","")
def anchor(n):
 if " - " not in n:return ""
 s=n.split(" - ",1)[1];s=re.split(r", may be sweep| \[f",s)[0];s=re.sub(r"\s*\(region unconfirmed\)|\s*\(\d+\)$","",s);return norm(s)
def content(p):
 s=p["revisions"][0]["slots"]["main"];return s.get("content",s.get("*",""))
def acquisition(c):
 m=re.search(r"(?ims)Where to (?:find|Find).*?(?=^==[^=]|\Z)",c);return m.group(0) if m else ""
def reserved(k):return k.startswith(("smithing stone ","somber smithing stone ","ancient dragon smithing stone","somber ancient dragon smithing stone","ghost glovewort ","grave glovewort ")) or k in {"scadutree fragment","revered spirit ash"}
def build(capture):
 data=mod("_data",ROOT/"greenfield/eldenring/data.py");idx=defaultdict(list);vague={norm(x) for x in data.LOCATIONS}|{"altus plateau","liurnia of the lakes","weeping peninsula","volcano manor","consecrated snowfield","crumbling farum azula","realm of shadow","lands between","limgrave","caelid","mt gelmir"}
 for region,entries in data.LOCATIONS.items():
  for name,ap,flag in entries:idx[norm(item(name))].append((ap,flag,region,name,anchor(name)))
 det={}
 with CLAIMS.open(encoding="utf-8",newline="") as h:
  for r in csv.DictReader(h,delimiter="\t"):
   if r["claim_kind"]=="detection" and r["active"]=="true":
    v=json.loads(r["value"])
    if isinstance(v,dict):det[int(r["subject_id"])]=v
 sources={}
 for fn in ("fextralife-item-pages.tsv","fextralife-acquisition-pages.tsv"):
  with (AUDIT/fn).open(encoding="utf-8",newline="") as h:
   for r in csv.DictReader(h,delimiter="\t"):sources[r["source_id"]]=r
 emitted={};stats=Counter(resolved_pages=len(capture["pages"]))
 for p in capture["pages"]:
  k=norm(p["title"]);candidates=idx.get(k,[])
  if not candidates or reserved(k):continue
  text=acquisition(content(p));links={norm(x.split("|")[-1]) for x in re.findall(r"\[\[([^\]]+)\]\]",text)}-vague;matches=[]
  for x in candidates:
   ap,flag,_region,_name,phrase=x;d=det.get(ap,{});found=sorted(q for q in links if len(q)>=6 and len(q.split())>=2 and re.search(rf"(?<![a-z0-9]){re.escape(q)}(?![a-z0-9])",phrase))
   if len(found)==1 and d.get("flag")==flag and d.get("mechanism")==MAP_LOT:matches.append((x,found[0]))
   else:stats["refused_nonunique_link_or_detection"]+=1
  counts=Counter(place for _x,place in matches)
  for (ap,flag,region,_name,phrase),place in matches:
   if counts[place]!=1:stats["refused_ambiguous_place"]+=1;continue
   rev=p["revisions"][0];pid,rid=int(p["pageid"]),int(rev["revid"]);sid=f"wiki:fextralife:page-{pid}:revision-{rid}"
   if sid not in sources:
    stats["refused_unpinned_page"]+=1;continue
   if sources[sid]["revision_sha1"]!=rev["sha1"]:raise ValueError(f"revision mismatch: {sid}")
   value={"ap_description_anchor":phrase,"flag":flag,"item_name":p["title"],"region":region,"source_place_anchor":place}
   emitted[ap]={"lead_id":f"fextralife-linked-place-page-{pid}-revision-{rid}-check-{ap}","subject_kind":"check","subject_id":str(ap),"claim_kind":"identity_region","normalized_value":json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")),"source_ids":sid,"independence_families":"gameplay-wiki:fextralife","disposition":"lead_only","game_version":"unknown","exact_citations":f"fextralife:pageid-{pid}:revision-{rid}:where-to-find-link:{place};project:check:{ap}/detection;flag-{flag}","summary":f"Fextralife revision {rid} links {place} in its {p['title']} acquisition guide; that exact multiword place occurs in one same-item AP description with map-lot flag {flag}.","limitations":"Community-wiki place lead matched to a broader phrase inside the AP description and cross-checked against the current v1.17 map-lot flag. It does not prove exact coordinates, access, route order, completeness, event timing, or absence of another acquisition."}
 rows=sorted(emitted.values(),key=lambda r:r["lead_id"]);stats["matched_checks"]=len(rows);return rows,dict(sorted(stats.items()))
def render(rows):
 o=StringIO(newline="");w=csv.DictWriter(o,fieldnames=FIELDS,delimiter="\t",lineterminator="\n");w.writeheader();w.writerows(rows);return o.getvalue()
def main():
 p=argparse.ArgumentParser();p.add_argument("capture",type=Path);a=p.parse_args();rows,stats=build(json.loads(a.capture.read_text(encoding="utf-8")));OUT.write_text(render(rows),encoding="utf-8");REPORT.write_text(json.dumps(stats,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(stats,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
