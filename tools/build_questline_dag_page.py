#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_questline_dag_page.py -- an offline reader for greenfield/questline_dag.tsv.

WHY A PAGE. The tsv is 280 rows of flag ids. The question a human actually asks of it is
"what gates THIS check, and what gates that", which is a walk over a graph, and a walk is
not a thing you do in a spreadsheet. SPEC-questline-dag §6 tier 1 says to ship the graph
"and let it be read by a human for a week" -- this is the reading surface for that week.

THE UNIT OF BROWSING IS THE CLUSTER, not the edge. The graph is not one DAG: it is 136
connected components, the largest 13 nodes across. That is a fact about the data (quest
chains are small and mostly disjoint) and it is what makes a diagram legible at all -- one
component fits on a screen, all 280 edges do not. Each cluster renders as its own mermaid
graph.

🛑 A READER, NOT AN ORACLE -- the same sentence build_check_browser.py carries, for the same
reason. Every number here is a join over the committed tsv. The page cannot know anything
the table does not, and it repeats the table's own warnings rather than presenting a clean
graph as a settled one:
  * an edge is CO-OCCURRENCE plus a polarity rule, not proof;
  * `sense=unknown` (108 of 280) means the corpus does not encode the polarity -- those
    edges are drawn DASHED and must not be reasoned with;
  * absence from the graph is NOT evidence of safety. f510110 (Fortissax) is absent by
    construction, and the page says so on its face rather than in a footnote.

MERMAID FROM CDN, WITH THE SOURCE ALWAYS VISIBLE. The other offline pages in this repo are
strictly self-contained; this one needs a layout engine, and vendoring ~2 MB of minified
mermaid into a public repo is a provenance problem (PROVENANCE.md) as well as an ugly diff.
So mermaid is loaded from cdnjs and the page DEGRADES HONESTLY: if the CDN is unreachable
-- offline, locked-down box, blocked egress -- every cluster still shows its mermaid SOURCE
in a copy box, which is useful on its own and pastes into any mermaid renderer. It says
which mode it is in rather than silently rendering nothing.

DETERMINISM. The CI `generators` job diffs the committed page, so the build must be
byte-identical run to run: no timestamps, no git hash, sorted iteration throughout, LF
endings. It is stamped with data.py's `inputs_hash`, like the check browser -- a content id
that is stable across commits.

INPUT:  greenfield/questline_dag.tsv (via build_questline_dag.build(), NOT a re-parse --
        one join, one implementation, so the page and the table cannot disagree).
OUTPUT: er-archipelago-questline-dag.html (repo root, beside the other offline pages).

USAGE:
    python tools/build_questline_dag_page.py
    python tools/build_questline_dag_page.py --check   # exit 1 if the committed page is stale
