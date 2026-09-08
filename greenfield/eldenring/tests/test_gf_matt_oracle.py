"""matt-oracle gate (tools/matt_oracle.py) -- parser and both checks, on a SYNTHETIC fixture.

The oracle cross-checks our generated tables against a LOCAL thefifthmatt/SoulsRandomizers
checkout. That checkout is not here, is not in CI's normal path, and must never be vendored (see
the licence boundary in the tool's docstring), so this suite proves the tool's LOGIC instead of its
verdict:

  A. PARSER -- a hand-written itemslots document, invented for this test, round-trips into the
     fields the checks consume: scope type, event flag, shop ids, tags, vanilla item names lifted
     from DebugText. Includes the shop-only case (LocationScope zeroes the id in ER, so the slot
     carries no flag and must not be joined on one) and a multi-item lot.
  B. ITEM IDENTITY -- agreement, disagreement, and the "not comparable" paths.
  C. MISSING SLOTS -- the tag-exclusion vocabulary, the allowlist, and the rule that an allowlisted
     flag stays visible even when a tag would also have hidden it.
  D. SKIP -- a missing or empty checkout exits 0 and says SKIP. This is load-bearing: the tool is
     opt-in and a missing checkout must never read as a failure.
  E. ALLOWLIST HYGIENE -- both allowlists are bare ints with non-empty reasons in the documented
     vocabulary, and disjointness of the class sets. This is the licence guard in test form: if a
     future edit ever put one of his strings in there, "bare int keys" fails.

🛑 THE FIXTURE IS OURS. Every slot below is made up -- invented flags, invented placements, item
names from the base game's own name table. Not one row, description or area name comes from his
repo. Do not "improve" this fixture by pasting real rows into it.

PROVENANCE-OK: this file writes the `<sortPrefix>,<Type>:<flag>::` key GRAMMAR, because a parser
test that does not exercise the real key shape tests nothing. The nine keys below are SYNTHETIC --
flags 90001-90013 and shop ids 90100/90101 are invented numbers in a range the game does not use,
and every DebugText line was written for this test. Grammar only, no foreign data. (The marker is
what tools/check_integrity.py's foreign-location-list guard reads; declaring it in-file puts the
claim in the diff, where a reviewer can check it, instead of in a filename allowlist.)

Run:  python -m pytest greenfield/eldenring/tests/test_gf_matt_oracle.py
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

try:                       # package-relative under pytest; plain path when run directly
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

HERE = os.path.dirname(os.path.abspath(__file__))
_FOUND = find_repo_root(HERE)
RUNNING_FROM_REPO = _FOUND is not None
REPO = _FOUND or os.path.dirname(os.path.dirname(HERE))
TOOL = os.path.join(REPO, "tools", "matt_oracle.py")

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


# A SYNTHETIC itemslots document. Same YAML-in-a-.txt shape the real one uses -- a `Slots:` list of
# mappings whose `Key` is '<sortPrefix>,<Type>:<UniqueID 10-digit>:<ShopIDs csv>:<ModelLots csv>'.
FIXTURE = """\
# Synthetic fixture written for test_gf_matt_oracle. Not derived from any third-party table.
Slots:
- Key: '100000,0:0000090001::'
  DebugText:
  - Smithing Stone [1] - lot 90000001[treasure in m99_00_00_00] Smithing Stone [1], 1x
  Tags: chest
- Key: '100001,0:0000090002::'
  DebugText:
  - Smithing Stone [8] - lot 90000002[treasure in m99_00_00_00] Smithing Stone [8], 1x
  Tags: chest
- Key: '100002,0:0000090003::'
  DebugText:
  - Golden Seed - lot 90000003[treasure in m99_00_00_00] Golden Seed, 1x
  - Sacred Tear - lot 90000003[treasure in m99_00_00_00] Sacred Tear, 1x
  Tags: outoftheway
- Key: '100003,0:0000090004::'
  Tags: boss
