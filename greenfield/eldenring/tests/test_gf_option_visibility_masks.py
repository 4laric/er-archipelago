"""Which options a player sees on each built-in Archipelago surface -- pinned in ONE table.

A newcomer reported that the options screen was overwhelming: 77 options on one page, five of the
first thirteen about region shape before the boss row. The Launcher's Options Creator and the WebHost
player-options page show ONLY options flagged `Visibility.simple_ui`; the WebHost weighted-options
page shows `complex_ui`; the generated template yaml shows `template`; the spoiler writes `spoiler`.
Demoting a dial off the simple page therefore does not delete it: it is still a valid yaml key, still
parses, still in the template and on the weighted page.

TWO MASKS, and neither is `Visibility.none`:
  * COMPAT   (complex_ui | spoiler)   superseded or inert keys. Off every surface except the weighted
                                      page and the spoiler; still parsed so an old yaml loads.
  * ADVANCED (all & ~simple_ui)       real dials a first-time player does not need. Still in the
                                      template, on the weighted page and in the wizard's More fold.

WHY NOT `Visibility.none` FOR THESE. It also removes the key from the metadata the wizard reads:
measured on a dry run over the 15 keys proposed for demotion it made 42 new er_yaml_lint errors in 12
shipped yamls, emptied three of the wizard's six pick groups and refused every old wizard export.
Commit f91cd789 (progression_sharing) DID use `none` for the three keys it retired -- fine there,
because nothing offers those keys any more. These are live dials the wizard still offers, so they
need a mask that leaves them in the metadata. `LEGACY_NONE_KEYS` below is that grandfathered set.

A NEW OPTION IS NOT AUTOMATICALLY HIDDEN. It is visible by default, which is the safe direction: a
knob a player cannot find is worse than one they can. Add a key to a table below only on purpose.
"""
import dataclasses
import typing

import pytest

pytest.importorskip("worlds.eldenring")

import Options  # noqa: E402
from Options import PerGameCommonOptions, Visibility  # noqa: E402
from worlds.eldenring.core import GFOptions, GreenfieldEldenRingWorld  # noqa: E402

COMPAT_MASK = Visibility.complex_ui | Visibility.spoiler
ADVANCED_MASK = Visibility.all & ~Visibility.simple_ui

COMPAT_KEYS = frozenset({
    "leyndell_runes_required", "global_scadutree_blessing", "merchant_bell_logic",
    "flask_upgrades_on_progression_surface",
})
ADVANCED_KEYS = frozenset({
    "curated_filler", "spawn_traps", "num_regions_order", "start_region_selection",
    "death_link_amnesty_inbound", "death_link_amnesty_outbound", "full_area_sweeps",
    "region_sweep", "reveal_sweep_boss_names", "keep_local_rune_cap", "pool_builder_intensity",
    "capital_reconciler", "coop_difficulty", "scale_rune_rewards", "enable_dlc_gear",
    "scadutree_blessing_scope", "dlc_blessing_catchup", "grace_attunement",
    "grace_attunement_anchor", "reroll_enemy_drops", "reroll_mine_materials",
    "pool_builder_pct_weapons", "pool_builder_pct_armor", "pool_builder_pct_spells",
    "pool_builder_pct_talismans", "pool_builder_pct_ashes_of_war", "ability_unlocks_required",
})
# Considered for demotion and deliberately kept on the simple page. Recorded so nobody re-derives it.
KEPT_VISIBLE_ON_PURPOSE = {
    "no_runes_in_shops": "the one-click alternative, keep_out_of_shops: runes, is not yet proven on "
                         "tiny seeds; demote it once test_gf_options sweeps that case",
    "start_with_whetblades": "waiting on an in-game check of whether the five items unlock Ash of "
                             "War affinities",
    "start_regions": "the only simple-UI way to ask for more than one open region",
}
# The six options a first-time player meets first. Order is the order on the page.
START_HERE = ["enable_dlc", "num_regions", "goal", "goal_great_runes", "enemy_scaling", "death_link"]

WORLD = GreenfieldEldenRingWorld
HINTS = typing.get_type_hints(GFOptions)
# Archipelago's own common options (accessibility, local_items, start_inventory ...) are not ours.
_COMMON = {f.name for f in dataclasses.fields(PerGameCommonOptions)} | {"accessibility", "progression_balancing"}
OURS = {f.name for f in dataclasses.fields(GFOptions)} - _COMMON


