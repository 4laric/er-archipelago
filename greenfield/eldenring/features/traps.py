"""traps -- trap items in the filler pool.

WHAT A TRAP IS HERE. An AP item that makes your run momentarily worse: it takes half your runes,
stops your flask healing for twenty seconds, blacks out the screen briefly, or drops an enemy on
your head. bobler and Alaric designed the set on 2026-08-08 (issue #114); only live-confirmed,
client-implemented effects enter this catalogue.

## Why this costs no contract move

A trap is a SYNTHETIC item, exactly like `Boss Key: <Boss>` and `<Region> Lock`: it declares `ITEMS`
and no `ITEM_GRANTS`, so it never enters `_AP_IDS_TO_ITEM_IDS` and the game is never asked to hand
anything over. The client recognises it by NAME in the receive stream, the same way it already
recognises Boss Keys, and fires the effect itself. No new slot_data key, no `CONTRACT_HASH` move, no
version lockstep -- which is the opposite of what the design note in #114 assumed, and worth saying
out loud because it is the reason this is small.

🛑 THE COST OF THAT CHOICE: the item NAME is a cross-repo contract with no gate behind it. Rename
`Trap: Rune Thief` here and the client silently stops recognising it -- no error, no failed build,
just a trap that does nothing. `test_gf_traps.py` pins the exact strings, and `er_logic::traps`
carries the same list with its own test. Change one, change both.

## The rules this obeys (issue #114)

3. Traps are FILLER-class and count-neutral: each trap displaces one filler item, never a useful one,
   and no progression may ride a trap. `core.create_items` sizes filler off `len(pool)`, so returning
   N items here removes N fillers and the pool total is unchanged.
4. 🛑 ADDING a trap name later is safe; REMOVING one is a compat break -- an OptionSet value that
   vanishes fails an old yaml. Never ship a name you might withdraw. That is why this file ships
   only confirmed names and not the eleven in the design: these are implemented, tested and
   CI-gated in the client. The rest arrive when they work, not when they are decided.

## Defaults

OFF. `traps` is an empty OptionSet, so a seed that does not name a trap is byte-identical to one
built before this file existed -- `create_items` returns `[]` and nothing else here runs.
"""
import difflib
import unicodedata
from typing import List, Optional, Set

from BaseClasses import ItemClassification
from Options import OptionError, OptionSet, Range

from ..registry import Feature, register
from .. import contract
from ..enemy_names import ENEMY_NAMES
from ..spawn_trap_data import SPAWN_TRAPS, SPAWN_TRAP_KEYS

#: 🛑 CROSS-REPO CONTRACT with `er_logic::traps::LABEL_CAP`. The client retains a spawn label INLINE
#: so its `SpawnSpec` can stay `Copy`, and REFUSES a longer one rather than truncating -- a
#: truncated label would silently rename the creature in the one line the player ever reads.
#: `tools/datamine_spawn_traps.py` asserts the same ceiling when it emits the table; this pins it on
#: the consuming side too, because the tsv can be hand-edited.
LABEL_CAP = 24


def yaml_name(name: str) -> str:
    """The game's spelling of a name -> the spelling the yaml and the wizard offer.

    🛑 COMMAS COME OUT, and this is not cosmetic. Six of the 35 names carry one -- `Alexander,
    Warrior Jar`, `Rennala, Queen of the Full Moon`, `Miriel, Pastor of Vows` and friends -- and a
    comma is a SEPARATOR in both places a player writes one of these: yaml flow style
    (`spawn_traps: [Alexander, Warrior Jar]` is two values, not one) and the wizard's text box,
    which splits on commas so that pasting a list of ids works at all. An accepted value that
    cannot survive being typed is not accepted. Caught by `tools/check_wizard_renders.py`, which
    types every multi-word accepted value into the live control.

    The COMMA'D spelling still resolves -- `_build_name_index` indexes both -- because it is what
    the game says and what a player copying from a wiki will write. Only the OFFERED spelling
    changes.
    """
    return " ".join(name.replace(",", " ").split())


