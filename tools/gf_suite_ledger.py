#!/usr/bin/env python3
"""The suite ledger: every repo-only test suite is EITHER run by a CI job OR explicitly dark.

WHY (inert-test audit finding #3, 2026-08-04). The `generators` CI job used to run a hand-typed
list of 12 suite names. Anything that skips in the installed-world `tests` job and is missing from
that list runs NOWHERE except the dev box -- and that is precisely how test_gf_scadu_supply's
client-rung mirror and test_gf_data's client-table gates fell dark: their sibling
(scaling_ladder_mirror) was in the list, they were not, and a green run looks identical either way.

So the list is now DERIVED, not typed:

  * this file is the single ledger; `--generators-list` emits the loop the workflow iterates
    (.github/workflows/tests.yaml), so a suite cannot be "in CI" without a ledger row;
  * `--check` scans greenfield/eldenring/tests/ for the repo-only SENTINELS (REPO_ONLY_REASON,
    elden_ring_artifacts, the client checkout path, find_repo_root, tools/gen_manifest,
    tools/upgrade_costs). Any sentinel-bearing suite that is not ledgered fails RED. A new
    repo-only suite therefore cannot be silently dark: its author must either put it in a CI
    bucket or write down, in this file, why it only runs on the dev box.

The three buckets, and what enforces each claim:

  GENERATORS   -- run as __main__ scripts by the `generators` job (AP-free, repo tree + client at
                  the gitlink). Enforced by the job itself: the loop is generated from this list.
  TESTS_JOB    -- run under pytest in the `tests` job (installed world; artifacts materialised
                  from the gen_inputs bundle; client checked out at the gitlink beside the repo).
                  Partial skips inside these suites are pinned, per reason family and count, by
                  tests/expected_skips_ci.json (gf_test.py --skip-census) -- if one of these
                  re-darkens, the census goes red, not green.
  DEV_BOX_ONLY -- every test in the suite skips in CI, with the honest reason recorded here.
                  Their skip counts are ALSO census families, so one of them silently waking or
                  growing goes red too.

Run:  python tools/gf_suite_ledger.py --check
      python tools/gf_suite_ledger.py --generators-list
"""
import argparse
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.join(REPO, "greenfield", "eldenring", "tests")

# A file containing any of these is claiming it needs something the installed world does not have
# (the repo tree, the extracted artifact bundle, the client checkout, or a tools/ script) -- i.e.
# it CAN go dark, so it MUST be ledgered.
SENTINELS = re.compile(
    r"REPO_ONLY_REASON|elden_ring_artifacts|from-software-archipelago-clients|find_repo_root"
    r"|tools/gen_manifest|tools/upgrade_costs")

# The 12 names the workflow loop used to hand-type, in the same order. `--generators-list` is now
# the only place they are written down.
GENERATORS = [
    "region_selection",
    "check_browser",
    "desc_triage",
    "provenance_gate",
    "questline_dag",
    "shipping_yaml_recipe",
    "scaling_ladder_mirror",
    "client_contract_paths",
    "client_can_sell_mirror",
    "client_resets_are_called",
    "contract_versions",
    "wizard_blob_sync",
    "infinite_shop_rows_are_browsable_shelves",
    # PlayRegion ground audit (#445): joins data.LOCATIONS x item_grace_coords.tsv x
    # play_region_buckets.tsv x region_groups.PLAY_REGION_GROUPS. Every input is committed and
    # none of them is installed beside the world, so it skips in the `tests` job and belongs
    # here. AP-free, no artifacts, no client.
    "check_ground_regions",
]

# Suites that run in the `tests` job (installed world + ensured artifacts + client at the gitlink).
# value = why the inputs are reachable there. Remaining per-test skips inside them are census
# families in expected_skips_ci.json.
TESTS_JOB = {
    "boss_geography": "committed greenfield data; artifact-dependent halves covered by the bundle",
    "capital_reconciler": "committed data only; sentinel is a comment/reference",
    "data": "client tables read from the gitlink checkout the tests job now makes",
    "finale": "committed data only",
    "gen_inputs_diff": "reads the committed gen_inputs.db + repo tree found by walk-up",
    "goods_hold_cap": "committed item_ids/hold_cap tables; its find_repo_root sentinel walks up "
                      "to the repo tree the tests job checks out. NOT a GENERATORS suite despite "
                      "its own 'deliberately AP-free' note: run as `python x.py` it dies on its "
                      "unconditional `from ..item_ids import`, and under pytest the package "
                      "__init__ chain pulls in BaseClasses -- so it needs the installed world",
    "gen_stamp": "freshness (test_D) recomputes over the bundle-materialised inputs",
    "grace_skip_oracle": "event/ decompiles + BonfireWarpParam.csv ship in the bundle; REPO is "
                         "resolved by find_repo_root walk-up since the #244 fix (its positional "
                         "REPO was what kept it dark). Woken 2026-08-04 with the #244 world-data "
                         "fix -- the 12 overworld 9005810 flags are now in gen's skip set and "
                         "76412 is withheld, so it runs GREEN, permanently, in CI.",
    "input_completeness": "reads the committed bundle manifest",
    "item_exists": "msg/ FMGs + vanilla_er params ship in the bundle (2026-07-27)",
    "location_desc": "committed data; FMG-dependent parts covered by the bundle",
    "location_regions_slotdata": "committed data only",
    "no_phantom_flags": "event flag corpus ships in the bundle",
    "noninteractive_guard": "committed data only",
    "progression_surface": "gen_data.py found by walk-up in every CI checkout",
    "wizard_yaml_generates": "runs the wizard's OWN buildYaml under node, then Generate.py "
                             "against the installed world -- so it needs BOTH the repo tree (for "
                             "wizard.html) and an AP checkout. The tests job has both. It exists "
                             "because every other wizard gate checks an INPUT; this is the only one "
                             "that reads what the wizard hands the player.",
    "region_census": "tools/build_region_census.py + build_surface_confidence.py, both found by "
                     "walk-up in the tests job's checkout. Its first three claims are AP-free "
                     "(blob sync, staleness, and the union pinned to build_surface_confidence's "
                     "default_hosting) -- but the fourth builds REAL worlds through WorldTestBase "
                     "to prove the census's check-count identity against seeds Archipelago "
                     "actually generates, so the whole file needs the installed world and belongs "
                     "here rather than in GENERATORS.",
    "progressive_flasks": "tools/upgrade_costs.py found by walk-up in every CI checkout",
    "region_correctness": "committed region_map.csv installed beside the world",
    "region_provenance_oracle": "bundle-covered where its sources ship; remainder is census-pinned",
    "scadu_supply": "client rung mirror reads the gitlink checkout the tests job now makes",
    "spare_goods_order": "committed data only",
    "surface_confidence": "committed surface_confidence.tsv",
    "academy_key_pocket": "committed gen_data.py/data.py read by walk-up; the fill-binding half "
                          "needs the installed world (module-level try-import, no skip)",
    "shopslot_ungated_merchant": "committed esd_gates.tsv + generated location_tags.py read by "
                                 "walk-up; same shape as spell_vendor_merchants below",
    "spell_vendor_merchants": "committed merchant_shops.tsv + generated shop_data/location_tags/"
                              "data.py, all read by walk-up; no AP import, but the tests job is "
                              "where the repo tree is guaranteed present",
    "isolated_merchant_region": "committed gen_data.py/data.py/location_tags.py read by walk-up; "
                                "the fill-binding half needs the installed world (tests job has it)",
    "unplaced_globals": "bundle-covered EMEVD corpus",
}