- Key: '100004,0:0000090010::'
  DebugText:
  - Rune Arc - lot 90000010[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: norandom
- Key: '100005,0:0000090011::'
  DebugText:
  - Rune Arc - lot 90000011[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: enemyweapon boss
- Key: '100006,0:0000090012::'
  DebugText:
  - Rune Arc - lot 90000012[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: missable
- Key: '100007,0:0000090013::'
  DebugText:
  - Rune Arc - lot 90000013[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: norandom
- Key: '100008,3:0000000000:90100,90101:'
  DebugText:
  - Rune Arc - shop 90100[merchant] 1x for 100 runes - flag 90200
  Tags: shop
"""

# Our side, standing in for data.LOCATIONS / item_ids.LOCATION_ITEM.
OUR_BY_FLAG = {
    90001: [("Limgrave", "Limgrave :: Smithing Stone [1] [f90001]", 7770001)],
    90002: [("Limgrave", "Limgrave :: Smithing Stone [4] [f90002]", 7770002)],
    90003: [("Limgrave", "Limgrave :: Golden Seed [f90003]", 7770003)],
    90004: [("Limgrave", "Limgrave :: Something [f90004]", 7770004)],
    90005: [("Limgrave", "Limgrave :: Ours only [f90005]", 7770005)],
}
OUR_ITEM = {
    7770001: "Smithing Stone [1]",     # agrees
    7770002: "Smithing Stone [4]",     # disagrees (he says [8])
    7770003: "Golden Seed",            # agrees -- one member of his multi-item lot
    # 7770004 absent -> not comparable (he has no DebugText for 90004 either)
    7770005: "Whatever",               # flag he does not carry at all -- never compared
}


def _load_tool():
    spec = importlib.util.spec_from_file_location("_matt_oracle_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
@unittest.skipUnless(HAVE_YAML, "matt_oracle's parser needs PyYAML")
class MattOracleLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.M = _load_tool()
        cls.dir = tempfile.TemporaryDirectory()
        base = os.path.join(cls.dir.name, "diste", "Base")
        os.makedirs(base)
        cls.slots_path = os.path.join(base, "itemslots.txt")
        with open(cls.slots_path, "w", encoding="utf-8") as fh:
            fh.write(FIXTURE)
        cls.rows = cls.M.parse_itemslots(cls.slots_path)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    # --- A. parser -------------------------------------------------------
    def test_A_parses_every_slot(self):
        self.assertEqual(len(self.rows), 9)

    def test_A_key_is_split_into_scope_flag_and_shops(self):
        by = {r["flag"]: r for r in self.rows if r["flag"]}
        self.assertEqual(sorted(by), [90001, 90002, 90003, 90004, 90010, 90011, 90012, 90013])
        self.assertTrue(all(r["stype"] == self.M.SCOPE_EVENT for r in by.values()))
        # The shop-only slot: ER zeroes the id, so it has NO flag and must be recognisable by its
        # scope type and shop ids instead. Joining it on flag 0 would be a silent mis-join.
        shop = [r for r in self.rows if r["stype"] == self.M.SCOPE_SHOP_INFINITE]
        self.assertEqual(len(shop), 1)
        self.assertEqual(shop[0]["flag"], 0)
        self.assertEqual(shop[0]["shop_ids"], [90100, 90101])

    def test_A_tags_and_item_names(self):
        by = {r["flag"]: r for r in self.rows if r["flag"]}
        self.assertEqual(by[90001]["tags"], frozenset({"chest"}))
        self.assertEqual(by[90001]["item_names"], ["Smithing Stone [1]"])
        # A multi-item lot yields one name per DebugText line, in order.
        self.assertEqual(by[90003]["item_names"], ["Golden Seed", "Sacred Tear"])
        # A slot with no DebugText yields no names -- the "not comparable" path. Asserted as a
        # COUNT MAP over every parsed slot rather than as `== []` on the one slot: an empty-list
        # assertion passes just as happily when the parser stopped early and saw nothing, whereas
        # this shape names how many item names each flag produced and so cannot be satisfied by a
        # dead parser.
        self.assertEqual(
            {f: len(r["item_names"]) for f, r in by.items()},
            {90001: 1, 90002: 1, 90003: 2, 90004: 0,
             90010: 1, 90011: 1, 90012: 1, 90013: 1},
        )
        self.assertEqual(by[90004]["tags"], frozenset({"boss"}))

    # --- B. item identity ------------------------------------------------
    def test_B_item_identity_agree_disagree_and_not_comparable(self):
        dis, agree, nocmp = self.M.check_item_identity(self.rows, OUR_BY_FLAG, OUR_ITEM)
        self.assertEqual(agree, 2)                      # 90001 exact, 90003 via the lot's members
        self.assertEqual([d["flag"] for d in dis], [90002])
        self.assertEqual(dis[0]["ours"], "Smithing Stone [4]")
        self.assertEqual(dis[0]["theirs"], ["Smithing Stone [8]"])
        self.assertIsNone(dis[0]["known"])              # not in the shipped allowlist
        self.assertEqual(nocmp, 1)                      # 90004: he names nothing
        # 90005 is ours-only: absent from his table entirely, so it is not counted anywhere here.
        # That asymmetry is report-only by design (it is dominated by gestures he does not model).

    def test_B_allowlist_is_consulted(self):
        self.M.ITEM_IDENTITY_KNOWN[90002] = "TEST: injected"
        try:
            dis, _, _ = self.M.check_item_identity(self.rows, OUR_BY_FLAG, OUR_ITEM)
            self.assertEqual(dis[0]["known"], "TEST: injected")
        finally:
            del self.M.ITEM_IDENTITY_KNOWN[90002]

    # --- C. missing slots ------------------------------------------------
    def test_C_missing_slots_excludes_by_tag(self):
        missing, excluded = self.M.check_missing_slots(self.rows, OUR_BY_FLAG)
        # 90010 norandom, 90011 enemyweapon (prefix rule), 90013 norandom -> excluded.
        # 90012 missable -> a genuine missing slot. 90001-90004 we carry. The shop slot has no flag.
        self.assertEqual(excluded, 3)
        self.assertEqual([m["flag"] for m in missing], [90012])
        self.assertEqual(missing[0]["tags"], ["missable"])
        self.assertIsNone(missing[0]["known"])

    def test_C_allowlist_beats_tag_exclusion(self):
        # An explained flag stays VISIBLE even when a tag would also have hidden it, so it is never
        # silently double-excused and its staleness stays checkable.
        self.M.MISSING_SLOT_KNOWN[90010] = "TEST: injected"
        try:
            missing, excluded = self.M.check_missing_slots(self.rows, OUR_BY_FLAG)
            self.assertEqual(excluded, 2)
            self.assertEqual([m["flag"] for m in missing], [90010, 90012])
            self.assertEqual(missing[0]["known"], "TEST: injected")
        finally:
            del self.M.MISSING_SLOT_KNOWN[90010]

    def test_C_stale_entry_is_reported_when_the_gap_closes(self):
        self.M.MISSING_SLOT_KNOWN[90001] = "TEST: injected"     # 90001 IS in OUR_BY_FLAG
        try:
            stale = self.M.stale_entries(set(), OUR_BY_FLAG)
            self.assertIn(("MISSING_SLOT_KNOWN", 90001, "TEST: injected"), stale)
        finally:
            del self.M.MISSING_SLOT_KNOWN[90001]

    # --- C2. region queue ------------------------------------------------
    # The queue exists so two humans can work the ~218 rows a second source's own partition
    # disagrees with. Its licence boundary is IN THE ALGORITHM: his area label is an equivalence
    # key, the mapping it produces is built from OUR regions, and the label is discarded before
    # anything is written. These tests assert that, not just the arithmetic.
    def test_C2_area_maps_to_our_region_by_strict_plurality(self):
        rows = [
            {"stype": 0, "flag": 1, "area": "alpha"},
            {"stype": 0, "flag": 2, "area": "alpha"},
            {"stype": 0, "flag": 3, "area": "alpha"},
            {"stype": 0, "flag": 4, "area": "split"},
            {"stype": 0, "flag": 5, "area": "split"},
            {"stype": 3, "flag": 0, "area": "shoponly"},       # no flag: contributes nothing
        ]
        by_flag = {
            1: [("Limgrave", "n", 11)], 2: [("Limgrave", "n", 12)], 3: [("Caelid", "n", 13)],
            4: [("Limgrave", "n", 14)], 5: [("Caelid", "n", 15)],
        }
        mapped, areas = self.M.region_area_map(rows, by_flag)
        self.assertEqual(areas, 2)                     # 'shoponly' never became a cluster
        self.assertEqual(mapped, {"alpha": "Limgrave"})
        # A cluster split evenly says nothing about any row in it, so it maps to NOTHING rather
        # than to whichever region sorted first. Silence, not a coin flip.
        self.assertNotIn("split", mapped)

    def test_C2_queue_is_the_rows_outside_their_own_cluster(self):
        rows = [{"stype": 0, "flag": f, "area": "alpha"} for f in (1, 2, 3)]
        rows.append({"stype": 0, "flag": 4, "area": "split"})
        rows.append({"stype": 0, "flag": 5, "area": "split"})
        by_flag = {
            1: [("Limgrave", "n", 11)], 2: [("Limgrave", "n", 12)], 3: [("Caelid", "n", 13)],
            4: [("Limgrave", "n", 14)], 5: [("Caelid", "n", 15)],
        }
        queue, joined, areas, mapped = self.M.check_region_queue(rows, by_flag)
        self.assertEqual((joined, areas, mapped), (3, 2, 1))   # only 'alpha' contributes rows
        self.assertEqual([(q["flag"], q["ap_id"], q["our_region"]) for q in queue],
                         [(3, 13, "Caelid")])
        self.assertEqual(queue[0]["basis"], self.M.BASIS_REGION)
        # 🛑 THE LICENCE GUARD. Nothing of his may leave this function: no area label, no field
        # beyond the four we write. Asserted as an EXACT key set so a future edit that carries
        # "area" along for debugging fails here rather than shipping it into the committed tsv.
        self.assertEqual(set(queue[0]), {"flag", "ap_id", "our_region", "basis"})
        for value in queue[0].values():
            self.assertNotIn("alpha", str(value))

    def test_C2_dlc_membership_rows_are_queued_unconditionally(self):
        # 520800 / 530950 are the two base-vs-DLC membership rows from the roadmap. They are queued
        # even when the partition happens to AGREE, which is the point: a model difference that
        # cancels out is not evidence that the row is right.
        flags = sorted(self.M.DLC_MEMBERSHIP_FLAGS)
        rows = [{"stype": 0, "flag": f, "area": "alpha"} for f in flags]
        by_flag = {f: [("Roundtable Hold", "n", 900 + i)] for i, f in enumerate(flags)}
        queue, _, _, _ = self.M.check_region_queue(rows, by_flag)
        self.assertEqual([q["flag"] for q in queue], flags)
        self.assertTrue(all(q["basis"] == self.M.BASIS_DLC for q in queue))

    def test_C2_refresh_preserves_verdicts_and_drops_resolved_rows(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "queue.tsv")
            first = [{"flag": 1, "ap_id": 11, "our_region": "Limgrave",
                      "basis": self.M.BASIS_REGION},
                     {"flag": 2, "ap_id": 12, "our_region": "Caelid",
                      "basis": self.M.BASIS_REGION}]
            self.M.write_region_queue(path, first, {})
            back = self.M.read_region_queue(path)
            self.assertEqual(sorted(back), [(1, 11), (2, 12)])
            self.assertEqual(back[(1, 11)]["status"], "open")

            back[(1, 11)].update(status="confirmed-ours", reviewer="alaric", note="ours is right")
            # flag 2 stopped disagreeing; flag 3 is new.
            second = [first[0], {"flag": 3, "ap_id": 13, "our_region": "Altus",
                                 "basis": self.M.BASIS_DLC}]
            kept, added, dropped = self.M.write_region_queue(path, second, back)
            self.assertEqual((kept, added, dropped), (1, 1, [(2, 12)]))
            final = self.M.read_region_queue(path)
            self.assertEqual(final[(1, 11)]["status"], "confirmed-ours")
            self.assertEqual(final[(1, 11)]["reviewer"], "alaric")
            self.assertEqual(final[(1, 11)]["note"], "ours is right")
            self.assertEqual(final[(3, 13)]["status"], "open")
            self.assertNotIn((2, 12), final)
            # newline='\n' on both platforms -- the committed file is diff-gated in CI.
            with open(path, "rb") as fh:
                self.assertNotIn(b"\r\n", fh.read())

    def test_C2_committed_queue_carries_nothing_but_our_own_columns(self):
        # The shipped file is the licence surface. Every cell must be an int of ours, one of OUR
        # region names, one of two basis tokens, a status from the documented vocabulary, or free
        # text a reviewer wrote. A stray column is how a foreign area name would arrive.
        path = os.path.join(REPO, "greenfield", "evidence", "oracle-region-queue.tsv")
        rows = self.M.read_region_queue(path)
        self.assertGreater(len(rows), 100)
        by_flag, _ = self.M.load_ours(REPO)
        regions = {r for entries in by_flag.values() for r, _n, _a in entries}
        for (flag, ap_id), row in rows.items():
            self.assertEqual(sorted(row), sorted(self.M.QUEUE_COLUMNS))
            self.assertIn(row["basis"], (self.M.BASIS_REGION, self.M.BASIS_DLC))
            self.assertIn(row["status"], self.M.QUEUE_STATUSES)
            self.assertIn(row["our_region"], regions)
            # the (flag, ap_id) pair must be a REAL row of ours, not just two plausible integers
            self.assertIn(ap_id, {a for _r, _n, a in by_flag.get(flag, ())})
        for flag in self.M.DLC_MEMBERSHIP_FLAGS:
            self.assertTrue(any(f == flag for f, _ in rows), "flag %d left the queue" % flag)

    # --- D. skip ---------------------------------------------------------
    def test_D_missing_checkout_skips_with_exit_zero(self):
        for arg in (os.path.join(self.dir.name, "nope"), self.dir.name + "-absent"):
            out = subprocess.run([sys.executable, TOOL, "--souls-rando-dir", arg],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn("SKIP:", out.stdout)

    def test_D_directory_without_itemslots_skips(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "diste", "Base"))       # present but empty
            out = subprocess.run([sys.executable, TOOL, "--souls-rando-dir", d],
                                 capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
            self.assertIn("SKIP:", out.stdout)

    def test_D_no_argument_and_no_env_skips(self):
        env = dict(os.environ)
        env.pop("SOULS_RANDO_DIR", None)
        out = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, env=env)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)
        self.assertIn("SKIP:", out.stdout)

    # --- E. allowlist hygiene (the licence guard) ------------------------
    def test_E_allowlists_are_bare_ints_with_classified_reasons(self):
        vocab = ("BUNDLE", "KEYING", "SCOPE", "OPEN")
        for name in ("ITEM_IDENTITY_KNOWN", "MISSING_SLOT_KNOWN"):
            table = getattr(self.M, name)
            self.assertTrue(table, name + " is empty")
            for flag, reason in table.items():
                self.assertIsInstance(flag, int, "%s key %r is not a bare event flag" % (name, flag))
                self.assertGreater(flag, 0, "%s[%r] is not a real flag" % (name, flag))
                self.assertIsInstance(reason, str)
                self.assertTrue(reason.startswith(vocab),
                                "%s[%d] reason %r is outside the documented vocabulary %s"
                                % (name, flag, reason, vocab))

    def test_E_class_sets_are_disjoint_and_land_in_their_table(self):
        # WITNESS FIRST: "these two sets do not overlap" is trivially true of two empty sets, so
        # assert they are populated before asserting they are disjoint.
        self.assertGreater(len(self.M._A_OPEN_DLC_MATERIAL), 50)
        self.assertGreater(len(self.M._B_SCOPE_MAP_FRAGMENT), 10)
        self.assertGreater(len(self.M._B_OPEN), 10)
        self.assertFalse(self.M._B_SCOPE_MAP_FRAGMENT & self.M._B_OPEN)
        for f in self.M._A_OPEN_DLC_MATERIAL:
            self.assertIn(f, self.M.ITEM_IDENTITY_KNOWN)
        for f in self.M._B_SCOPE_MAP_FRAGMENT | self.M._B_OPEN:
            self.assertIn(f, self.M.MISSING_SLOT_KNOWN)

    def test_E_excluded_tag_vocabulary_is_lowercase_words(self):
        for t in self.M.EXCLUDED_TAGS:
            self.assertRegex(t, r"^[a-z+]+$")
        self.assertTrue(self.M._excluded_by_tags(frozenset({"norandom"})))
        self.assertTrue(self.M._excluded_by_tags(frozenset({"enemygem"})))
        self.assertFalse(self.M._excluded_by_tags(frozenset({"missable", "chest"})))


if __name__ == "__main__":
    unittest.main()
