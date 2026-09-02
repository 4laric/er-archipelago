"""Spawn traps -- the resolved catalogue, the id block, and the cross-repo NAME contract.

A spawn trap drops a real enemy on top of the player. That needs THREE game ids, not one -- chr
model, `NpcParam` body, `NpcThinkParam` brain -- so a yaml naming `c4150` has to be RESOLVED, and
this world resolves it at generation time and posts the answer in the item NAME.

🛑 THE FAILURE THIS FILE EXISTS FOR is the same one `test_gf_traps.py` guards, one level meaner.
`er_logic::traps::SpawnSpec::from_item_name` parses `Trap: <label> (<chr>/<npc>/<think> x<count>)`
and REFUSES anything else. Change the format here and nothing breaks: the item still generates, is
still filler, still arrives -- and the client silently refuses it forever. There is no gate across
the repo boundary, so both sides pin the literal and these cases are our half.

The second failure guarded here is quieter still: an AP id that MOVES. Ids are handed out by
`core._SPAWN_TRAP_BASE + chr_id`, deliberately outside `registry.allocate_item_ids`, so that
blessing a new enemy renumbers nothing. If someone "tidies" that into an `enumerate`, every seed
already in flight starts resolving its trap items to the wrong enemy, and every test here still
passes unless one of them is watching the arithmetic itself.
"""
import unittest

# 🛑 NO `find_repo_root` / REPO_ONLY_REASON SENTINEL HERE, deliberately, and it was removed rather
# than never written: the first draft copied one from `test_gf_traps.py` and gated `TheIdBlock` on
# it. That gate is a LIE -- nothing in this file reads the repo tree; every case imports
# `worlds.eldenring.*`, which is the INSTALLED world. Had `find_repo_root` ever missed, the four
# renumbering guards below would have skipped citing a missing input that is not one of theirs, and
# a dark id gate is precisely the failure they exist to catch. The suite is ledgered in
# `tools/gf_suite_ledger.py` under TESTS_JOB so its home is on the record either way.

#: Written out literally rather than imported. Importing would make this test agree with any
#: reformat by construction, which is the one thing it must not do. This is the exact string the
#: client's parser is pinned against on the other side.
BASILISK_NAME = "Trap: Basilisk x3 (4150/41500060)"
AGING_UNTOUCHABLE_NAME = "Trap: Aging Untouchable x1 (5280/52800086)"
MALENIA_NAME = "Trap: Malenia (Phase 1) x1 (2120/21200000)"

#: `er_logic::traps::LABEL_CAP`. The client retains a spawn label inline so its `SpawnSpec` stays
#: `Copy`, and REFUSES a longer one rather than truncating.
LABEL_CAP = 24

#: `er_logic::traps::MAX_SPAWN_COUNT`. A horde big enough to hang the game is a save-ruining bug.
MAX_SPAWN_COUNT = 8


def _mod():
    from worlds.eldenring.features import traps
    return traps


def _data():
    from worlds.eldenring import spawn_trap_data
    return spawn_trap_data