def _fold(s: str) -> str:
    """The form two spellings of one name are compared in: casefolded, accent-stripped, and with
    runs of whitespace collapsed.

    ⭐ ACCENTS ARE STRIPPED because `Merchant Kale` is what a player with a US keyboard types and
    `Merchant Kal\u00e9` is what the game's FMG says. Refusing the first over one diacritic would be
    the id problem again in a smaller costume. The CANONICAL spelling -- the one in `ENEMY_NAMES`,
    the wizard and the yaml template -- keeps its accent; only the comparison drops it.
    """
    n = unicodedata.normalize("NFKD", s.strip().casefold())
    return " ".join("".join(c for c in n if not unicodedata.combining(c)).split())


#: The prefix the client dispatches on. Kept as a constant so the test can assert every name
#: carries it -- a trap named without it is a filler item that silently never fires.
TRAP_PREFIX = "Trap: "


#: The client-feature tag a seed declares when it mints ANY spawn trap. er-archipelago#595.
#:
#: 🛑 WHY A TAG AT ALL. bobler's 2026-08-12 seed placed seven spawn traps and his client could not
#: read their names, so each one would have CONSUMED ITSELF on pickup: the item arrives, AP marks it
#: delivered, `enqueue_by_item_name` does not recognise the name, and it is dropped. No toast, no
#: tracker row, no way to get it back. `requiresClientFeatures` was honoured in full that session and
#: could not help, because spawn traps declared nothing for it to check.
#:
#: 🛑🛑 THE TAG VERSIONS THE NAME FORMAT, NOT JUST THE CAPABILITY. A client that knows spawn traps
#: but speaks the older `Trap: <label> (<chr>/<npc>/<think> x<count>)` shape refuses the name exactly
#: as an ignorant client does -- so a bare "I do spawn traps" boolean would pass the handshake and
#: still eat the item. Change `spawn_item_name`'s format and this tag MUST change with it; the client
#: adds the new tag in the same release that learns the new shape, and older clients then say
#: CLIENT TOO OLD instead of failing quietly. `test_gf_spawn_traps` pins the two together so the
#: format cannot move without this line moving.
#:
#: Deliberately NOT declared by the older fixed traps (`Trap: Rune Thief` and friends): their names
#: are exact-match and have never changed, so an older client reads them correctly. Blackout gets
#: its own tag below because it is a new fixed name.
CLIENT_FEATURE_TAG = "spawn_traps"

#: A fixed-name capability tag for the newly promoted Blackout trap. Unlike the older fixed traps,
#: clients already in circulation do not recognise this name and would consume it silently.
BLACKOUT_CLIENT_FEATURE_TAG = "blackout"