"""
import argparse
import ast
import collections
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_questline_dag as dag  # noqa: E402

OUT = os.path.join(ROOT, "er-archipelago-questline-dag.html")


def _inputs_hash():
    """data.py's _GEN_STAMP.inputs_hash -- a content id stable across commits, never the
    commit sha (which would make every page rebuild a diff)."""
    path = os.path.join(ROOT, "greenfield", "eldenring", "data.py")
    text = open(path, encoding="utf-8").read()
    m = re.search(r"_GEN_STAMP\s*=\s*(\{.*?\})", text, re.S)
    return ast.literal_eval(m.group(1)).get("inputs_hash", "") if m else ""


def _clusters(edges):
    """-> [[edge, ...], ...] connected components, deterministically ordered.

    Components are found over the UNDIRECTED graph: a source shared by two checks makes
    them one questline as surely as a chain does, and splitting them would hide exactly the
    structure the page exists to show.
    """
    adj = collections.defaultdict(set)
    for e in edges:
        adj["t%d" % e["target_flag"]].add("s%d" % e["source_flag"])
        adj["s%d" % e["source_flag"]].add("t%d" % e["target_flag"])
    seen, groups = set(), []
    for node in sorted(adj):
        if node in seen:
            continue
        stack, comp = [node], set()
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            comp.add(cur)
            stack.extend(adj[cur] - seen)
        groups.append(comp)
    out = []
    for comp in groups:
        targets = {int(n[1:]) for n in comp if n[0] == "t"}
        members = sorted((e for e in edges if e["target_flag"] in targets),
                         key=lambda e: (e["target_flag"], e["source_flag"], e["tool"]))
        out.append(members)
    # Biggest first, then by lowest target flag -- stable, and it puts the interesting
    # multi-check chains where a reader lands.
    out.sort(key=lambda ms: (-len({e["target_flag"] for e in ms}), -len(ms), ms[0]["target_flag"]))
    return out


_SENSE_ARROW = {"set": "-->", "clear": "-->", "unknown": "-.->"}


def _mermaid(members, world):
    """One cluster as mermaid `graph LR` source.

    Node ids are `F<flag>` so they are stable and collision-free; mermaid chokes on the
    punctuation in real check names, so every label is quoted and sanitised. Edge labels
    carry the SENSE, because an unlabelled arrow in a graph like this reads as "requires"
    and half of these do not mean that.
    """
    lines = ["graph LR"]
    nodes, seen = [], set()
    for e in members:
        for flag, is_target in ((e["target_flag"], True), (e["source_flag"], False)):
            if flag in seen:
                continue
            seen.add(flag)
            # ONE LINE per label. Mermaid does not interpret `\\n` inside a quoted label (it
            # renders literally), and `<br/>` is stripped under securityLevel:'strict' -- which
            # this page keeps, because it embeds datamined strings. So the flag id goes inline.
            if is_target:
                shape = 'F%d["%s (f%d)"]' % (flag, _short(world.flag_name.get(flag, "check")), flag)
                cls = "chk"
            else:
                kind = ("check" if world.is_check(flag)
                        else ("npc" if flag in _NPC else "world"))
                label = ("%s (f%d)" % (_short(world.flag_name.get(flag, "")), flag)
                         if kind == "check" else "f%d" % flag)
                shape = 'F%d(["%s"])' % (flag, label)
                cls = {"check": "chk", "npc": "npc", "world": "wld"}[kind]
            nodes.append((flag, shape, cls))
    for _flag, shape, _cls in sorted(nodes):
        lines.append("  " + shape)
    # ONE ARROW per (source, target, sense). Several tsv ROWS can describe the same pair --
    # the same gate found in two events, or via two corpora -- and drawing each would put
    # parallel arrows between one pair of boxes, which reads as "two requirements" when it is
    # one requirement with two witnesses. The evidence table below the diagram still lists
    # every row, so nothing is hidden; only the DUPLICATE INK is dropped.
    drawn = set()
    for e in sorted(members, key=lambda x: (x["source_flag"], x["target_flag"], x["sense"])):
        key = (e["source_flag"], e["target_flag"], e["sense"])
        if key in drawn:
            continue
        drawn.add(key)
        arrow = _SENSE_ARROW[e["sense"]]
        label = {"set": "must be SET", "clear": "must be CLEAR",
                 "unknown": "polarity UNKNOWN"}[e["sense"]]
        lines.append("  F%d %s|%s| F%d" % (e["source_flag"], arrow, label, e["target_flag"]))
    for cls, style in (("chk", "fill:#E6F1FB,stroke:#378ADD,color:#0C447C"),
                       ("npc", "fill:#EEEDFE,stroke:#7F77DD,color:#3C3489"),
                       ("wld", "fill:#F1EFE8,stroke:#888780,color:#2C2C2A")):
        ids = sorted({"F%d" % f for f, _s, c in nodes if c == cls})
        if ids:
            lines.append("  classDef %s %s" % (cls, style))
            lines.append("  class %s %s" % (",".join(ids), cls))
    return "\n".join(lines)


def _short(name, width=46):
    """A check name trimmed for a diagram box, with the region prefix kept (it is half the
    identity) and the mermaid-hostile punctuation removed."""
    name = (name or "").replace("::", "·")
    name = re.sub(r"\s*\[f\d+\]\s*$", "", name)
    name = name.replace('"', "'").replace("[", "(").replace("]", ")")
    name = " ".join(name.split())
    return name if len(name) <= width else name[:width - 1] + "…"


_NPC = set()


def build_page():
    global _NPC
    edges, tally, notes = dag.build()
    world = notes["world"]
    _NPC = {e["source_flag"] for e in edges if e["source_kind"] == "npc_state"}
    groups = _clusters(edges)
    summary = dag.summarise(edges, tally, notes)
    acceptance = dag._acceptance(edges)

    payload = []
    for idx, members in enumerate(groups):
        targets = sorted({e["target_flag"] for e in members})
        regions = sorted({e["target_region"] for e in members if e["target_region"]})
        payload.append({
            "i": idx,
            "title": _short(world.flag_name.get(targets[0], "f%d" % targets[0]), 70),
            "targets": len(targets),
            "regions": regions,
            "senses": sorted({e["sense"] for e in members}),
            "tools": sorted({e["tool"] for e in members}),
            "cross": any(e["cross_region"] == "yes" for e in members),
            "untagged": any(world.flag_ap.get(e["target_flag"]) not in world.missable
                            for e in members),
            "semantics": sorted({e["group_semantics"] for e in members}),
            "mermaid": _mermaid(members, world),
            "search": " ".join(sorted({
                str(e["target_flag"]) for e in members} | {
                str(e["source_flag"]) for e in members} | {
                (world.flag_name.get(e["target_flag"]) or "") for e in members} | set(regions))).lower(),
            "rows": [{
                "s": e["source_flag"], "t": e["target_flag"], "sense": e["sense"],
                "basis": e["basis"], "tool": e["tool"], "sreg": e["source_region"],
                "treg": e["target_region"], "loc": e["source_locator"],
                "kind": e["source_kind"], "sem": e["group_semantics"],
                "name": world.flag_name.get(e["target_flag"], ""),
                "tag": world.flag_ap.get(e["target_flag"]) in world.missable,
                "ev": e["evidence"],
            } for e in members],
        })
    return payload, summary, acceptance, edges


_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Elden Ring Archipelago -- questline DAG</title>
<style>
:root{--bg:#faf9f7;--card:#fff;--ink:#1a1a19;--dim:#5f5e5a;--line:#e1e0d9;--acc:#185fa5;
--warnbg:#faece7;--warnink:#712b13;--okbg:#e1f5ee;--okink:#0f6e56}
@media(prefers-color-scheme:dark){:root{--bg:#141413;--card:#1f1f1e;--ink:#ecebe4;--dim:#a3a29b;
--line:#33322f;--acc:#85b7eb;--warnbg:#3b1c10;--warnink:#f0997b;--okbg:#0d2c24;--okink:#5dcaa5}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 ui-sans-serif,system-ui,'Segoe UI',sans-serif}
header{padding:22px 26px;border-bottom:1px solid var(--line)}
h1{margin:0 0 4px;font-size:20px;font-weight:600}
.sub{color:var(--dim);font-size:13px}
.banner{margin:14px 26px 0;padding:12px 14px;border-left:3px solid #d85a30;background:var(--warnbg);
color:var(--warnink);font-size:13px;border-radius:0}
.banner b{font-weight:600}
.stats{display:flex;flex-wrap:wrap;gap:10px;padding:16px 26px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 14px;min-width:104px}
.stat .n{font-size:20px;font-weight:600}.stat .l{font-size:12px;color:var(--dim)}
main{display:grid;grid-template-columns:330px 1fr;gap:0;align-items:start}
#side{border-right:1px solid var(--line);height:calc(100vh - 60px);overflow:auto;padding:14px}
#pane{padding:18px 26px 60px}
input,select{font:inherit;padding:6px 9px;border:1px solid var(--line);border-radius:6px;
background:var(--card);color:var(--ink);width:100%;margin-bottom:8px}
.filters{display:flex;gap:6px;margin-bottom:10px}.filters select{margin:0}
.item{padding:8px 10px;border:1px solid var(--line);border-radius:6px;background:var(--card);
margin-bottom:6px;cursor:pointer}
.item:hover{border-color:var(--acc)}.item.on{border-color:var(--acc);box-shadow:inset 3px 0 0 var(--acc)}
.item .t{font-size:13px;font-weight:600;line-height:1.35}
.item .m{font-size:11px;color:var(--dim);margin-top:3px}
.pill{display:inline-block;font-size:10px;padding:1px 6px;border-radius:9px;border:1px solid var(--line);margin-right:4px}
.pill.x{background:var(--warnbg);color:var(--warnink);border-color:#d85a30}
.pill.g{background:var(--okbg);color:var(--okink);border-color:#1d9e75}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin-top:16px}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--dim);font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.04em}
code,pre{font-family:ui-monospace,'SF Mono',Menlo,monospace;font-size:12px}
pre{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto}
details{margin-top:14px}summary{cursor:pointer;color:var(--dim);font-size:13px}
.mer{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:14px;overflow:auto}
.legend{font-size:12px;color:var(--dim);margin:10px 0 0}
.legend span{margin-right:14px}
.sw{display:inline-block;width:10px;height:10px;border-radius:2px;vertical-align:-1px;margin-right:4px}
#mode{font-size:12px;color:var(--dim);padding:6px 26px}
</style></head><body>
<header>
<h1>Questline DAG &mdash; tier 1</h1>
<div class="sub">__SUB__</div>
</header>
<div class="banner">
<b>A reader, not an oracle.</b> Nothing in the world reads this graph &mdash; every check named here
still carries its missable tag. An edge is <b>co-occurrence plus a polarity rule, not proof</b>, and a
dashed edge (<code>sense=unknown</code>) means the corpus does not encode the polarity: do not reason
with those. <b>Absence is not safety.</b> Every corpus feeding this reads an AWARD SITE, so a questline
that gates whether a <i>fight exists</i> leaves no trace &mdash; <code>f510110</code> (Fortissax), the
case the spec was written from, is absent here <b>by construction</b>.
</div>
<div class="stats" id="stats"></div>
<div id="mode"></div>
<main>
<div id="side">
<input id="q" placeholder="search name, region, flag id&hellip;" autocomplete="off">
<div class="filters">
<select id="fs"><option value="">any sense</option><option>set</option><option>clear</option><option>unknown</option></select>
<select id="ft"><option value="">any corpus</option><option>lot_gates</option><option>esd_gifts</option><option>treasure_enablers</option></select>
</div>
<div class="filters">
<select id="fx"><option value="">all clusters</option><option value="cross">cross-region only</option><option value="untag">untagged target only</option><option value="sem">claims any/all</option></select>
</div>
<div id="list"></div>
</div>
<div id="pane"></div>
</main>
<script id="data" type="application/json">__DATA__</script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js"></script>
<script>__JS__</script>
</body></html>
"""