class SpawnCatalogue(unittest.TestCase):
    """Pure table checks -- no world, no fill."""

    def test_the_table_is_not_empty(self):
        """WITNESS for every loop below. An empty catalogue would make this whole file vacuously
        green while minting no items at all -- exactly the shape test_gf_vacuous_pass exists for."""
        self.assertGreater(len(_data().SPAWN_TRAPS), 300)

    def test_every_row_names_rows_from_its_own_model_family(self):
        """A body running another creature's brain. The ids are unvalidated integers by the time
        they reach `spawn_debug_character`, so a mismatched family spawns something nobody chose --
        and it would surface in a live session, not as a build error. The client makes the same
        check on its side of the name."""
        rows = _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id, (label, npc, think, count) in rows.items():
            prefix = str(chr_id)
            self.assertTrue(str(npc).startswith(prefix),
                            f"NpcParam {npc} is not in the c{chr_id} family")
            self.assertTrue(str(think).startswith(prefix),
                            f"NpcThinkParam {think} is not in the c{chr_id} family")

    def test_every_label_is_one_the_client_will_accept(self):
        """🛑 CROSS-REPO CEILING. The client REFUSES a label over LABEL_CAP bytes rather than
        truncating it, so an over-long label here is not a cosmetic problem -- it is a trap that
        arrives and never fires. Non-ASCII is the same story for a different reason: the in-game
        font draws `?` for anything else."""
        rows = _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id, (label, _npc, _think, _count) in rows.items():
            self.assertTrue(label, f"c{chr_id} has an empty label")
            self.assertTrue(label.isascii(), f"c{chr_id} label {label!r} is not ASCII")
            self.assertLessEqual(len(label.encode("utf-8")), LABEL_CAP,
                                 f"c{chr_id} label {label!r} exceeds LABEL_CAP={LABEL_CAP}")

    def test_every_count_is_one_the_client_will_accept(self):
        """Same shape, the other cross-repo constant. A count of 0 mints a trap that spawns nothing;
        a count over the cap is refused outright."""
        rows = _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id, (_label, _npc, _think, count) in rows.items():
            self.assertGreaterEqual(count, 1, f"c{chr_id} spawns nothing")
            self.assertLessEqual(count, MAX_SPAWN_COUNT, f"c{chr_id} exceeds MAX_SPAWN_COUNT")

    def test_the_derivation_reproduces_the_hand_derived_runebear(self):
        """🛑 THE CONTROL FOR THE WHOLE TABLE, and the only row with an independent answer.

        The Runebear's three ids were derived BY HAND in client PR #114, by a person reading
        `NpcName.fmg.xml` and the param families. The rule that built this table -- lowest POSITIVE
        `getSoul`, ties by id -- picks `46300010` out of that family's 21 rows without being told.
        A rule that disagreed with the only known-good answer on record would be the wrong rule, and
        every other one of the 390 rows rests on it being right."""
        self.assertEqual(_data().SPAWN_TRAPS[4630][1:3], (46300010, 46300000))

    def test_the_basilisk_is_the_motivating_case(self):
        """Issue #114's spawn trap, and the reason the table exists. Three of them because one
        basilisk at zero range is trivially killable -- the threat is the Death Blight mist."""
        self.assertEqual(_data().SPAWN_TRAPS[4150], ("Basilisk", 41500060, 41500000, 3))
        self.assertEqual(_data().SPAWN_TRAP_KEYS["basilisk"], 4150)

    def test_the_aging_untouchable_is_a_curated_single_spawn(self):
        """Aging Untouchable is deliberately singular: it cannot be damaged until parried, so a
        horde would be substantially meaner than the option name suggests."""
        self.assertEqual(
            _data().SPAWN_TRAPS[5280],
            ("Aging Untouchable", 52800086, 52800000, 1),
        )
        self.assertEqual(_data().SPAWN_TRAP_KEYS["aging_untouchable"], 5280)

    def test_malenia_is_the_phase_one_template(self):
        """Malenia's later phase is entered by her arena event. A standalone c2120 debug spawn
        using the family template remains phase one, so pin all three ids rather than letting a
        future row-selection change silently alter the promised trap."""
        self.assertEqual(
            _data().SPAWN_TRAPS[2120],
            ("Malenia (Phase 1)", 21200000, 21200000, 1),
        )
        self.assertEqual(_data().SPAWN_TRAP_KEYS["malenia"], 2120)

    def test_props_and_brainless_models_are_excluded(self):
        """🛑 THE REFUSALS ARE THE POINT, so they get a test of their own rather than being a
        by-product of the derivation. Each of these would generate clean and mint an item that does
        nothing in-game forever: c5350 (Basilisk Eyes) and c4450 (Walking Mausoleum) have `hp 0` and
        are scenery; c2131 (dead Morgott) and c8101 (wheeled ballista) have no NpcThinkParam row at
        all, so nothing would come after you.

        ⚠️ Note c5350 specifically: it is NAMED 'Basilisk Eyes' and is NOT the basilisk. Spawning it
        instead of c4150 is the single most plausible wrong answer to 'what is a basilisk'."""
        rows = _data().SPAWN_TRAPS
        for excluded in (5350, 4450, 4492, 8120, 2131, 8101, 4751):
            self.assertNotIn(excluded, rows, f"c{excluded} is not spawnable and must not be offered")
        # WITNESS: the exclusions are selective, not a table that excluded everything.
        for included in (4150, 4630, 5990):
            self.assertIn(included, rows)

    def test_curated_keys_point_at_models_that_exist(self):
        """A yaml key resolving to a model the table dropped is an option a player can set that
        mints nothing."""
        data = _data()
        self.assertTrue(data.SPAWN_TRAP_KEYS)
        for key, chr_id in data.SPAWN_TRAP_KEYS.items():
            self.assertIn(chr_id, data.SPAWN_TRAPS, f"curated key {key!r} -> missing c{chr_id}")
            self.assertTrue(key.islower() and key.replace("_", "").isalnum(), key)


