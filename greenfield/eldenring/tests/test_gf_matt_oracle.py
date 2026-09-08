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
  F. MISSABLE JOIN -- the report-only survey of our MISSABLE_LOCATIONS flags against his slots
     tagged `missable`: the joinable set, agreement, and both one-sided sets, on a second synthetic
     fixture. `missable` is filter vocabulary here exactly as EXCLUDED_TAGS is; no row of his is
     stored.
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
        # Class A no longer HAS a bulk set. `_A_OPEN_DLC_MATERIAL`'s 99 DLC upgrade-material flags
        # were region_map.csv's stale `item_name` capture, closed by gen_data's lot-reconcile pass,
        # and the set was DELETED rather than shrunk -- so nothing here may assert its existence.
        # Class A's own invariants are covered by the reason-vocabulary test above, which walks
        # ITEM_IDENTITY_KNOWN itself and so would also cover any future bulk set merged into it.
        self.assertGreater(len(self.M.ITEM_IDENTITY_KNOWN), 0)
        self.assertGreater(len(self.M._B_SCOPE_MAP_FRAGMENT), 10)
        self.assertGreater(len(self.M._B_OPEN), 10)
        self.assertFalse(self.M._B_SCOPE_MAP_FRAGMENT & self.M._B_OPEN)
        for f in self.M._B_SCOPE_MAP_FRAGMENT | self.M._B_OPEN:
            self.assertIn(f, self.M.MISSING_SLOT_KNOWN)

    def test_E_excluded_tag_vocabulary_is_lowercase_words(self):
        for t in self.M.EXCLUDED_TAGS:
            self.assertRegex(t, r"^[a-z+]+$")
        self.assertTrue(self.M._excluded_by_tags(frozenset({"norandom"})))
        self.assertTrue(self.M._excluded_by_tags(frozenset({"enemygem"})))
        self.assertFalse(self.M._excluded_by_tags(frozenset({"missable", "chest"})))


# A SECOND synthetic fixture, for the report-only missable join. Flags 90021-90025 and shop id 90102
# are invented numbers in a range the game does not use; every DebugText line was written for this
# test. PROVENANCE-OK, same declaration as the fixture above: grammar only, no foreign data.
FIXTURE_MISSABLE = """# Synthetic fixture written for test_gf_matt_oracle. Not derived from any third-party table.
Slots:
- Key: '200000,0:0000090021::'
  DebugText:
  - Rune Arc - lot 90000021[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: missable npc
- Key: '200001,0:0000090022::'
  DebugText:
  - Rune Arc - lot 90000022[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: missable
- Key: '200002,0:0000090023::'
  DebugText:
  - Rune Arc - lot 90000023[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: missable
- Key: '200003,0:0000090024::'
  DebugText:
  - Rune Arc - lot 90000024[treasure in m99_00_00_00] Rune Arc, 1x
  Tags: chest
- Key: '200004,3:0000000000:90102:'
  DebugText:
  - Rune Arc - shop 90102[merchant] 1x for 100 runes - flag 90201
  Tags: missable shop
"""

# Our side. 90021/90022/90024 have rows; 90023 does NOT (so his missable tag is not joinable).
MISS_BY_FLAG = {
    90021: [("Limgrave", "Limgrave :: Agreed missable [f90021]", 7770021)],
    90022: [("Limgrave", "Limgrave :: His only [f90022]", 7770022)],
    90024: [("Limgrave", "Limgrave :: Ours only [f90024]", 7770024)],
}
MISS_OURS = {90021, 90024}          # what MISSABLE_LOCATIONS would resolve to, flag-side


