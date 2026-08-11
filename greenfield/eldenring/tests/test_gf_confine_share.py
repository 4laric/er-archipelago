"""`confine_foreign_progression` as a SHARE -- the option that decides how much of another world's
progression is held to our Progression Surface.

WHY IT STOPPED BEING A TOGGLE (measured 2026-08-10, Archipelago 0.6.7, shipped yaml, num_regions 6).
The rule is about OUR locations but it displaces the NEIGHBOUR: barred from our ~3000 filler checks,
a partner game's progression has nowhere but its own locations and saturates them during
`fill_restrictive`. Archipelago then places the entire `useful` tier before any filler
(`Fill.py`: `restitempool = filleritempool + usefulitempool`, popped from the tail), so by the time
the scan reaches what is left of the partner's world only filler is available. Of 498 Elden Ring
items that reached Hollow Knight across three seeds, ZERO were useful -- no weapon, no armour, no
talisman -- while the other Elden Ring slot received 43.1% useful. Turning the flag off sent Hollow
Knight 40.7% useful, the pool's own mix. boblerrr reported the symptom from a live seed the same day.

🛑 WHAT THESE TESTS ARE FOR, and it is not "the option exists". Two things can silently break:
  1. The 100 default must be EXACTLY the old toggle. Not "equivalent" -- the same predicate object,
     so the shipped seed cannot move. `test_full_share_is_the_old_predicate_object` pins that.
  2. A yaml saying `true` must still mean 100. `bool` is a subclass of `int` in Python, so AP's
     `Range.from_any` would read `true` as the integer 1 -- one percent, indistinguishable from off
     -- and every yaml in the wild says `true`. That is a SILENT inversion of the option, and it is
     the single most likely way this change hurts somebody. Four cases below cover it.
"""
import pytest
import yaml

WorldTestBase = pytest.importorskip("test.bases").WorldTestBase
pytest.importorskip("worlds.eldenring")

from worlds.eldenring.features.progression_surface import (  # noqa: E402
    ConfineForeignProgression, confine_pct, confined_surface_ids, foreign_advancement_barred,
    foreign_bar_for,
)

GAME = "Elden Ring"


class _Item:
    def __init__(self, name, player, advancement=True):
        self.name = name
        self.player = player
        self.advancement = advancement


class _World:
    """The smallest thing `foreign_bar_for` reads: options.value, multiworld.seed, player."""
    def __init__(self, pct, seed=1234, player=1):
        self.options = type("O", (), {"confine_foreign_progression": type("V", (), {"value": pct})()})()
        self.multiworld = type("M", (), {"seed": seed})()
        self.player = player


# ---- the option class itself --------------------------------------------------------------------

def test_default_is_a_full_share():
    """The default must be the pre-share behaviour. Moving it is a separate, measured decision --
    this test is what makes that move deliberate rather than incidental."""
    assert ConfineForeignProgression.default == 100
    assert ConfineForeignProgression.range_start == 0
    assert ConfineForeignProgression.range_end == 100


@pytest.mark.parametrize("data,expected", [(True, 100), (False, 0)])
def test_a_yaml_bool_keeps_meaning_what_it_meant(data, expected):
    """🛑 THE MIGRATION CASE. `bool` is an `int`, so without the `from_any` override `true` becomes
    1 -- a 1% share, which reads as OFF. Every shipped yaml says `true`."""
    assert ConfineForeignProgression.from_any(data).value == expected


@pytest.mark.parametrize("text,expected", [("true", 100), ("false", 0),
                                           ("all", 100), ("none", 0)])
def test_the_named_values_map_to_the_endpoints(text, expected):
    assert ConfineForeignProgression.from_any(text).value == expected


@pytest.mark.parametrize("scalar,expected", [("true", 100), ("false", 0), ("on", 100), ("off", 0),
                                             ("yes", 100), ("no", 0)])
def test_a_yaml_boolean_spelling_reaches_the_endpoint_without_being_a_named_value(scalar, expected):
    """🛑 `on` / `off` are deliberately NOT in `special_range_names` -- see the option's comment;
    listing them made AP's generated template hold a duplicate key. They still work, and this is the
    test that says so, because it goes through the yaml loader rather than handing `from_any` a
    string the loader would never have produced. All six spellings below are YAML 1.1 booleans, so
    each arrives as a Python `bool` and the `from_any` bool catch answers it."""
    value = yaml.safe_load("confine_foreign_progression: %s" % scalar)["confine_foreign_progression"]
    assert isinstance(value, bool), "%r stopped being a yaml boolean" % scalar
    assert ConfineForeignProgression.from_any(value).value == expected


@pytest.mark.parametrize("data", [0, 25, 50, 100])
def test_a_plain_number_is_taken_as_a_percent(data):
    assert ConfineForeignProgression.from_any(data).value == data


# ---- the predicate ------------------------------------------------------------------------------