class TheNameContract(unittest.TestCase):
    """The exact string the other repository parses."""

    def test_the_basilisk_name_is_the_literal_the_client_parses(self):
        """🛑 If this fails, the client stops recognising the item and NOTHING else breaks. Compare
        against the written-out literal at the top of this file, never against a rebuild of the
        format from the same code under test."""
        self.assertEqual(_mod().spawn_item_name(4150), BASILISK_NAME)

    def test_the_aging_untouchable_name_is_the_literal_the_client_parses(self):
        self.assertEqual(_mod().spawn_item_name(5280), AGING_UNTOUCHABLE_NAME)

    def test_the_malenia_name_is_the_literal_the_client_parses(self):
        self.assertEqual(_mod().spawn_item_name(2120), MALENIA_NAME)

    def test_every_name_carries_the_prefix_the_client_dispatches_on(self):
        t = _mod()
        rows = _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id in rows:
            nm = t.spawn_item_name(chr_id)
            self.assertTrue(nm.startswith(t.TRAP_PREFIX), nm)
            self.assertTrue(nm.isascii(), nm)
            self.assertTrue(nm.endswith(")"), nm)

    def test_a_name_carries_the_two_ids_and_the_count_in_the_parsed_positions(self):
        """The whole reason the payload is in the NAME rather than in slot_data: the integers travel
        for free and no CONTRACT_HASH moves. Parsed exactly the way the client parses it -- last
        `" ("` for the payload, last `" x"` for the count -- so a label that happens to contain
        either is exercised here rather than discovered in a seed."""
        t, rows = _mod(), _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id, (label, npc, _think, count) in rows.items():
            nm = t.spawn_item_name(chr_id)
            readable, _, payload = nm[:-1].rpartition(" (")
            self.assertEqual(payload.split("/"), [str(chr_id), str(npc)], nm)
            lbl, _, cnt = readable.rpartition(" x")
            self.assertEqual(cnt, str(count), nm)
            self.assertEqual(lbl[len(t.TRAP_PREFIX):], label, nm)

    def test_the_think_row_is_the_family_template_for_every_row(self):
        """🛑 THE PREMISE THAT LICENSES DROPPING think FROM THE NAME. The client does not receive it;
        it computes `chr_id * 10000`. That is sound only because admission to this table REQUIRES an
        NpcThinkParam row at exactly `<chr>0000`, so the two can never disagree.

        If this ever fails, the name cannot express reality any more and the field has to come back
        -- which is a cross-repo format change, so it needs to fail HERE, loudly, and not as a
        creature that spawns with another creature's brain."""
        rows = _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id, (_label, _npc, think, _count) in rows.items():
            self.assertEqual(think, chr_id * 10000,
                             f"c{chr_id} think row {think} is not the family template")

    def test_the_npc_row_is_not_derivable_and_therefore_must_stay_in_the_name(self):
        """The other half of the same argument, and the reason only ONE id was dropped. If the npc
        row were also always the template, the name would need just the model -- so this measures
        that it is not, rather than leaving it as a claim in a comment."""
        rows = _data().SPAWN_TRAPS
        differ = [c for c, (_l, npc, _t, _n) in rows.items() if npc != c * 10000]
        self.assertGreater(len(differ), 100,
                           "if nearly every npc row were the template, the format is carrying a "
                           "field it could derive")

    def test_names_are_distinct(self):
        """Two models minting one name would make one of them unreachable and the other ambiguous."""
        t, rows = _mod(), _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        names = [t.spawn_item_name(c) for c in rows]
        self.assertEqual(len(set(names)), len(names))