_JS = r"""
var D = JSON.parse(document.getElementById('data').textContent);
var CL = D.clusters, cur = 0, MER = false;
document.getElementById('stats').innerHTML = D.stats.map(function(s){
  return '<div class="stat"><div class="n">'+s[1]+'</div><div class="l">'+s[0]+'</div></div>';}).join('');
function match(c){
  var q=document.getElementById('q').value.toLowerCase().trim();
  var s=document.getElementById('fs').value, t=document.getElementById('ft').value, x=document.getElementById('fx').value;
  if(q && c.search.indexOf(q)<0) return false;
  if(s && c.senses.indexOf(s)<0) return false;
  if(t && c.tools.indexOf(t)<0) return false;
  if(x==='cross' && !c.cross) return false;
  if(x==='untag' && !c.untagged) return false;
  if(x==='sem' && !(c.semantics.indexOf('any')>=0 || c.semantics.indexOf('all')>=0)) return false;
  return true;
}
function list(){
  var out=[], n=0;
  CL.forEach(function(c){
    if(!match(c)) return; n++;
    out.push('<div class="item'+(c.i===cur?' on':'')+'" data-i="'+c.i+'">'
      +'<div class="t">'+esc(c.title)+'</div><div class="m">'
      +(c.targets>1?'<span class="pill">'+c.targets+' checks</span>':'')
      +(c.cross?'<span class="pill x">cross-region</span>':'')
      +(c.semantics.indexOf('any')>=0?'<span class="pill g">any</span>':'')
      +(c.semantics.indexOf('all')>=0?'<span class="pill g">all</span>':'')
      +esc(c.regions.join(', '))+'</div></div>');
  });
  document.getElementById('list').innerHTML =
    '<div class="legend">'+n+' of '+CL.length+' clusters</div>'+out.join('');
  [].forEach.call(document.querySelectorAll('.item'), function(el){
    el.onclick=function(){ cur=+el.dataset.i; list(); show(); };
  });
}
function esc(s){var d=document.createElement('div'); d.textContent=s==null?'':s; return d.innerHTML;}
function show(){
  var c=CL[cur], p=document.getElementById('pane');
  var rows=c.rows.map(function(r){
    return '<tr><td><code>f'+r.s+'</code><div class="m">'+esc(r.kind)+(r.sreg?' &middot; '+esc(r.sreg):'')+'</div></td>'
      +'<td><b>'+(r.sense==='set'?'must be SET':r.sense==='clear'?'must be CLEAR':'UNKNOWN')+'</b>'
      +'<div class="m"><code>'+esc(r.basis)+'</code></div></td>'
      +'<td><code>f'+r.t+'</code> '+esc(r.name)+'<div class="m">'+esc(r.treg)
      +(r.tag?' &middot; missable-tagged':' &middot; <b>not tagged</b>')+'</div></td>'
      +'<td>'+esc(r.tool)+'<div class="m">'+esc(r.loc||'unplaced')+' &middot; group '+esc(r.sem)+'</div></td></tr>';
  }).join('');
  p.innerHTML='<h2 style="margin:0 0 2px;font-size:17px">'+esc(c.title)+'</h2>'
    +'<div class="sub">'+esc(c.regions.join(', '))+' &middot; '+c.rows.length+' edge(s) over '+c.targets+' check(s)</div>'
    +'<div class="mer" id="mer"></div>'
    +'<div class="legend"><span><span class="sw" style="background:#85b7eb"></span>check</span>'
    +'<span><span class="sw" style="background:#afa9ec"></span>NPC state (an ESD sets it)</span>'
    +'<span><span class="sw" style="background:#b4b2a9"></span>world flag</span>'
    +'<span>solid = polarity known &middot; dashed = unknown, unusable</span></div>'
    +'<table><thead><tr><th>source flag</th><th>sense</th><th>gated check</th><th>corpus</th></tr></thead><tbody>'
    +rows+'</tbody></table>'
    +'<details><summary>evidence, verbatim</summary><pre>'
    +esc(c.rows.map(function(r){return 'f'+r.s+' -> f'+r.t+'  ['+r.tool+']\n    '+r.ev;}).join('\n'))
    +'</pre></details>'
    +'<details><summary>mermaid source</summary><pre>'+esc(c.mermaid)+'</pre></details>';
  var box=document.getElementById('mer');
  if(MER){
    var id='m'+cur+'_'+Date.now();
    mermaid.render(id, c.mermaid).then(function(o){ box.innerHTML=o.svg; })
      .catch(function(e){ box.innerHTML='<pre>'+esc(c.mermaid)+'</pre>'; });
  } else {
    box.innerHTML='<pre>'+esc(c.mermaid)+'</pre>';
  }
}
['q','fs','ft','fx'].forEach(function(id){
  document.getElementById(id).oninput=function(){ list(); };
});
if(typeof mermaid!=='undefined'){
  MER=true;
  mermaid.initialize({startOnLoad:false, securityLevel:'strict',
    theme: matchMedia('(prefers-color-scheme: dark)').matches?'dark':'default'});
  document.getElementById('mode').innerHTML='Diagrams rendered with mermaid.';
} else {
  document.getElementById('mode').innerHTML='<b>mermaid could not be loaded</b> (offline, or the CDN is '
    +'blocked). Every cluster still shows its mermaid SOURCE below &mdash; copy it into any mermaid '
    +'renderer. Nothing else on this page depends on the network.';
}
list(); show();
"""