def spawn_item_name(chr_id: int) -> str:
    """The item name a spawn trap for `chr_id` mints. THE PAYLOAD IS IN THE NAME.

    `Trap: Basilisk x3 (4150/41500060)` -- label, horde size, then the two ids the client cannot
    derive for itself.

    ⭐ THE THINK ROW IS NOT IN THE NAME, and its absence is proved rather than assumed. A model only
    enters this table if `NpcThinkParam` has a row at exactly `<chr>0000` -- that IS the eligibility
    rule -- so `think == chr_id * 10000` for all 390 rows, and the client derives it.
    `test_gf_spawn_traps` holds that premise against the real table; if it ever fails, the name can
    no longer express reality and the field has to come back. The npc row is NOT derivable (300 of
    390 differ from the template), so it stays.

    ⭐ THE PAYLOAD IS LAST, and the count sits with the label, because Archipelago fuzzy-matches item
    names in `!getitem` / `/send` (`Utils.get_intended_text`, 75% threshold). With 389 uncurated
    names shaped `Trap: cNNNN ...` they are near-identical to EACH OTHER, and a payload in the
    middle pushed the only distinguishing text past where the matcher weighs it. Leading with
    `Trap: c4630 x1` gives the match something to bite on.

    🛑 THE FORMAT IS ONLY FREE TO CHANGE UNTIL A TAG. Nothing has shipped it yet (the v0.3.12 window
    is open), so this reshaping costs nothing. After a release it is a compat break for every seed
    in flight, and the client refuses -- loudly, by design -- anything it cannot parse.

    🛑 WHY THE NAME AND NOT slot_data. A spawn trap is a SYNTHETIC item like every other trap: it
    declares `ITEMS` and no `ITEM_GRANTS`, and the client recognises it by NAME. Putting the ids in
    slot_data instead would be a CONTRACT MOVE -- a new key, both repos in lockstep, `CONTRACT_HASH`
    moving, a version bump -- to carry three integers the name can carry for free.

    🛑 THE COST, stated plainly: this name is a promise to another repository with nothing enforcing
    it. `er_logic::traps::SpawnSpec::from_item_name` parses exactly this shape and REFUSES anything
    else. `test_gf_spawn_traps` pins the format; the client pins its own parser. Change one, change
    both -- the failure mode is an item that arrives, is filler, and does nothing forever.
    """
    label, npc, _think, count = SPAWN_TRAPS[chr_id]
    return "%s%s x%d (%d/%d)" % (TRAP_PREFIX, label, count, chr_id, npc)

# The trap catalogue: option value -> item name. 🛑 BOTH SIDES OF THIS TABLE ARE PUBLIC.
# The KEY is a yaml value a player types and may not be renamed (rule 4). The VALUE is the string
# the client matches on; `er_logic::traps::Trap::from_item_name` carries the same list.
TRAPS = {
    "rune_thief": "Trap: Rune Thief",
    "no_flask": "Trap: No Flask",
    "blackout": "Trap: Blackout",
    "runebear": "Trap: Runebear",
}



class Traps(OptionSet):
    """Which traps may appear in your world. Empty (default) = no traps at all.

    A trap is an item that makes your run briefly worse. They are FILLER: a trap never holds
    progression, and every trap in your pool replaces one junk item, so your seed does not grow.

    - **rune_thief** -- half your runes, gone.
    - **no_flask** -- your flask heals nothing for 20 seconds. You can still drink it; it just does
      nothing, and the charge is spent.
    - **blackout** -- the screen fades out, stays dark for 2 seconds, then fades back in.
    - **runebear** -- a Runebear appears exactly where you are standing. Kill it and you keep the
      runes.
    - **basilisk** -- THREE basilisks appear where you are standing. One is a joke; three is the
      Death Blight mist, which kills outright. Killing you sends a DeathLink.

    Traps are sent to YOU by your own world like any other item, so in a multiworld somebody else
    may be the one who finds them.

    THIS OPTION TAKES THESE WORDS AND NOTHING ELSE. For any other enemy in the game -- by name or by
    character model id -- use `spawn_traps`, which is the other list in this section.
    """
    display_name = "Traps"
    # 🛑 The union, not `TRAPS` alone: a curated spawn key is a yaml value exactly like a fixed
    # trap's, and leaving it out would make `traps: [basilisk]` an unknown-key error.
    valid_keys = frozenset(TRAPS) | frozenset(SPAWN_TRAP_KEYS)
    default = frozenset()

    def verify(self, world, player_name: str, plando_options) -> None:
        """The inherited exact-key check, plus ONE SENTENCE for the mistake that actually happened.

        SwiftyTaco, Discord 2026-08-26, put character model ids in THIS option -- the two lists sit
        next to each other in the wizard, one takes words and one took numbers, and nothing said
        which was which. `Found unexpected key 4150 ... Allowed keys: frozenset({'no_flask', ...})`
        is a true message that answers a question nobody asked. A number here is never a typo for
        `rune_thief`; it is always somebody who meant `spawn_traps`, so say so.

        🛑 The check is not RELAXED -- ids are still refused here, because a trap named in the wrong
        option would be an item that never fires. Only the sentence is new.
        """
        stray = sorted(v for v in self.value if str(v).strip().isdigit())
        if stray:
            raise OptionError(
                "Player %s put character model id(s) %s in `traps`. Those go in `spawn_traps`, "
                "which takes ids AND enemy names; `traps` takes only these words: %s."
                % (player_name, ", ".join(str(v) for v in stray), ", ".join(sorted(self.valid_keys))))
        super().verify(world, player_name, plando_options)