def _page(level):
    """{group: [our option keys]} exactly as Archipelago's own group filter renders it."""
    groups = Options.get_option_groups(WORLD, visibility_level=level)
    return {g: [k for k in opts if k in OURS] for g, opts in groups.items()}


def _flat(page):
    return {k for keys in page.values() for k in keys}


def test_the_two_tables_are_disjoint_and_name_real_options():
    assert not COMPAT_KEYS & ADVANCED_KEYS
    assert (COMPAT_KEYS | ADVANCED_KEYS) <= OURS, sorted((COMPAT_KEYS | ADVANCED_KEYS) - OURS)
    assert set(KEPT_VISIBLE_ON_PURPOSE) <= OURS
    assert not set(KEPT_VISIBLE_ON_PURPOSE) & (COMPAT_KEYS | ADVANCED_KEYS)


@pytest.mark.parametrize("key", sorted(COMPAT_KEYS))
def test_a_compat_key_has_exactly_the_compat_mask(key):
    assert HINTS[key].visibility == COMPAT_MASK, key


@pytest.mark.parametrize("key", sorted(ADVANCED_KEYS))
def test_an_advanced_key_has_exactly_the_advanced_mask(key):
    assert HINTS[key].visibility == ADVANCED_MASK, key


# The keys that are ALREADY `Visibility.none`, grandfathered: `Options.Removed` stubs (whose whole job
# is to raise on a stale yaml) and the three keys progression_sharing replaced (commit f91cd789).
# tools/dump_options_metadata.py prints exactly this list as "hiding 12 non-visible option(s)".
LEGACY_NONE_KEYS = frozenset({
    "pool_builder", "pool_builder_scope", "pool_builder_juice_cap", "pool_builder_juice_pct",
    "local_item_only", "exclude_local_item_only", "progression_surface_mode", "progression_bias",
    "confine_foreign_progression", "cross_game_progression", "completion_scaling_floor",
    "completion_scaling_ramp",
})


def test_no_new_key_uses_visibility_none():
    """A NEW demotion must use one of the two masks above, never `Visibility.none`: none also removes
    the key from the metadata the wizard reads, so the wizard cannot offer it, er_yaml_lint flags it
    in every shipped yaml that sets it, and old wizard exports are refused. The set below is
    grandfathered and must not grow."""
    none_keys = {k for k, c in HINTS.items() if k in OURS and c.visibility == Visibility.none}
    assert none_keys == LEGACY_NONE_KEYS, (
        "Visibility.none changed. New: %s. Gone: %s. Use COMPAT or ADVANCED for a new demotion."
        % (sorted(none_keys - LEGACY_NONE_KEYS), sorted(LEGACY_NONE_KEYS - none_keys)))


def test_the_simple_page_shows_no_demoted_key_and_the_weighted_page_shows_all_of_them():
    simple = _flat(_page(Visibility.simple_ui))
    weighted = _flat(_page(Visibility.complex_ui))
    demoted = COMPAT_KEYS | ADVANCED_KEYS
    assert not simple & demoted, sorted(simple & demoted)
    assert demoted <= weighted, sorted(demoted - weighted)


def test_advanced_keys_stay_in_the_template_and_compat_keys_do_not():
    template = _flat(_page(Visibility.template))
    assert ADVANCED_KEYS <= template, sorted(ADVANCED_KEYS - template)
    assert not COMPAT_KEYS & template, sorted(COMPAT_KEYS & template)


@pytest.mark.parametrize("key", sorted(COMPAT_KEYS | ADVANCED_KEYS))
def test_a_hidden_key_still_parses_its_own_default(key):
    """The contract of hiding: an existing yaml that names the key must still load."""
    cls = HINTS[key]
    cls.from_any(cls.default)  # must not raise
    if issubclass(cls, Options.Choice):
        for name in cls.options:  # every documented spelling of a Choice must still parse
            assert cls.from_any(name).value == cls.options[name], (key, name)


def test_the_first_page_a_newcomer_meets_is_start_here():
    """Six decisions answerable without opening a tooltip. If this grows, the 'overwhelming first
    page' complaint is back."""
    page = _page(Visibility.simple_ui)
    ours = [(g, keys) for g, keys in page.items() if keys]
    assert ours[0][0] == "Start Here"
    assert ours[0][1] == START_HERE


def test_the_simple_page_stays_small():
    """A ratchet, not a rule: 77 options used to be on this page; 47 are now. Raising the number
    means a new option went onto the newcomer's page -- decide that on purpose."""
    n = len(_flat(_page(Visibility.simple_ui)))
    assert n <= 50, "%d of our options are on the simple page; the ceiling is 50" % n