class TheIdBlock(unittest.TestCase):
    """🛑 The renumbering guard. See this module's docstring."""

    def _core(self):
        from worlds.eldenring import core
        return core

    def test_every_spawn_id_is_arithmetic_in_the_model(self):
        """THE INVARIANT THAT MAKES ADDING AN ENEMY FREE. An id derived by `enumerate` moves every
        later id when one row is inserted; an id derived from the chr model never moves at all.
        That is also what makes issue #114 rule 4 ('removing a trap name is a compat break') cost
        nothing on this surface."""
        core, t, rows = self._core(), _mod(), _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id in rows:
            nm = t.spawn_item_name(chr_id)
            self.assertIn(nm, core.item_name_to_id, f"c{chr_id} minted no AP id")
            self.assertEqual(core.item_name_to_id[nm], core._SPAWN_TRAP_BASE + chr_id, nm)

    def test_the_spawn_block_does_not_overlap_any_other_id_block(self):
        """The three blocks are chosen constants with room between them, and the catalogue in the
        middle GROWS. Asserting disjointness beats a comment claiming it."""
        core = self._core()
        spawn = {core._SPAWN_TRAP_BASE + c for c in _data().SPAWN_TRAPS}
        others = {v for k, v in core.item_name_to_id.items()
                  if v not in spawn}
        self.assertTrue(spawn, "WITNESS: no spawn ids at all would make the intersection empty")
        self.assertTrue(others, "WITNESS: no other ids at all would do the same")
        self.assertEqual(spawn & others, set())

    def test_every_spawn_item_is_filler(self):
        """#114 rule 3: a trap is filler and no progression may ride one. A spawn trap classed
        progression would put a required item behind an enemy the fill never reasoned about."""
        from BaseClasses import ItemClassification
        core, t, rows = self._core(), _mod(), _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id in rows:
            self.assertEqual(core._item_class[t.spawn_item_name(chr_id)],
                             ItemClassification.filler)

    def test_no_spawn_item_claims_a_real_game_item(self):
        """A spawn trap is SYNTHETIC: it has no ITEM_GRANTS, so the game must never be asked to hand
        the player something for it. A stray `_AP_IDS_TO_ITEM_IDS` row would do exactly that."""
        core, t, rows = self._core(), _mod(), _data().SPAWN_TRAPS
        self.assertGreater(len(rows), 300)
        for chr_id in rows:
            aid = str(core.item_name_to_id[t.spawn_item_name(chr_id)])
            self.assertNotIn(aid, core._AP_IDS_TO_ITEM_IDS)


class TheYamlSurface(unittest.TestCase):
    """What a player can actually ask for."""

    class _Opt:
        def __init__(self, value):
            self.value = value

    class _World:
        def __init__(self, traps=(), spawn=(), count=0):
            class O:
                pass
            self.options = O()
            self.options.traps = TheYamlSurface._Opt(frozenset(traps))
            self.options.spawn_traps = TheYamlSurface._Opt(frozenset(spawn))
            self.options.trap_count = TheYamlSurface._Opt(count)

    def test_spawn_traps_is_off_by_default(self):
        """A default seed must be byte-identical to one built before this feature existed."""
        self.assertEqual(set(_mod().SpawnTraps.default), set())

    def test_an_unspawnable_id_is_not_a_valid_yaml_value(self):
        """🛑 `valid_keys` IS the validation. Without it `spawn_traps: [5350]` gens clean and mints
        an item that can never fire, which is the failure mode this whole design refuses."""
        t = _mod()
        self.assertIn("4150", t.SpawnTraps.valid_keys)
        for bad in ("5350", "9999", "0", "c4150"):
            self.assertNotIn(bad, t.SpawnTraps.valid_keys)

    def test_a_curated_key_is_a_valid_traps_value(self):
        """`traps: [basilisk]` must not be an unknown-key error -- the curated keys share the
        `traps` option with the fixed ones."""
        t = _mod()
        self.assertIn("basilisk", t.Traps.valid_keys)
        self.assertIn("aging_untouchable", t.Traps.valid_keys)
        self.assertIn("rune_thief", t.Traps.valid_keys)

    def test_naming_one_enemy_both_ways_mints_it_once(self):
        """🛑 A SILENT WEIGHTING BUG, not a visible one. `traps: [basilisk]` and
        `spawn_traps: ["4150"]` resolve to the same string; without the dedup the round-robin would
        deal basilisks twice as often as everything else and nothing would look wrong."""
        t = _mod()
        w = self._World(traps=["basilisk"], spawn=["4150"], count=4)
        self.assertEqual(t.enabled_trap_names(w), [BASILISK_NAME])
        self.assertEqual(t.trap_items(w), [BASILISK_NAME] * 4)

    def test_the_split_is_even_across_fixed_and_spawn_traps(self):
        """The two sources feed ONE round-robin. WITNESSED against a live single-source case so that
        an `enabled_trap_names` returning [] could not satisfy this for free."""
        t = _mod()
        self.assertTrue(t.trap_items(self._World(traps=["rune_thief"], count=2)))
        got = t.trap_items(self._World(traps=["rune_thief", "basilisk"], count=6))
        self.assertEqual(len(got), 6)
        self.assertEqual(got.count("Trap: Rune Thief"), 3)
        self.assertEqual(got.count(BASILISK_NAME), 3)

    def test_the_order_is_a_function_of_the_yaml_not_of_set_iteration(self):
        """An OptionSet is a frozenset and iterating one is not order-stable. A seed must be
        rebuildable from its yaml, so the same options must give the same list."""
        t = _mod()
        a = t.trap_items(self._World(traps=["rune_thief", "basilisk"], spawn=["4630", "5990"], count=9))
        b = t.trap_items(self._World(traps=["basilisk", "rune_thief"], spawn=["5990", "4630"], count=9))
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), 4)

    def test_spawn_traps_alone_is_enough(self):
        """The escape hatch must work with `traps` left empty -- otherwise a raw id is only usable
        by someone who also enabled a curated trap."""
        t = _mod()
        got = t.trap_items(self._World(spawn=["4630"], count=3))
        self.assertEqual(got, [t.spawn_item_name(4630)] * 3)

    def test_a_count_of_zero_mints_nothing_however_many_are_named(self):
        """Witnessed with the same set and a non-zero count, so the off-case is evidence."""
        t = _mod()
        self.assertTrue(t.trap_items(self._World(spawn=["4150", "4630"], count=4)))
        self.assertEqual(t.trap_items(self._World(spawn=["4150", "4630"], count=0)), [])


