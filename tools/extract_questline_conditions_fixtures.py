#!/usr/bin/env python3
"""Acceptance fixtures for the questline-condition extractor (#1085), eleven of them, reported
pass/fail as-is; nothing here is weakened to make a fixture green. F1 is the motivating case
(Fortissax f510110) and F4 is its negative control.

NEEDS THE ARTIFACTS -- decompiled EMEVD + talk ESD, licensing-restricted and absent from CI, which
is why this is a COMMAND and not a CI gate (AGENTS §5, the same footing as
`build_questline_dag.py --verify-commonarg`). Run it whenever the extractor changes, before
re-emitting greenfield/questline_conditions.tsv:

    python tools/gen_inputs.py --ensure elden_ring_artifacts
    python tools/extract_questline_conditions_fixtures.py elden_ring_artifacts [OUTDIR]
"""
import os, sys, csv, re, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_questline_conditions as q

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = sys.argv[1] if len(sys.argv) > 1 else 'elden_ring_artifacts'
OUT = sys.argv[2] if len(sys.argv) > 2 else tempfile.mkdtemp(prefix='questline_fixtures_')
C, R, rows = q.run(ART, OUT)
setters, bf, band = q.build_setters(C)
R2 = q.Resolver(C, setters, bf, band)
sg = q.spawn_gates(C)
edges = q.band_edges(C, setters, band)
res = []


def fx(name, ok, detail):
    res.append((name, "PASS" if ok else "FAIL", detail))


# F1 -- Fortissax remembrance (flag 510110)
r = [x for x in rows if str(x['flag']) == '510110']
if not r:
    fx("F1 510110 present", False, "no award site maps to flag 510110")
else:
    rule = r[0]['rule']
    fx("F1a 510110 is quest-gated (not TRUE)",
       'NPC_STATE' in rule or 'DIALOGUE_STEP' in rule,
       r[0]['designation'] + " | " + rule[:200])
    fx("F1b Deeproot (MAP_ACCESS m12_03)", 'MAP_ACCESS(m12_03)' in rule, "")
    fx("F1c Champions defeat f12030800", 'BOSS_KILL(f12030800)' in rule, "")
    fx("F1d Cursemark possession goods 8191", 'ITEM_POSSESSION(goods 8191)' in rule,
       "cone flags: %s" % sorted(R.seen_flags)[:0])

# F2 -- Fia chain
fx("F2a spawn 12030702 gated on 4128/4129",
   {4128, 4129} <= sg.get(12030702, set()), "gate=%s" % sorted(sg.get(12030702, ()))[:8])
e = [x for x in edges if x[1] == 4128 and {4127, 12030800} <= set(x[0])]
fx("F2b band edge 4127 && 12030800 -> 4128", bool(e),
   "%s" % ([(sorted(x[0]), x[2], x[3]) for x in e][:1]))
hit = []
for (rel, mach), lines in C.esd.items():
    if 't322001203' not in rel:
        continue
    for l in lines:
        if 'ComparePlayerInventoryNumber(ItemType.Goods, 8191' in l or \
           'PlayerEquipmentQuantityChange(ItemType.Goods, 8191, -1)' in l:
            hit.append((mach, l.strip()[:70]))
fx("F2c handover possession-tests goods 8191 in t322001203", bool(hit), str(hit[:2]))

# F3 -- Great Runes: flag 182 opens the capital after event 730 counts the
# held-rune band 170-179.  The sibling 190-199 counter feeds flags 160-167 and
# does not own the Leyndell seal (#1088 and the correction on #1085).
roots, unres = R2.resolve([(True, 'EventFlag(182)')], 'common.emevd.dcx.js')
fx("F3 capital gate is COUNT_FLAGS(170-179) -> f182",
   any(x.startswith('COUNT_FLAGS(170-179)') for x in roots) and
   not any(x.startswith('ITEM_POSSESSION') for x in roots),
   "roots=%s" % sorted(roots))

# F4 -- negative control: Fia's Mist f510350 must not be Fia-chain gated
neg = [x for x in rows if str(x['flag']) == '510350']
if not neg:
    fx("F4 negative control f510350", True, "not an award site in this corpus (vacuous pass)")
else:
    bad = [x for x in neg if re.search(r'NPC_STATE\(f41[23]\d\)', x['rule'])]
    fx("F4 f510350 NOT Fia-chain gated", not bad,
       (bad[0]['rule'][:160] if bad else neg[0]['designation']))

# F5 -- diff against curated QUEST_GATED_FLAGS
src = open(os.path.join(ROOT, 'greenfield', 'gen_data.py'), encoding='utf-8').read()
m = re.search(r'^QUEST_GATED_FLAGS = \{(.*?)^\}', src, re.S | re.M)
blk = "\n".join(l.split("#")[0] for l in m.group(1).splitlines()) if m else ""
cur = {int(x) for x in re.findall(r'\b(\d{3,})\b', blk)}
derived = {int(x['flag']) for x in rows
           if x['flag'] and x['designation'] == 'MISSABLE'}
derived_any = {int(x['flag']) for x in rows if x['flag'] and
               ('NPC_STATE' in x['rule'] or 'DIALOGUE_STEP' in x['rule'])}
all_flags = {int(x['flag']) for x in rows if x['flag']}
diff = dict(curated=len(cur), derived_missable=len(derived),
            derived_quest_touched=len(derived_any),
            overlap=len(cur & derived_any),
            derived_only=sorted(derived_any - cur)[:40],
            curated_only_seen_as_award=sorted((cur - derived_any) & all_flags)[:40],
            curated_not_an_award_site=len(cur - all_flags))

# F6 -- parameterised common events are expanded at EVERY concrete call site.
# 90005300 is the widest setter in this corpus (252 sites); its last binding is
# far beyond the old [:12] truncation and therefore fails if that cap returns.
boss_ev = C.events['common_func.emevd.dcx.js']['90005300']
boss_binds = C.resolve_args(boss_ev)
last_boss_flag = int(boss_binds[-1][2]['eventFlagId'])
fx("F6a 90005300 exposes all 252 concrete call sites",
   len(boss_binds) == 252 and any(s.eid == '90005300'
                                  for s in setters.get(last_boss_flag, [])),
   "bindings=%d last=f%d setters=%s" %
   (len(boss_binds), last_boss_flag,
    [(s.file, s.eid) for s in setters.get(last_boss_flag, [])]))

# A value merely passed to the same common function is not necessarily a
# setter.  In 90005703 f3360 is eventFlagId5 (read/batch-clear only), while the
# ON writes target eventFlagId/eventFlagId2.  Complete binding must preserve
# that role distinction instead of promoting every numeric argument.
fx("F6b read-only common-event params do not become setters",
   not any(s.eid == '90005703' for s in setters.get(3360, [])),
   "f3360 setters=%s" % [(s.file, s.eid) for s in setters.get(3360, [])])

json.dump(dict(fixtures=res, diff=diff,
               noise=R.noise.most_common(12),
               negatives=len(R.negatives)),
          open(os.path.join(OUT, '_fixtures.json'), 'w'), indent=1)
for n, s, d in res:
    print("%-58s %s  %s" % (n, s, d[:130]))
print(json.dumps(diff, indent=1)[:1500])