class SpawnTraps(OptionSet):
    """Extra enemies to drop on your own head. Takes an ENEMY NAME or a character model id.

    THE ESCAPE HATCH. `traps` carries the enemies we curated and named; this takes any of the 390
    spawnable models in the game, for anyone who wants something specific standing on top of them.
    One appears where you are; the curated ones may come in numbers.

    Both spellings work and mean the same thing, so write whichever you have::

        spawn_traps: [Basilisk, Runebear]     # a name -- case does not matter
        spawn_traps: ["4150", "4630"]         # the same two models, by id

    THE NAMED MODELS (35 of the 390):

    Aging Untouchable, Alexander Warrior Jar, Asimi Silver Tear, Basilisk, Blaidd the Half-Wolf,
    Boc the Seamster, Demi-Human Boc, Finger Reader Crone, Finger Reader Enia, Gatekeeper Gostoc,
    Gurranq Beast Clergyman, Hornsent Grandam, Jar-Bairn, Latenna the Albinauric,
    Malenia (Phase 1), Melina, Merchant Kale, Miriel Pastor of Vows, Pidia Carian Servant,
    Primeval Sorcerer Azur, Primeval Sorcerer Lusat, Ranni the Witch,
    Rennala Queen of the Full Moon, Runebear, Smithing Master Hewg, Smithing Master Iji,
    Sorceress Sellen, St. Trina, Tanith's Knight, The Noble Goldmask, The Two Fingers,
    Zorayas the Scout. (Six of these carry a comma in the game -- `Alexander,
    Warrior Jar`. A comma separates values in yaml flow style and in the wizard box, so the
    offered spelling drops it; both spellings resolve.)

    THE OTHER 355 HAVE NO NAME TO TAKE, and that is the game's doing rather than an omission here:
    Elden Ring never writes an enemy's name on screen, so outside `NpcName.fmg.xml` -- 31 of these
    models -- there is no name in the data to use, and this project will not invent one. Those
    models stay reachable by id, which is what they always were.

    Empty by default, and inert unless `trap_count` is above zero. A name or id that is not
    spawnable is a yaml ERROR naming its nearest matches, rather than an item that silently never
    fires -- 26 models are excluded because they have no AI row or no body (props like the Walking
    Mausoleum), and refusing them at generation is the point.

    Naming the same enemy here and in `traps` is harmless: it is one item either way.

    🛑 THE ITEM IS STILL NAMED AFTER THE MODEL, not after what you typed: `Runebear` here mints
    `Trap: c4630 x1`, because the item name is a cross-repo contract the client parses and writing a
    name into the yaml must not move it. What you write is resolved to the model at generation and
    goes no further -- which is the whole reason this cost no client release.
    """
    display_name = "Spawn Traps"
    # Strings, because a yaml list of bare ints is easy to write and an OptionSet keys on str.
    # The union of the three spellings a player can write: the model ids, the display names, and
    # the curated `traps` keys (so `basilisk` means the same thing in either option).
    #
    # 🛑 THIS IS STILL THE MENU, NOT STILL THE VALIDATION. `verify` below resolves case-insensitively
    # and reports near misses, so `_valid_keys` alone would reject `basilisk` typed as `Basilisk`.
    # What this list is for is (a) the wizard's accepted-value list and the metadata dump, and
    # (b) the corpus `verify` suggests out of. Every member of it resolves; see `_resolve_spawn`.
    valid_keys = (frozenset(str(c) for c in SPAWN_TRAPS)
                  | frozenset(yaml_name(n) for n in ENEMY_NAMES.values())
                  | frozenset(SPAWN_TRAP_KEYS))
    default = frozenset()
    #: WIZARD PRESENTATION: a text field, not 425 checkboxes.
    #:
    #: The wizard draws an OptionSet as one checkbox per `valid_keys` member, which is the right
    #: control when the keys are a MENU -- `traps` has four, `progression_surface` has a labelled
    #: grid. These keys are a CATALOGUE: 390 model ids in numeric order, only 35 of which have a
    #: name on them, none of which means anything to a player until they have looked it up
    #: somewhere else. There is nothing to scan and nothing to compare, so the grid costs 425 rows
    #: of scrolling to express the one thing anyone does with this option, which is write the two
    #: or three enemies they want.
    #:
    #: 🛑 THIS IS PRESENTATION ONLY -- the wizard refuses an unrecognised token in the box rather
    #: than writing it into the yaml for Archipelago to reject after the download. An option that
    #: renders as free text does not become free-form.
    wizard_free_text = True

    def verify(self, world, player_name: str, plando_options) -> None:
        """Every value must RESOLVE to a spawnable model -- by id, by name, or by curated key.

        🛑 WHY NOT `verify_keys` (the inherited one). It is an exact, case-sensitive set membership
        test, and this option now accepts three spellings of the same thing plus any casing of two
        of them. `Basilisk` and `basilisk` are the same enemy and both have to work, which a
        frozenset cannot express. What is NOT relaxed is the refusal: an unresolvable token is still
        a generation-time error, because the alternative is a filler item that arrives in-game and
        does nothing forever -- the exact failure this option was built to refuse.

        ⭐ AND THE ERROR NAMES NEAR MISSES. SwiftyTaco's report (2026-08-26) was a player who could
        not tell which of two options wanted words; `Allowed keys: frozenset({...425 items})` is not
        an answer to that. A misspelling gets the three closest accepted values back.
        """
        bad = [v for v in self.value if _resolve_spawn(v) is None]
        if bad:
            raise OptionError("Player %s has invalid %s values: %s"
                              % (player_name, self.display_name, "; ".join(_near(v) for v in bad)))