# Suites where EVERY test skips in CI. The reason must name the missing input honestly -- these are
# the dev box's share of the coverage, and the census pins their exact skip counts so they cannot
# quietly grow or wake.
DEV_BOX_ONLY = {
    "grace_region_correctness":
        "needs elden_ring_artifacts/grace_region_map_*.tsv + grace_flags.tsv -- Windows-side "
        "BonfireWarpParam dumps that are NOT in the gen_inputs bundle (the bundle carries only "
        "what gen_data.py reads). Runs in run_ci.ps1 against the full artifact dump.",
    "grace_skip_classes":
        "needs elden_ring_artifacts/grace_flags.tsv (same Windows dump family as above); its "
        "setUpClass gates all 12 tests on the full source set even though event/ + "
        "BonfireWarpParam.csv ARE bundled -- splitting the suite so the bundled half runs in CI "
        "is possible follow-up work, noted in the 2026-08-04 audit, not done silently here.",
    "region_artifact_oracle":
        "needs REGION_ID_MAP.md + the grace dump TSVs -- neither is in the bundle. Runs in "
        "run_ci.ps1.",
}


def _suite(fname):
    return fname[len("test_gf_"):-len(".py")]


def check():
    errors = []
    on_disk = {f for f in os.listdir(TESTS) if f.startswith("test_") and f.endswith(".py")}
    ledgered = {}
    for bucket_name, names in (("GENERATORS", GENERATORS), ("TESTS_JOB", TESTS_JOB),
                               ("DEV_BOX_ONLY", DEV_BOX_ONLY)):
        for n in names:
            fname = "test_gf_%s.py" % n
            if fname not in on_disk:
                errors.append("%s entry %r names no file on disk (stale ledger row?)"
                              % (bucket_name, n))
            if n in ledgered:
                errors.append("suite %r is in two buckets (%s and %s) -- pick one"
                              % (n, ledgered[n], bucket_name))
            ledgered[n] = bucket_name

    for fname in sorted(on_disk):
        if not fname.startswith("test_gf_"):
            continue
        text = open(os.path.join(TESTS, fname), encoding="utf-8").read()
        if not SENTINELS.search(text):
            continue
        n = _suite(fname)
        if n not in ledgered:
            errors.append(
                "%s carries a repo-only sentinel (%s) but is in NO ledger bucket -- it would run "
                "only on the dev box, invisibly. Add it to GENERATORS / TESTS_JOB / DEV_BOX_ONLY "
                "in tools/gf_suite_ledger.py, with the honest reason."
                % (fname, ", ".join(sorted(set(SENTINELS.findall(text))))))

    # generators entries are run as scripts -- a loop entry without a __main__ block would
    # "pass" by doing nothing, which is this defect class wearing a different hat.
    for n in GENERATORS:
        fp = os.path.join(TESTS, "test_gf_%s.py" % n)
        if os.path.isfile(fp) and "__main__" not in open(fp, encoding="utf-8").read():
            errors.append("GENERATORS entry %r has no __main__ entry point -- the workflow would "
                          "run it as a script and it would exit 0 having tested nothing" % n)

    if errors:
        print("gf_suite_ledger: %d error(s):" % len(errors))
        for e in errors:
            print("  * " + e)
        return 1
    print("gf_suite_ledger: OK -- %d generator suites, %d tests-job suites, %d dev-box-only"
          % (len(GENERATORS), len(TESTS_JOB), len(DEV_BOX_ONLY)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="verify every repo-only suite is ledgered")
    g.add_argument("--generators-list", action="store_true",
                   help="emit the suite names the generators job loop runs (one per line)")
    args = ap.parse_args()
    if args.generators_list:
        print("\n".join(GENERATORS))
        return 0
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