if __name__ == "__main__":
    unittest.main()


class TheClientFeatureHandshake(unittest.TestCase):
    """🛑 er-archipelago#595: seven spawn traps sat in bobler's seed that his client could not read.

    Each would have CONSUMED ITSELF on pickup -- the item arrives, AP marks it delivered,
    `enqueue_by_item_name` does not recognise the name, and it is dropped with no toast and no
    tracker row. `requiresClientFeatures` was honoured in full that session and could not help,
    because spawn traps declared nothing for it to check.

    These pin the declaration. They cannot pin the client honouring it -- that literal lives in the
    other repository's `client_features::SUPPORTED`, which is the same ungated cross-repo string
    contract the item names already carry.
    """

    class _Opt:
        def __init__(self, value):
            self.value = value

    class _World:
        def __init__(self, traps=(), spawn=(), count=0):
            class O:
                pass
            self.options = O()
            self.options.traps = TheClientFeatureHandshake._Opt(frozenset(traps))
            self.options.spawn_traps = TheClientFeatureHandshake._Opt(frozenset(spawn))
            self.options.trap_count = TheClientFeatureHandshake._Opt(count)

    def _declared(self, world):
        from worlds.eldenring import contract
        return _mod().TrapsFeature().slot_data(world).get(contract.REQUIRES_CLIENT_FEATURES, [])

    def test_a_seed_that_mints_a_spawn_trap_declares_the_tag(self):
        """The whole point. Without this an older client connects clean and eats the item."""
        self.assertEqual(self._declared(self._World(traps=["basilisk"], count=4)),
                         [_mod().CLIENT_FEATURE_TAG])
        self.assertEqual(self._declared(self._World(spawn=["4630"], count=1)),
                         [_mod().CLIENT_FEATURE_TAG])

    def test_a_seed_with_no_spawn_traps_declares_nothing(self):
        """🛑 A tag declared by a seed that cannot use it refuses older clients FOR NO REASON, which
        is how a safety check becomes an upgrade tax.

        WITNESS IN THIS TEST, not in a sibling: `slot_data` returning {} for every input would
        satisfy the two assertions below for free, and that is indistinguishable from the feature
        being dead."""
        self.assertEqual(self._declared(self._World(traps=["basilisk"], count=4)),
                         [_mod().CLIENT_FEATURE_TAG],
                         "witness: the declaring path must be alive for the empty cases to mean "
                         "anything")
        self.assertEqual(self._declared(self._World()), [])
        self.assertEqual(self._declared(self._World(traps=["rune_thief", "no_flask"], count=8)), [])

    def test_blackout_declares_its_own_fixed_name_capability(self):
        self.assertEqual(
            self._declared(self._World(traps=["blackout"], count=1)),
            [_mod().BLACKOUT_CLIENT_FEATURE_TAG],
        )
        self.assertEqual(_mod().BLACKOUT_CLIENT_FEATURE_TAG, "blackout")

    def test_blackout_and_spawn_tags_union_without_either_disappearing(self):
        self.assertEqual(
            self._declared(self._World(traps=["blackout", "basilisk"], count=2)),
            [_mod().CLIENT_FEATURE_TAG, _mod().BLACKOUT_CLIENT_FEATURE_TAG],
        )

    def test_a_named_trap_with_a_zero_count_declares_nothing(self):
        """Keyed on the items that WILL EXIST, not on the options being non-empty. `trap_count: 0`
        mints nothing, and a seed that mints nothing needs nothing from the client.

        WITNESSED with the SAME options at a non-zero count, so the empty case is evidence about the
        count rather than about the options never having declared anything."""
        opts = dict(traps=["basilisk"], spawn=["4630"])
        self.assertTrue(self._declared(self._World(count=4, **opts)),
                        "witness: these options DO declare at a non-zero count")
        self.assertEqual(self._declared(self._World(count=0, **opts)), [])

    def test_the_fixed_traps_alone_never_declare_it(self):
        """`Trap: Rune Thief` and friends are EXACT-MATCH names that have never changed, so an older
        client fires them correctly. Requiring the tag for them would refuse clients that can in
        fact run the seed."""
        fixed = ("rune_thief", "no_flask", "runebear")
        # WITNESS, twice over: the corpus is non-empty, and each of these keys really does mint
        # items -- so "declares nothing" is about them being FIXED names, not about the seed being
        # empty.
        self.assertEqual(len(fixed), 3)
        for key in fixed:
            self.assertTrue(_mod().trap_items(self._World(traps=[key], count=4)),
                            f"{key} must actually mint items for its silence to mean anything")
            self.assertEqual(self._declared(self._World(traps=[key], count=4)), [],
                             f"{key} is a fixed name and must not require the tag")

    def test_the_tag_is_pinned_beside_the_format_it_versions(self):
        """🛑🛑 THE TAG VERSIONS THE NAME FORMAT, NOT THE CAPABILITY.

        A client that knows spawn traps but speaks the older
        `Trap: <label> (<chr>/<npc>/<think> x<count>)` shape refuses the name exactly as an ignorant
        client does, so a bare "I do spawn traps" boolean would pass the handshake and still eat the
        item. If the format below changes, this test fails and whoever changed it must mint a NEW
        tag -- otherwise older clients go back to failing silently, which is the whole defect.

        Pinned as a LITERAL, not rebuilt from `spawn_item_name`, so it cannot agree with a reformat
        by construction."""
        self.assertEqual(_mod().spawn_item_name(4150), "Trap: Basilisk x3 (4150/41500060)")
        self.assertEqual(_mod().CLIENT_FEATURE_TAG, "spawn_traps")


