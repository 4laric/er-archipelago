#!/usr/bin/env python3
"""Bind immutable Game8 legacy-dungeon captures to AP checks, as leads only."""
from __future__ import annotations
import argparse, csv, hashlib, importlib.util, json, re, sys, unicodedata
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/"greenfield/eldenring/data.py"
DEFAULT_OUT=ROOT/"greenfield/evidence/wiki-audit/game8-check-leads.tsv"
PAGES={
 "369673":("20260316153255","0ee6a591482b0ad2bf8ca9eabc623a54e73161ddafb4cd60c0f663b42be759d7","Raya Lucaria Academy","Academy of Raya Lucaria"),
 "369906":("20260201121746","86afcc0e8a14a63b82d7e38345c773adf065efe2ffd7d2850fccdc7192bb5382","Haligtree","Miquella's Haligtree"),
 "369958":("20260405223753","6882ca47f6993563de93535b35a6cccba57b807f6c996d1507e2550ed6f7cbe6","Caelid","Redmane Castle"),
 "370279":("20260128184241","2dad8fdf0d1f155e000662cd129e1e09eed1029b96180e9f0d660fa0693a624e","Leyndell","Leyndell, Royal Capital"),
 "371005":("20250906203009","48f5333402b5d866ac8dba8ca3ba9779eaf9553c0cb45116e4073b179095e652","Farum Azula","Crumbling Farum Azula"),
}
FIELDS=("lead_id","subject_kind","subject_id","claim_kind","normalized_value","source_ids","independence_families","disposition","game_version","exact_citations","summary","limitations")

def norm(text):
 text=unicodedata.normalize("NFKD",text).encode("ascii","ignore").decode()
 return " ".join(re.findall(r"[a-z0-9]+",text.casefold().replace("&"," and ")))
def ap_item_name(location):
 value=location.split(" :: ",1)[-1]; value=re.sub(r"\s*\[f\d+\]\s*$","",value)
 value=value.split(", may be sweep-granted",1)[0].split(" - ",1)[0]
 return re.sub(r"^\[(?:Incantation|Sorcery)\]\s*","",value).strip()

class Sections(HTMLParser):
 def __init__(self): super().__init__(convert_charrefs=True); self.in_h=False; self.hid=""; self.ht=[]; self.current=None; self.sections=[]
 def handle_starttag(self,tag,attrs):
  if tag=="h2": self.in_h=True; self.hid=dict(attrs).get("id",""); self.ht=[]
 def handle_data(self,data):
  if self.in_h: self.ht.append(data)
  elif self.current is not None: self.current[2].append(data)
 def handle_endtag(self,tag):
  if tag=="h2" and self.in_h:
   self.current=[self.hid," ".join("".join(self.ht).split()),[]]; self.sections.append(self.current); self.in_h=False

def locations():
 spec=importlib.util.spec_from_file_location("_game8_data",DATA); mod=importlib.util.module_from_spec(spec); assert spec.loader; spec.loader.exec_module(mod); return mod.LOCATIONS
def build(capture_dir):
 locs=locations(); emitted={}; stats={"pages":0,"matched_checks":0,"ambiguous_mentions":0}
 for archive_id,(timestamp,expected,region,page_title) in PAGES.items():
  body=(capture_dir/f"{archive_id}.html").read_bytes(); digest=hashlib.sha256(body).hexdigest()
  if digest!=expected: raise ValueError(f"refusing unknown Game8 capture {archive_id}: sha256 {digest}")
  stats["pages"]+=1; parser=Sections(); parser.feed(body.decode("utf-8")); by_name={}
  for location,ap_id,_flag in locs[region]: by_name.setdefault(norm(ap_item_name(location)),[]).append((ap_id,location))
  for heading_id,heading,chunks in parser.sections:
   if not any(term in heading.casefold() for term in ("walkthrough","objectives","what to do","points of interest")): continue
   section=f" {norm(' '.join(chunks))} "
   for key,candidates in by_name.items():
    if len(key)<5 or f" {key} " not in section: continue
    if len(candidates)!=1: stats["ambiguous_mentions"]+=1; continue
    ap_id,location=candidates[0]
    emitted.setdefault(ap_id,{"lead_id":f"game8-{archive_id}-{heading_id}-check-{ap_id}","subject_kind":"check","subject_id":str(ap_id),"claim_kind":"identity_region","normalized_value":json.dumps({"item_name":ap_item_name(location),"region":region},ensure_ascii=False,sort_keys=True,separators=(",",":")),"source_ids":f"wiki:game8:legacy-{archive_id}:{timestamp}","independence_families":"gameplay-guide:game8","disposition":"lead_only","game_version":"unknown","exact_citations":f"game8:{archive_id}:#{heading_id}","summary":f"Game8 names {ap_item_name(location)} in the {heading} section of its {page_title} guide; that exact item name identifies one current AP check in {region}.","limitations":"One commercial-guide family, matched only by an exact item name inside a declared AP region. This does not prove v1.17 access logic, event predicates, route order, alternate-acquisition absence, or the accuracy of AP's location suffix."})
 result=sorted(emitted.values(),key=lambda row:row["lead_id"]); stats["matched_checks"]=len(result); return result,stats
def render(rows):
 from io import StringIO
 out=StringIO(newline=""); writer=csv.DictWriter(out,fieldnames=FIELDS,delimiter="\t",lineterminator="\n"); writer.writeheader(); writer.writerows(rows); return out.getvalue()
def main():
 parser=argparse.ArgumentParser(); parser.add_argument("capture_dir",type=Path); parser.add_argument("--output",type=Path,default=DEFAULT_OUT); args=parser.parse_args()
 try: rows,stats=build(args.capture_dir)
 except (OSError,UnicodeError,ValueError) as exc: print(f"Game8 lead build failed: {exc}",file=sys.stderr); return 1
 text=render(rows)
 args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text,encoding="utf-8")
 print(json.dumps(stats,sort_keys=True)); return 0
if __name__=="__main__": raise SystemExit(main())