def test_full_share_is_the_old_predicate_object():
    """Not merely equivalent -- IDENTICAL. If this ever returns a wrapper instead, the default seed
    has started running new code and any drift in it is invisible to every default-config gate."""
    assert foreign_bar_for(_World(100)) is foreign_advancement_barred


def test_zero_share_bars_nothing():
    barred = foreign_bar_for(_World(0))
    assert barred(_Item("Mothwing Cloak", player=2), player=1) is False


def test_a_share_only_ever_bars_foreign_advancement():
    """Whatever the percentage, our own items and everybody's non-progression are untouched. A
    regression here would bar filler from our own filler checks, which is a FillError, not a nudge."""
    barred = foreign_bar_for(_World(50))
    assert barred(_Item("Limgrave Lock", player=1), player=1) is False, "our own advancement passes"
    assert barred(_Item("Geo Chest", player=2, advancement=False), player=1) is False, \
        "foreign non-advancement passes"


def test_the_draw_is_stable_across_calls():
    """`item_rule` is called an unbounded number of times per item -- once per candidate location,
    again on every swap in `remaining_fill`. An rng draw there would answer differently each time,
    which is not a share of anything. Same item, 200 calls, one answer."""
    barred = foreign_bar_for(_World(50))
    it = _Item("Crystal Heart", player=2)
    answers = {barred(it, 1) for _ in range(200)}
    assert len(answers) == 1


def test_two_er_slots_in_one_seed_do_not_agree():
    """The salt carries OUR player number. Without it every Elden Ring world in a multiworld would
    confine the same names, so an item barred from one would be barred from all of them -- a far
    harder rule than 50% claims, and one that would put the displacement straight back."""
    a = foreign_bar_for(_World(50, seed=7, player=1))
    b = foreign_bar_for(_World(50, seed=7, player=2))
    names = ["item %d" % i for i in range(200)]
    va = [a(_Item(n, player=3), 1) for n in names]
    vb = [b(_Item(n, player=3), 2) for n in names]
    assert va != vb, "two ER slots drew the identical confinement set"


def test_the_share_is_roughly_the_percentage():
    """A propensity, not a quota -- so this asserts a band, not a number. 400 names at 50% lands
    well inside +/-10 points unless the hash is broken or the comparison is inverted."""
    barred = foreign_bar_for(_World(50, seed=99))
    names = ["foreign item %d" % i for i in range(400)]
    hits = sum(1 for n in names if barred(_Item(n, player=2), 1))
    assert 40 <= (100 * hits / len(names)) <= 60


@pytest.mark.parametrize("pct,lo,hi", [(10, 2, 20), (90, 80, 98)])
def test_the_share_tracks_the_endpoints_too(pct, lo, hi):
    barred = foreign_bar_for(_World(pct, seed=5))
    names = ["n%d" % i for i in range(400)]
    hits = 100 * sum(1 for n in names if barred(_Item(n, player=2), 1)) / len(names)
    assert lo <= hits <= hi


def test_an_absent_option_behaves_as_before_the_option_existed():
    """A stubbed or older world must not silently start letting foreign progression onto its filler
    checks. Absent -> 100, the opposite endpoint from `_released_pct`'s absent -> 0, and for the same
    reason: both mean 'behave as you did before this knob'."""
    class _Bare:
        options = type("O", (), {})()
    assert confine_pct(_Bare) == 100


# ---- the surface resolution -----------------------------------------------------------------------

class ConfineSurfaceOff(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "confine_foreign_progression": 0}

    def test_zero_share_installs_no_bar_at_all(self):
        """0 must be the same "feature inactive" state the old `false` produced, all the way down to
        core not installing an item_rule -- not a bar that happens to say yes to everything.

        The `assertGreater` is a WITNESS, in the sense test_gf_vacuous_pass.py means it: "no bar was
        installed" is trivially true of a world with nothing to install it on, so the test has to say
        out loud that it saw locations first."""
        addressed = [loc for loc in self.multiworld.get_locations(self.player)
                     if getattr(loc, "address", None) is not None]
        self.assertGreater(len(addressed), 0,
                           "this world has no addressed locations, so 'no foreign bar was "
                           "installed' would pass over nothing")
        self.assertIsNone(confined_surface_ids(self.world))
        self.assertEqual(confine_pct(self.world), 0)


class ConfineSurfaceHalf(WorldTestBase):
    game = GAME
    options = {"num_regions": 0, "confine_foreign_progression": 50}

    def test_a_partial_share_still_resolves_a_surface(self):
        """The surface must exist for the confined half to be confined TO. A share that quietly
        turned the surface off would read as 'working' in every count-based check."""
        self.assertEqual(confine_pct(self.world), 50)
        self.assertIsNotNone(confined_surface_ids(self.world))


class ConfineSurfaceDefault(WorldTestBase):
    game = GAME
    options = {"num_regions": 0}

    def test_the_shipped_default_confines_everything(self):
        self.assertEqual(confine_pct(self.world), 100)
        self.assertIs(self.world._foreign_barred_fn, foreign_advancement_barred)
