#!/usr/bin/env python3
"""Build the v0.6 Phase-1 evidence audit browser from its temporary fixture contract.

This is deliberately a reader only. It does not adjudicate claims, adapt a production corpus,
change runtime tables, or participate in regen_all yet; #1213 owns that integration. The small
checked-in fixture makes the browser's identity/region display contract reviewable now without
pretending the future ledger emitter already exists.

Run: python3 tools/build_evidence_browser.py [--check] [--out PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "greenfield", "evidence", "browser_fixture.json")
OUT_HTML = os.path.join(REPO, "er-archipelago-evidence-browser.html")

STATUSES = {"proven", "corroborated", "single_source", "conflicted", "inferred", "unverified"}
RISKS = {"critical", "high", "medium", "low"}
CLAIM_KINDS = {"identity", "region"}
STANCES = {"supports", "contradicts", "silent", "ambiguous"}
REQUIRED_CLAIM = {
    "claim_id", "claim_kind", "value", "status", "risk", "last_reviewed",
    "review_issue", "graduation", "evidence",
}
REQUIRED_EVIDENCE = {
    "evidence_id", "family_id", "source_title", "source_version", "stance",
    "citation", "method", "lineage",
}


def canonical_bytes(contract: dict) -> bytes:
    return json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def validate(contract: dict) -> None:
    if contract.get("schema") != "evidence-browser-fixture-v1":
        raise ValueError("fixture schema must be evidence-browser-fixture-v1")
    checks = contract.get("checks")
    if not isinstance(checks, list) or not checks:
        raise ValueError("fixture must carry a non-empty checks list")
    seen_checks, seen_claims, seen_evidence = set(), set(), set()
    for check in checks:
        check_id = check.get("check_id")
        if not isinstance(check_id, int) or check_id in seen_checks:
            raise ValueError(f"check_id must be a unique integer: {check_id!r}")
        seen_checks.add(check_id)
        if not str(check.get("name", "")).strip():
            raise ValueError(f"check {check_id} has no name")
        kinds = set()
        for claim in check.get("claims", []):
            missing = REQUIRED_CLAIM - claim.keys()
            if missing:
                raise ValueError(f"check {check_id} claim missing {sorted(missing)}")
            expected_prefix = f"check:{check_id}/"
            claim_id = claim["claim_id"]
            if not claim_id.startswith(expected_prefix) or claim_id in seen_claims:
                raise ValueError(f"unstable or duplicate claim_id: {claim_id!r}")
            seen_claims.add(claim_id)
            kind = claim["claim_kind"]
            if kind not in CLAIM_KINDS or claim_id != expected_prefix + kind or kind in kinds:
                raise ValueError(f"bad or duplicate claim kind for check {check_id}: {kind!r}")
            kinds.add(kind)
            if claim["status"] not in STATUSES or claim["risk"] not in RISKS:
                raise ValueError(f"closed vocabulary violation in {claim_id}")
            evidence = claim["evidence"]
            if not isinstance(evidence, list):
                raise ValueError(f"evidence must be a list in {claim_id}")
            for row in evidence:
                missing = REQUIRED_EVIDENCE - row.keys()
                if missing:
                    raise ValueError(f"{claim_id} evidence missing {sorted(missing)}")
                if row["stance"] not in STANCES:
                    raise ValueError(f"unknown evidence stance {row['stance']!r}")
                if not row["citation"].strip() or not row["family_id"].strip():
                    raise ValueError(f"{claim_id} evidence needs an exact citation and family")
                if row["evidence_id"] in seen_evidence:
                    raise ValueError(f"duplicate evidence_id: {row['evidence_id']}")
                seen_evidence.add(row["evidence_id"])
        if kinds != CLAIM_KINDS:
            raise ValueError(f"Phase 1 check {check_id} needs exactly identity and region claims")


def load_fixture(path: str = FIXTURE) -> dict:
    with open(path, encoding="utf-8") as fh:
        contract = json.load(fh)
    validate(contract)
    contract = json.loads(canonical_bytes(contract))
    contract["inputs_hash"] = "sha256:" + hashlib.sha256(canonical_bytes(contract)).hexdigest()
    return contract


def render(contract: dict) -> str:
    payload = json.dumps(contract, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    stamp = contract["inputs_hash"]
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="evidence-inputs-hash" content="{stamp}">
<title>ER Archipelago evidence audit</title>
<style>
:root{{--bg:#0b1118;--panel:#121b25;--panel2:#182431;--line:#2b3b4d;--text:#e8eef5;--muted:#9fb0c2;--gold:#e8bd62;--red:#ff786f;--green:#75d69c;--blue:#75baff}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.45 system-ui,sans-serif}}
header{{padding:24px clamp(18px,4vw,54px);border-bottom:1px solid var(--line);background:linear-gradient(120deg,#152537,#0b1118)}}
h1{{margin:0 0 6px;font-size:clamp(24px,4vw,38px)}} h2,h3{{margin:.4rem 0}} .muted{{color:var(--muted)}} code{{color:#b9d9ff}}
.layout{{display:grid;grid-template-columns:minmax(330px,42%) 1fr;min-height:calc(100vh - 126px)}}
.queue,.detail{{padding:20px;overflow:auto}} .queue{{border-right:1px solid var(--line)}}
.filters{{display:grid;grid-template-columns:2fr repeat(4,1fr);gap:8px;position:sticky;top:0;background:var(--bg);padding-bottom:14px;z-index:2}}
input,select,button{{width:100%;padding:9px;border:1px solid var(--line);border-radius:7px;background:var(--panel);color:var(--text)}} button{{cursor:pointer}}
.row{{display:grid;grid-template-columns:1fr auto;gap:8px;padding:12px;margin:7px 0;border:1px solid var(--line);border-radius:9px;background:var(--panel);cursor:pointer}}
.row:hover,.row.active{{border-color:var(--blue);background:var(--panel2)}} .badges{{display:flex;gap:5px;flex-wrap:wrap;margin-top:5px}}
.badge{{font-size:12px;padding:2px 7px;border-radius:20px;border:1px solid var(--line)}} .conflicted,.contradicts{{color:var(--red);border-color:#81433f}} .proven,.supports{{color:var(--green)}}
.high,.critical{{color:#ffb36b}} .questions{{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0}}
.answer,.family{{padding:13px;border:1px solid var(--line);border-radius:9px;background:var(--panel)}} .answer h3{{font-size:14px;color:var(--gold)}}
.family{{margin:9px 0}} .evidence{{padding:10px 0;border-top:1px solid var(--line)}} .citation{{padding:7px;background:#0b141e;border-radius:5px;overflow-wrap:anywhere}}
.alert{{padding:10px;border:1px solid #81433f;background:#2a1718;color:#ffd2cf;border-radius:7px;margin:10px 0}}
.toolbar{{display:flex;gap:8px;align-items:center}} .toolbar button{{width:auto}} .empty{{padding:20px;color:var(--muted)}}
@media(max-width:900px){{.layout{{display:block}}.queue{{border-right:0;border-bottom:1px solid var(--line)}}.filters{{grid-template-columns:1fr 1fr}}.questions{{grid-template-columns:1fr}}}}
</style></head><body>
<header><h1>Evidence audit · Phase 1</h1><div class="muted">Identity and region claims from a deterministic fixture contract · reader only · <code>{stamp}</code></div></header>
<main class="layout"><section class="queue"><div class="filters">
<input id="q" aria-label="Search" placeholder="Search check, claim, value, citation">
<select id="status" aria-label="Status"><option value="">All statuses</option></select>
<select id="risk" aria-label="Risk"><option value="">All risks</option></select>
<select id="kind" aria-label="Claim kind"><option value="">All claim kinds</option></select>
<select id="family" aria-label="Evidence family"><option value="">All families</option></select></div>
<div class="toolbar"><strong id="count"></strong><span class="muted">risk-ranked audit queue</span></div><div id="rows"></div></section>
<section class="detail" id="detail"><p class="empty">Select a claim to inspect its evidence.</p></section></main>
<script id="evidence-payload" type="application/json">{payload}</script>
<script>
const DATA=JSON.parse(document.getElementById('evidence-payload').textContent);
const claims=DATA.checks.flatMap(c=>c.claims.map(x=>({{...x,check_id:c.check_id,check_name:c.name}})));
const riskRank={{critical:0,high:1,medium:2,low:3}}, statusRank={{conflicted:0,unverified:1,inferred:2,single_source:3,corroborated:4,proven:5}};
const els=Object.fromEntries(['q','status','risk','kind','family','rows','count','detail'].map(x=>[x,document.getElementById(x)]));
function values(key){{return [...new Set(claims.flatMap(c=>key==='family'?c.evidence.map(e=>e.family_id):[c[key]]))].sort()}}
function options(el,vals){{for(const v of vals){{const o=document.createElement('option');o.value=v;o.textContent=v;el.append(o)}}}}
options(els.status,values('status'));options(els.risk,values('risk'));options(els.kind,values('claim_kind'));options(els.family,values('family'));
function readHash(){{const p=new URLSearchParams(location.hash.slice(1));for(const k of ['q','status','risk','kind','family'])if(p.has(k))els[k].value=p.get(k);return p.get('claim')||''}}
function writeHash(selected){{const p=new URLSearchParams();for(const k of ['q','status','risk','kind','family'])if(els[k].value)p.set(k,els[k].value);if(selected)p.set('claim',selected);history.replaceState(null,'','#'+p.toString())}}
function text(c){{return JSON.stringify(c).toLowerCase()}}
function filtered(){{const q=els.q.value.trim().toLowerCase();return claims.filter(c=>(!q||text(c).includes(q))&&(!els.status.value||c.status===els.status.value)&&(!els.risk.value||c.risk===els.risk.value)&&(!els.kind.value||c.claim_kind===els.kind.value)&&(!els.family.value||c.evidence.some(e=>e.family_id===els.family.value))).sort((a,b)=>riskRank[a.risk]-riskRank[b.risk]||statusRank[a.status]-statusRank[b.status]||a.check_id-b.check_id||a.claim_kind.localeCompare(b.claim_kind))}}
function badge(s,extra=''){{return `<span class="badge ${{s}} ${{extra}}">${{escapeHtml(s)}}</span>`}}
function escapeHtml(s){{return String(s).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c]))}}
function show(c){{
 const families=Map.groupBy?Map.groupBy(c.evidence,e=>e.family_id):c.evidence.reduce((m,e)=>(m.set(e.family_id,[...(m.get(e.family_id)||[]),e]),m),new Map());
 const contradictions=c.evidence.filter(e=>e.stance==='contradicts'||e.stance==='ambiguous');
 const identity=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='identity');
 const region=claims.find(x=>x.check_id===c.check_id&&x.claim_kind==='region');
 const why=identity?`Identity ${{escapeHtml(JSON.stringify(identity.value))}} · ${{identity.status}}`:'No identity claim in this phase.';
 const reach=region?`Filed in ${{escapeHtml(JSON.stringify(region.value))}}. Phase 1 establishes ownership evidence, not the complete access path.`:'No region evidence in this phase.';
 const disagree=contradictions.length?contradictions.map(e=>`${{e.family_id}}: ${{e.citation}}`).join(' · '):'No active contradiction is represented in this fixture.';
 let html=`<div class="toolbar"><div><h2>${{escapeHtml(c.check_name)}}</h2><div class="muted">${{c.claim_id}} · check ${{c.check_id}}</div></div><button id="copy">Copy permalink</button></div>`;
 html+=`<div class="badges">${{badge(c.claim_kind)}}${{badge(c.status)}}${{badge(c.risk)}}</div>`;
 if(c.status==='conflicted')html+=`<div class="alert"><strong>Conflict is active.</strong> Contradicting evidence remains visible below; the current value does not erase it.</div>`;
 html+=`<div class="questions"><div class="answer"><h3>1. Why is this check here?</h3>${{why}}</div><div class="answer"><h3>2. What says the player can reach and collect it?</h3>${{reach}}</div><div class="answer"><h3>3. What disagrees with that answer?</h3>${{escapeHtml(disagree)}}</div><div class="answer"><h3>4. What evidence would graduate it?</h3>${{escapeHtml(c.graduation)}}</div></div>`;
 html+=`<div class="answer"><h3>Current claim</h3><strong>${{escapeHtml(JSON.stringify(c.value))}}</strong><div class="muted">reviewed ${{c.last_reviewed}} · ${{escapeHtml(c.review_issue)}}</div></div><h3>Evidence by independent family (${{families.size}})</h3>`;
 for(const [family,rows] of [...families].sort((a,b)=>a[0].localeCompare(b[0]))){{html+=`<div class="family"><strong>${{escapeHtml(family)}}</strong><span class="muted"> · ${{rows.length}} row(s), one witness family</span>`;for(const e of rows)html+=`<div class="evidence"><div>${{badge(e.stance)}} <strong>${{escapeHtml(e.source_title)}}</strong> · version ${{escapeHtml(e.source_version)}}</div><div class="citation">${{escapeHtml(e.citation)}}</div><div class="muted">${{escapeHtml(e.method)}} · ${{escapeHtml(e.lineage)}}<br><code>${{escapeHtml(e.evidence_id)}}</code></div></div>`;html+='</div>'}}
 els.detail.innerHTML=html;document.getElementById('copy').onclick=()=>navigator.clipboard?.writeText(location.href);writeHash(c.claim_id);
}}
let selected=readHash();function render(){{const rows=filtered();els.count.textContent=`${{rows.length}} / ${{claims.length}} claims`;els.rows.innerHTML=rows.length?'':'<p class="empty">No claims match this permalink/filter.</p>';for(const c of rows){{const d=document.createElement('div');d.className='row'+(c.claim_id===selected?' active':'');d.innerHTML=`<div><strong>${{escapeHtml(c.check_name)}}</strong><div class="muted">${{c.claim_kind}} · ${{escapeHtml(JSON.stringify(c.value))}}</div><div class="badges">${{badge(c.status)}}${{badge(c.risk)}}${{c.evidence.some(e=>e.stance==='contradicts')?badge('conflict','contradicts'):''}}</div></div><code>${{c.check_id}}</code>`;d.onclick=()=>{{selected=c.claim_id;render();show(c)}};els.rows.append(d)}}if(selected){{const c=claims.find(x=>x.claim_id===selected);if(c)show(c);else els.detail.innerHTML='<div class="alert">This permalink names a claim that is absent from this build.</div>'}}writeHash(selected)}}
for(const k of ['q','status','risk','kind','family'])els[k].addEventListener(k==='q'?'input':'change',()=>{{selected='';render()}});window.addEventListener('hashchange',()=>{{selected=readHash();render()}});render();
</script></body></html>'''


def build(out_path: str = OUT_HTML) -> bytes:
    return render(load_fixture()).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=OUT_HTML)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    blob = build(args.out)
    if args.check:
        try:
            with open(args.out, "rb") as fh:
                current = fh.read()
        except FileNotFoundError:
            current = b""
        if current != blob:
            print(f"STALE: {args.out}; run python3 tools/build_evidence_browser.py")
            return 1
        print(f"OK: {args.out} ({len(blob)} bytes)")
        return 0
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(prefix=".evidence-browser-", dir=os.path.dirname(os.path.abspath(args.out)))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(blob)
        os.replace(temp_path, args.out)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    print(f"wrote {args.out} ({len(blob)} bytes; {load_fixture()['inputs_hash']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
