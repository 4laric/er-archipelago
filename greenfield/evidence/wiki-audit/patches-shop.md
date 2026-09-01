# Gameplay-wiki audit pilot: Patches' shop state

This second #1273 pilot examines one concrete check from #1271's Patches shop regression: Margit's
Shackle (AP 7770235). It records two vanilla acquisition-route leads and makes no gameplay-rule
change. The sources are independent commercial guides, but neither claims current v1.17 behavior;
both leads therefore remain `lead_only`.

## Sources and reproducibility

`sources.tsv` records immutable Internet Archive revision URLs, author and publisher metadata,
publication/modification/archive dates, page-body SHA-256, license disposition, and patch scope.
Retrieve each revision with `curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL`, then compare its
SHA-256. No source prose is redistributed: `leads.tsv` contains short paraphrases and section
anchors only.

Game8 credits its Elden Ring walkthrough team and explicitly discusses the patch 1.04 quest
extension. Gamer Guides credits Ben Chard and does not state a game version. Those authorship lines
make the pages independent of each other; multiple sections within one page remain one family.
Neither page promotes the other to v1.17 evidence.

## Findings

The pages agree on two Patches shop routes:

1. In Murkwater Cave, ending the encounter without killing Patches and then returning or reloading
   makes his shop available. Gamer Guides names Margit's Shackle in that stock.
2. Later, Patches moves to Scenic Isle in Liurnia and sets up shop again. Both guides warn through
   their route descriptions that later progress can skip this phase.

These are normalized as separate `alternate_acquisition` leads for AP 7770235. They must not be
collapsed into an AND rule, and neither says that merely owning a region lock is sufficient.

## Comparison with current logic

Current generated data labels AP 7770235 as `from Patches or Thiollier`, and the reviewed site set
in `test_gf_hub_collapsed_merchant_sites.py` is Limgrave, Mt. Gelmir, and Cerulean. The two guide
families independently identify a Patches shop in Liurnia, which is absent from that set. This is a
specific coverage gap, not authority to add Liurnia immediately: the current row also represents a
Thiollier route, and the wiki pages do not adjudicate shared ShopLineupParam semantics, Patches'
Bell Bearing, or exact v1.17 state flags.

The correct future model is a disjunction of typed merchant-state routes. Stronger evidence must
identify the exact Patches shop-release/state predicates and separately model the Thiollier and
bell-bearing routes before this lead changes placement logic.