class TrapCount(Range):
    """How many trap items to put in your pool, shared out evenly between the traps you enabled.

    INERT unless `traps` names at least one trap. Each trap displaces one filler item, so raising
    this does not change how many checks your seed has -- only how much of your junk bites back.
    """
    display_name = "Trap Count"
    range_start = 0
    range_end = 40
    default = 8


def _spawn_names():
    """Every name `spawn_item_name` can produce. Used to ask "is any MINTED item a spawn trap?"
    without re-deriving which option put it there."""
    return {spawn_item_name(c) for c in SPAWN_TRAPS}


def _chosen(world, option: str) -> set:
    opt = getattr(world.options, option, None)
    return set(opt.value or ()) if opt is not None else set()


def _build_name_index():
    """folded spelling -> chr model id. Built once, deterministically, at import.

    🛑 LOWEST MODEL ID WINS a name two models share -- Latenna (c3170/c6210), Smithing Master Hewg
    (c3451/c6291) and Rennala (c2030/c2031) are one NPC with two bodies each. Written as an explicit
    walk of `sorted(ENEMY_NAMES)` with `setdefault`, because dict order is insertion order and
    "whichever the generator emitted first" is not a rule anybody can predict from the yaml.
    `enemy_names.ENEMY_NAME_COLLISIONS` records the same six rows in the table itself.

    The curated `traps` keys (`basilisk`, `malenia`, `aging_untouchable`) are indexed too, so a
    player who found a name in the `traps` docs can write it here and get the enemy they asked for
    instead of an unknown-key error.
    """
    idx = {}
    for chr_id in sorted(ENEMY_NAMES):
        name = ENEMY_NAMES[chr_id]
        idx.setdefault(_fold(name), chr_id)
        idx.setdefault(_fold(yaml_name(name)), chr_id)
    for key in sorted(SPAWN_TRAP_KEYS):
        idx.setdefault(_fold(key), SPAWN_TRAP_KEYS[key])
    return idx