class TheNameSurface(unittest.TestCase):
    """`spawn_traps` takes an ENEMY NAME as well as a model id (SwiftyTaco, Discord 2026-08-26).

    🛑 THE MOTIVATING CASE IS THE FIRST TEST HERE, per CONTRIBUTING rule 11. SwiftyTaco asked "Am I
    supposed to put in ids, or the name of the enemy?" after writing model ids into `traps` -- the
    option next to this one, which takes words. Two things had to change and both are pinned below:
    a name works here, and a number in `traps` says where numbers go.

    🛑 AND THE CONTRACT MUST NOT HAVE MOVED. A name is a yaml-side convenience that dies at
    `spawn_trap_models`; everything past it sees the id it always saw. The cases that matter most
    here are the ones asserting the MINTED STRING is byte-identical whichever spelling was written,
    because that identity is the whole argument for why this cost no client release.
    """

    class _Opt:
        def __init__(self, value):
            self.value = value

    class _World:
        def __init__(self, traps=(), spawn=(), count=0):
            class O:
                pass
            self.options = O()
            self.options.traps = TheNameSurface._Opt(frozenset(traps))
            self.options.spawn_traps = TheNameSurface._Opt(frozenset(spawn))
            self.options.trap_count = TheNameSurface._Opt(count)

    def _verify(self, cls, values):
        """Run the option's own `verify`, the way generation runs it."""
        cls(frozenset(values)).verify(None, "SwiftyTaco", None)

    # -- SwiftyTaco's case, end to end
    def test_a_player_writes_an_enemy_name_and_it_works(self):
        """THE ACCEPTANCE TEST. `spawn_traps: [Basilisk]` gens clean and mints the basilisk."""
        t = _mod()
        self._verify(t.SpawnTraps, ["Basilisk"])
        w = self._World(spawn=["Basilisk"], count=2)
        self.assertEqual(t.enabled_trap_names(w), [BASILISK_NAME])
        self.assertEqual(t.trap_items(w), [BASILISK_NAME] * 2)

    def test_the_name_and_the_id_mint_the_same_string(self):
        """🛑 THE CONTRACT ARGUMENT, as an assertion. If these ever differ, accepting names became a
        cross-repo change and the client's parser is the thing that finds out."""
        t = _mod()
        for name, chr_id in (("Basilisk", 4150), ("Runebear", 4630), ("Malenia (Phase 1)", 2120)):
            self.assertEqual(t.trap_items(self._World(spawn=[name], count=1)),
                             t.trap_items(self._World(spawn=[str(chr_id)], count=1)),
                             "%r and %d must mint the same item" % (name, chr_id))

    def test_the_id_spelling_still_works(self):
        """BACK-COMPAT. Every yaml written before names existed keeps its meaning."""
        t = _mod()
        self._verify(t.SpawnTraps, ["4150", "4630"])
        self.assertEqual(sorted(t.spawn_trap_models(self._World(spawn=["4150", "4630"]))),
                         [4150, 4630])

    def test_case_and_accents_do_not_matter(self):
        """A player types what their keyboard has. `Merchant Kale` and `Merchant Kalé` are one
        enemy, and so are `basilisk` and `BASILISK`."""
        t = _mod()
        for spelling in ("basilisk", "BASILISK", "  Basilisk  "):
            self.assertEqual(t._resolve_spawn(spelling), 4150, spelling)
        self.assertEqual(t._resolve_spawn("Merchant Kale"), t._resolve_spawn("Merchant Kalé"))
        self.assertIsNotNone(t._resolve_spawn("Merchant Kale"))

    # -- the refusals, which are the half that must NOT relax
    def test_an_unknown_name_is_a_generation_error_that_names_near_misses(self):
        """🛑 NEVER A SILENT SKIP. A dropped name would be a seed quietly missing the trap the
        player asked for; a bare `Allowed keys: frozenset({...425})` would be a true message nobody
        can act on. Both halves are asserted: it raises, and it suggests."""
        from Options import OptionError
        t = _mod()
        with self.assertRaises(OptionError) as ctx:
            self._verify(t.SpawnTraps, ["Basilsk"])
        self.assertIn("Basilisk", str(ctx.exception))

    def test_an_unspawnable_id_is_still_a_generation_error(self):
        """The refusal this option was built for, unchanged by the new spelling."""
        from Options import OptionError
        t = _mod()
        for bad in ("5350", "9999", "0"):
            with self.assertRaises(OptionError):
                self._verify(t.SpawnTraps, [bad])
        self.assertIsNone(t._resolve_spawn("c4150"), "the c-prefixed form is not a spelling we take")

    def test_a_bad_id_is_not_offered_a_neighbouring_id_as_a_suggestion(self):
        """⭐ `difflib` answers '9999' with '9998'. That is a DIFFERENT CREATURE and a confident
        wrong answer, so ids get told they are not spawnable and are offered nothing."""
        t = _mod()
        msg = t._near("9999")
        self.assertIn("not a spawnable", msg)
        self.assertNotIn("did you mean", msg)

    def test_a_number_in_traps_says_where_numbers_go(self):
        """SwiftyTaco's actual first move. The two lists sit next to each other, one took words and
        one took numbers, and the stock message named neither."""
        from Options import OptionError
        t = _mod()
        with self.assertRaises(OptionError) as ctx:
            self._verify(t.Traps, ["4150"])
        self.assertIn("spawn_traps", str(ctx.exception))
        # NOT relaxed: the id is still refused here, it is only explained.
        self.assertNotIn("4150", t.Traps.valid_keys)

    def test_traps_still_refuses_an_ordinary_unknown_word(self):
        """WITNESS for the case above -- the new branch must not have swallowed the inherited one."""
        from Options import OptionError
        t = _mod()
        with self.assertRaises(OptionError):
            self._verify(t.Traps, ["rune_theif"])
        self._verify(t.Traps, ["rune_thief", "basilisk"])   # and the good values still pass

    # -- the table itself
    def test_a_shared_name_resolves_to_the_lowest_model_id_deterministically(self):
        """🛑 THREE NAMES ARE ON TWO MODELS EACH (one NPC, two bodies). A name that resolved to
        'whichever the dict emitted first' would make the same yaml build different seeds across
        runs; the rule is the LOWEST id and `enemy_names.ENEMY_NAME_COLLISIONS` records the rows."""
        from worlds.eldenring.enemy_names import ENEMY_NAMES, ENEMY_NAME_COLLISIONS
        t = _mod()
        self.assertTrue(ENEMY_NAME_COLLISIONS, "witness: the collision table must not be empty")
        for chr_id, (name, others) in ENEMY_NAME_COLLISIONS.items():
            self.assertEqual(t._resolve_spawn(name), min([chr_id] + list(others)), name)
        # Rebuilding the index must give the same answer, not merely an answer.
        self.assertEqual(t._build_name_index(), t.SPAWN_NAME_INDEX)
        self.assertEqual(len(ENEMY_NAMES), 35)

    def test_every_named_model_is_spawnable_and_every_name_resolves(self):
        """A name for a model this world refuses to spawn would be a yaml value that gens dirty --
        the id problem inverted. WITNESSED by the length assert so an empty table cannot pass."""
        from worlds.eldenring.enemy_names import ENEMY_NAMES
        t, rows = _mod(), _data().SPAWN_TRAPS
        self.assertGreater(len(ENEMY_NAMES), 30)
        for chr_id, name in ENEMY_NAMES.items():
            self.assertIn(chr_id, rows, "c%d is named but not spawnable" % chr_id)
            self.assertIsNotNone(t._resolve_spawn(name), name)

    def test_every_valid_key_resolves(self):
        """`valid_keys` is what the wizard offers and what the error suggests out of. A member that
        does not resolve would be a value the wizard writes and generation then rejects."""
        t = _mod()
        for k in t.SpawnTraps.valid_keys:
            self.assertIsNotNone(t._resolve_spawn(k), k)

    def test_the_names_are_reachable_from_the_option_the_player_reads(self):
        """DOCSTRING = WIZARD METADATA. The names only help if they are written where the option is
        described, so the docstring has to carry them and to say ids still work."""
        doc = _mod().SpawnTraps.__doc__
        for needle in ("Basilisk", "Runebear", "model id", "4150"):
            self.assertIn(needle, doc, needle)

    def test_the_contract_hash_did_not_move(self):
        """🛑 THE PIN. Names are resolved at generation and the emitted slot data is untouched, so
        this change owed no client release. The later foreign-Lock placement contract move is
        separately versioned; this pin still proves the spawn-name work added no further shape."""
        from worlds.eldenring import contract
        self.assertEqual(contract.CONTRACT_HASH[:8], "ffc0f1b5")

    def test_a_name_the_game_writes_with_a_comma_is_offered_without_one(self):
        """🛑 A COMMA IS A SEPARATOR WHERE PLAYERS WRITE THESE. `spawn_traps: [Alexander, Warrior
        Jar]` is TWO yaml values, and the wizard's box splits on commas so pasting a list works, so
        an accepted value carrying one cannot survive being typed. Six names carry one; the offered
        spelling drops it and the game's spelling still resolves."""
        from worlds.eldenring.enemy_names import ENEMY_NAMES
        t = _mod()
        commad = [n for n in ENEMY_NAMES.values() if "," in n]
        self.assertGreaterEqual(len(commad), 5, "witness: the comma'd population must not be empty")
        for name in commad:
            plain = t.yaml_name(name)
            self.assertNotIn(",", plain)
            self.assertEqual(t._resolve_spawn(plain), t._resolve_spawn(name), name)
            self.assertIn(plain, t.SpawnTraps.valid_keys)
            self.assertNotIn(name, t.SpawnTraps.valid_keys)
        self.assertEqual(t.yaml_name("Alexander, Warrior Jar"), "Alexander Warrior Jar")

    def test_the_offered_spelling_survives_a_yaml_flow_list(self):
        """The end of the same argument, run through a real yaml parser rather than reasoned about:
        every accepted value has to come back out of `[a, b]` as itself."""
        import yaml
        t = _mod()
        offered = sorted(k for k in t.SpawnTraps.valid_keys if not k.isdigit())
        self.assertGreater(len(offered), 30)
        parsed = yaml.safe_load("spawn_traps: [%s]" % ", ".join(offered))["spawn_traps"]
        self.assertEqual(parsed, offered)
        for v in parsed:
            self.assertIsNotNone(t._resolve_spawn(v), v)