def render():
    payload, summary, acceptance, edges = build_page()
    senses = collections.Counter(e["sense"] for e in edges)
    stats = [
        ["clusters", len(payload)],
        ["edges", len(edges)],
        ["checks", len({e["target_flag"] for e in edges})],
        ["prerequisites", senses["set"]],
        ["exclusions", senses["clear"]],
        ["unusable", senses["unknown"]],
    ]
    sub = ("%d edges over %d checks, in %d disjoint clusters &middot; inputs_hash %s &middot; "
           "generated by tools/build_questline_dag_page.py from greenfield/questline_dag.tsv"
           % (len(edges), len({e["target_flag"] for e in edges}), len(payload),
              html.escape(_inputs_hash()[:23])))
    data = json.dumps({"clusters": payload, "stats": stats,
                       "summary": summary,
                       "acceptance": [[bool(ok), lab, det] for ok, lab, det in acceptance]},
                      sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return (_HTML.replace("__SUB__", sub)
            .replace("__DATA__", data.replace("</", "<\\/"))
            .replace("__JS__", _JS))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed page differs from a fresh build")
    args = ap.parse_args(argv)
    page = render()
    # Determinism is not optional: the CI generators job diffs this file, so a build that
    # varied run to run would make that gate permanently red rather than meaningful.
    if page != render():
        sys.exit("FATAL: two builds from the same inputs differ. Something unsorted or "
                 "time-dependent crept in; the CI diff gate would go permanently red.")
    if args.check:
        if not os.path.isfile(OUT):
            print("DRIFT: %s does not exist." % OUT, file=sys.stderr)
            return 1
        if open(OUT, encoding="utf-8", newline="").read() != page:
            print("DRIFT: er-archipelago-questline-dag.html is STALE -- run "
                  "`python tools/build_questline_dag_page.py`.", file=sys.stderr)
            return 1
        print("--check: committed page matches a fresh build")
        return 0
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(page)
    print("wrote %s (%d bytes, %d clusters)"
          % (os.path.relpath(OUT, ROOT), len(page.encode("utf-8")), len(payload_count(page))))
    return 0


def payload_count(page):
    m = re.search(r'<script id="data" type="application/json">(.*?)</script>', page, re.S)
    return json.loads(m.group(1).replace("<\\/", "</"))["clusters"] if m else []


if __name__ == "__main__":
    sys.exit(main())