#: folded spelling -> chr model id. Names AND curated keys; ids are handled arithmetically below.
SPAWN_NAME_INDEX = _build_name_index()


def _resolve_spawn(token: str) -> Optional[int]:
    """One yaml value -> the chr model it names, or None if nothing in the catalogue answers to it.

    Ids first and by VALUE, not by string: `4150`, `"4150"` and `" 4150 "` are the same model, and a
    yaml that quotes its numbers (or does not) must not change the seed.
    """
    tok = str(token).strip()
    if tok.isdigit():
        return int(tok) if int(tok) in SPAWN_TRAPS else None
    return SPAWN_NAME_INDEX.get(_fold(tok))


def _near(token: str) -> str:
    """`'basilsk' -- did you mean Basilisk?`. The message a player actually reads when they typo.

    Suggestions come out of the NAMES only, never the 390 ids: `difflib` cheerfully answers "4150"
    with "4151", which is a different creature and a confident wrong answer. A bad id gets told it
    is not a spawnable model, which is the true statement about it.
    """
    tok = str(token).strip()
    if tok.isdigit():
        return ("%s is not a spawnable character model id -- 26 of the 416 models have no AI row "
                "or no body and cannot be spawned" % tok)
    near = difflib.get_close_matches(_fold(tok), list(SPAWN_NAME_INDEX), n=3, cutoff=0.6)
    names = [yaml_name(ENEMY_NAMES.get(SPAWN_NAME_INDEX[k], k)) for k in near]
    if names:
        return "%r -- did you mean %s?" % (tok, ", ".join(sorted(set(names))))
    return ("%r is not an enemy name this option knows and is not a model id; only 35 of the 390 "
            "spawnable models have a name, the rest are written as their id" % tok)


def spawn_trap_models(world) -> Set[int]:
    """The `spawn_traps` option resolved to MODEL IDS.

    🛑 THIS IS THE WHOLE CONTRACT ARGUMENT IN ONE FUNCTION. Names are a yaml-side convenience that
    dies here: everything downstream -- `spawn_item_name`, the minted item, `slot_data`, the client's
    parser -- sees the id it always saw, so accepting names moved `CONTRACT_HASH` by nothing and
    needs no client release. Translating at generation is what buys that; carrying the name any
    further would not.
    """
    out = set()
    for tok in _chosen(world, "spawn_traps"):
        chr_id = _resolve_spawn(tok)
        if chr_id is not None:
            out.add(chr_id)
    return out


def enabled_traps(world) -> List[str]:
    """The `traps` option values this seed enabled, in catalogue order -- deterministic.

    🛑 Sorted by the catalogue rather than by the OptionSet, because an OptionSet is a `frozenset`
    and iterating one is not stable across runs. A seed must be reproducible from its yaml.
    """
    chosen = _chosen(world, "traps")
    return [k for k in TRAPS if k in chosen] + [k for k in sorted(SPAWN_TRAP_KEYS) if k in chosen]