@unittest.skipUnless(RUNNING_FROM_REPO, REPO_ONLY_REASON)
@unittest.skipUnless(HAVE_YAML, "matt_oracle's parser needs PyYAML")
class MattOracleMissableJoin(unittest.TestCase):
    """F. The report-only missable survey.

    It is REPORT-ONLY on purpose and this suite must not grow an expectation about the real counts:
    he tags a SLOT ("do not randomize this into oblivion") and we tag a CHECK ("must not host
    REQUIRED progression"), so the two sides answer different questions and a one-sided flag is a
    worklist entry rather than a defect. What is testable is the JOIN's arithmetic, below.
    """

    @classmethod
    def setUpClass(cls):
        cls.M = _load_tool()
        cls.dir = tempfile.TemporaryDirectory()
        base = os.path.join(cls.dir.name, "diste", "Base")
        os.makedirs(base)
        path = os.path.join(base, "itemslots.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(FIXTURE_MISSABLE)
        cls.rows = cls.M.parse_itemslots(path)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def test_F_join_splits_agree_and_both_one_sided_sets(self):
        joinable, agree, his_only, ours_only = self.M.check_missable(
            self.rows, MISS_BY_FLAG, MISS_OURS)
        # 90023 carries his tag but we have no row for it, so it is NOT joinable -- counting it
        # would inflate "his-only" with slots the join cannot speak about at all.
        self.assertEqual(joinable, [90021, 90022])
        self.assertEqual(agree, [90021])
        self.assertEqual(his_only, [90022])
        self.assertEqual(ours_only, [90024])
        # The arithmetic the report prints must close over the joinable set.
        self.assertEqual(len(joinable), len(agree) + len(his_only))

    def test_F_shop_only_slot_is_never_joined(self):
        """ER's LocationScope zeroes the id on a shop-only slot. A missable tag on one must not
        join onto flag 0, which is not a flag."""
        by_flag = dict(MISS_BY_FLAG)
        by_flag[0] = [("Nowhere", "flag zero is not a flag", 7770000)]
        joinable, _agree, _his, _ours = self.M.check_missable(self.rows, by_flag, MISS_OURS)
        self.assertNotIn(0, joinable)

    def test_F_missable_tag_is_the_only_filter(self):
        """An untagged slot we DO carry (90024) is never in his set, whatever else it is tagged."""
        _joinable, _agree, his_only, ours_only = self.M.check_missable(
            self.rows, MISS_BY_FLAG, MISS_OURS)
        self.assertNotIn(90024, his_only)
        self.assertIn(90024, ours_only)

    def test_F_our_missable_flags_resolve_through_data_locations(self):
        """load_missable_flags maps ap_ids back to flags; every flag it returns must be a real
        LOCATIONS flag, and the row count must be the table's own length (nothing dropped silently
        beyond ap_ids LOCATIONS has no row for -- there should be none)."""
        flags, n_rows = self.M.load_missable_flags(REPO)
        miss = self.M._load_table(REPO, "missable_locations").MISSABLE_LOCATIONS
        data = self.M._load_table(REPO, "data")
        all_flags = {f for entries in data.LOCATIONS.values() for (_n, _a, f) in entries}
        self.assertEqual(n_rows, len(miss))
        self.assertTrue(flags, "no missable flag resolved -- the ap_id -> flag join is broken")
        self.assertTrue(flags <= all_flags)

    def test_F_section_letter_is_registered_in_the_tool(self):
        """The section header the report prints, asserted against the tool's SOURCE rather than by
        running it end-to-end. An end-to-end --report over a synthetic fixture cannot be used here:
        section D (boss taxonomy) raises TypeError when a class count is None, which it always is
        for an invented fixture -- a pre-existing edge in THAT section, untouched by this one."""
        src = open(TOOL, encoding="utf-8").read()
        self.assertIn('"== F. MISSABLE (report-only, no gate) =="', src)
        self.assertIn("check_missable(rows, by_flag, ours_flags)", src)
        # Report-only: nothing the survey computes may reach main()'s return value.
        tail = src[src.index("stale = stale_entries"):]
        self.assertNotIn("his_only", tail,
                         "the missable survey leaked into the gated tail of main()")

if __name__ == "__main__":
    unittest.main()