def enabled_trap_names(world) -> List[str]:
    """Every distinct trap item NAME this seed may mint, in a deterministic order.

    Three sources feed one list: the fixed traps, the curated spawn keys, and raw model ids from
    `spawn_traps`. All three are walked in CATALOGUE order (never OptionSet order) so the result is
    a function of the yaml and not of frozenset iteration.

    🛑 DEDUPLICATED, order-preserving. `traps: [basilisk]` and `spawn_traps: ["4150"]` name the same
    creature and mint the same string; without this the round-robin would deal that one trap twice
    as often as the others, which is a silent weighting bug rather than a visible one.
    """
    names = []
    chosen = _chosen(world, "traps")
    for k in TRAPS:
        if k in chosen:
            names.append(TRAPS[k])
    for k in sorted(SPAWN_TRAP_KEYS):
        if k in chosen:
            names.append(spawn_item_name(SPAWN_TRAP_KEYS[k]))
    raw = spawn_trap_models(world)
    for c in sorted(SPAWN_TRAPS):
        if c in raw:
            names.append(spawn_item_name(c))
    return list(dict.fromkeys(names))


def trap_items(world) -> List[str]:
    """The trap item NAMES this seed mints, dealt round-robin across everything enabled.

    Round-robin rather than random so the split is even and reproducible: with 8 traps and 2 kinds
    you get 4 and 4, every time, and a player who enabled two traps never rolls a seed with seven of
    one and one of the other.
    """
    chosen = enabled_trap_names(world)
    if not chosen:
        return []
    opt = getattr(world.options, "trap_count", None)
    n = int(opt.value) if opt is not None else 0
    if n <= 0:
        return []
    return [chosen[i % len(chosen)] for i in range(n)]


@register
class TrapsFeature(Feature):
    name = "traps"
    OPTIONS = {"traps": Traps, "trap_count": TrapCount, "spawn_traps": SpawnTraps}
    # FILLER, always. Rule 3: no progression may ride a trap, and `_class_for` never promotes these
    # because they are not required runes, gate runes, legacy keys or natural keys.
    #
    # 🛑 THE 390 SPAWN NAMES ARE DELIBERATELY ABSENT. `registry.allocate_item_ids` walks features in
    # import order handing out SEQUENTIAL ids, so declaring 390 names here would shift the AP id of
    # every feature-minted item registered after this one -- the exact renumbering `core.py` goes out
    # of its way to avoid for ASHEN_LOCK ("appending here leaves every existing id exactly where they
    # were"). They are registered in `core.py` instead, in their own block, at an id ARITHMETIC in
    # the chr model, so adding or removing a family renumbers nothing at all.
    ITEMS = {n: ItemClassification.filler for n in TRAPS.values()}
    # 🛑 NO `ITEM_GRANTS`. That absence is what makes a trap synthetic -- it never lands in
    # `_AP_IDS_TO_ITEM_IDS`, so the client is never told to hand the player an ER item for it, and
    # the "no ER mapping ... contract drift?" warn is answered by the client's name branch instead.

    def create_items(self, world):
        # Count-neutral by construction: core.create_items sizes filler off len(pool), so each trap
        # returned here displaces exactly one filler. OFF (empty OptionSet) -> [] -> a pool
        # byte-identical to one built before this feature existed.
        return [world.create_item(nm) for nm in trap_items(world)]

    def slot_data(self, world):
        """Declare each trap capability, and ONLY when this seed actually mints one.

        Keyed on the ITEMS THAT WILL EXIST, not on the options being non-empty: `trap_count: 0` with
        a trap named mints nothing, and a seed that mints nothing needs nothing from the client. A
        tag declared by a seed that cannot use it would refuse older clients for no reason, which is
        how a safety check turns into an upgrade tax.

        The three older fixed names need no tag: every released trap client knows them. Blackout is
        fixed too, but new, so it declares its own capability rather than being silently consumed
        by an older client.
        """
        minted = set(trap_items(world))
        tags = []
        if minted & set(_spawn_names()):
            tags.append(CLIENT_FEATURE_TAG)
        if TRAPS["blackout"] in minted:
            tags.append(BLACKOUT_CLIENT_FEATURE_TAG)
        return {contract.REQUIRES_CLIENT_FEATURES: tags} if tags else {}
