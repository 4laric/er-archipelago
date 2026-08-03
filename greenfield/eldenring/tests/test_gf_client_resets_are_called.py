"""Every client module that WRITES GAME STATE must be re-armed on the in-world edge.

THE CLASS, four instances in eleven days:
  * shop_sell    -- 2026-07-24, found by a Kale repro in playtest
  * shop_icon    -- 2026-07-29, found by a review noticing the asymmetry
  * shop_stock   -- 2026-07-29, found only after a player reported the SAME symptom three times
  * shop_preview -- 2026-08-03, found by reading a log (153 placeholder swaps across 51 edges vs
                   3 preview swaps across one), NOT by this file -- see WHY THE GATE MISSED #4.

A map load streams ShopLineupParam / ItemLotParam / EquipParamGoods / the FMG blocks back in and
reverts our writes. Each writer latches a `DONE` flag after one clean pass, so unless it is re-armed
on the `in_world` false->true edge, the write applies once on connect and is gone for the rest of the
session. `DONE` stays set, so nothing retries and nothing logs.

WHY THE GATE MISSED #4 (CONTRIBUTING rule 11 -- the motivating case is the acceptance test). Until
2026-08-03 this file built its module set with:

    if re.search(r"pub fn reset\\s*\\(", body):
        cls.modules[fn[:-3]] = body

-- it enumerated modules that DEFINE reset(). A module that defines none was never scanned, so it
could never fail. `shop_preview` writes three FMG categories through `swap_category` and had no
reset() at all: it was invisible to the one gate written to catch exactly it. Worse, the
`_EDGE_EXEMPT` comment dated 2026-07-31 NOTICED that shop_preview and fmg_inject had stopped
defining reset() and responded by DELETING their exemptions -- the observation that should have
raised the alarm silenced it instead. A gate keyed on the SAFEGUARD can only ever find modules that
already tried; it is blind to the ones that never did.

So the scan is now keyed on the HAZARD. It enumerates modules that write game state -- a
`SoloParamRepository::instance_mut()` borrow, or an FMG `swap_category` / `extend_swap_overrides` --
and demands a re-arm from each. MEASURED against client 19e586b (2026-08-03): 18 writers, of which
the 9 known-good ones (check_lots, whetblade_lots, enemy_drops, shop_sell, shop_repoint, shop_prices,
shop_stock, shop_icon, shop_preview) are all accepted, and no read-only module is picked up --
`minibaker` and `params.rs` use `SoloParamRepository::instance()` and are correctly ignored, as are
the `GameDataMan` / `WorldChrMan` / `FieldArea` mutators (deathlink, flask, fogwall, fast_travel,
upgrades, auto_equip), which touch live objects a load rebuilds rather than a param file it re-streams.

THE CALL MUST BE IN THE EDGE BLOCK, not merely somewhere in core.rs. The old gate substring-matched
`crate::<mod>::reset()` against the whole 3800-line file, so a CONNECT-scoped reset counted as an
edge reset -- which is the shop_stock bug with the latch moved one scope out. `scadu_blessing` is
live proof: its `reset()` is called from the slot_data parse (core.rs:705), never from the edge, and
the old gate passed it green.

WHY IT COST SO MUCH. The generator was provably correct -- his seed's slot_data carried a Golden Rune
[5] priced at 4 runes -- so every measurement upstream of the game agreed the feature worked, and I
told him so three times. A correct wire is not a correct feature.

A `reset()` WITH NO CALLER IS THE SAME BUG AS A PREDICATE WITH NO CALLER, and a WRITER WITH NO
`reset()` IS THE SAME BUG WITH THE EVIDENCE REMOVED.

THE LEDGER IS DISCHARGED (2026-08-04, client PR "Re-arm every latched game-state writer on the
in_world edge"). Alaric ruled "resets for everything should be handled in the same way", so the seven
modules that were merely UNRULED got the same edge re-arm as their siblings and their rows are gone.
RE-MEASURED against that branch: still 18 writers, now 16 accepted (the 9 above plus shop_flags,
upgrade_cost, notif_ticker, no_weapon_reqs, no_equip_load, no_fall_damage, scadu_blessing) and 2 in
_EDGE_EXEMPT (shop_value the pure helper, fmg_inject the measured-inert one). `_UNRULED_WRITERS` is
now EMPTY and stays a live list: the ratchet still refuses a fixed row, and the next writer that
lands without an edge re-arm turns this file RED on the day it lands rather than joining a backlog.

The eighth, fmg_inject, is the one entry that did NOT become a reset. It is RULED, not deleted:
`test_fmg_inject_is_still_inert` re-derives the three facts its exemption rests on every run, so the
prose below is checked rather than believed. That distinction is the whole point -- on 2026-07-31 an
exemption for shop_preview was DELETED because someone noticed it had gone stale, and the deletion
silenced the alarm instead of raising it.
"""
import os
import re
import unittest

try:
    from ._util import find_repo_root, REPO_ONLY_REASON
except ImportError:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _util import find_repo_root, REPO_ONLY_REASON

_ROOT = find_repo_root(os.path.dirname(os.path.abspath(__file__)))
_SRC = os.path.join(_ROOT or "", "from-software-archipelago-clients",
                    "crates", "eldenring-archipelago", "src")

# The in_world false->true edge in core.rs, by its two anchors. Both are asserted in setUpClass: if
# either moves the scan must DIE, not quietly widen to the whole file (which is how a connect-scoped
# reset used to read as an edge reset).
_EDGE_OPEN = "if now_in_world && !self.was_in_world {"
_EDGE_CLOSE = "self.was_in_world = now_in_world;"

# ---------------------------------------------------------------------------------------------
# WHAT COUNTS AS WRITING GAME STATE.
#
# Each signal is (label, regex, why-this-one). `test_every_write_signal_matches_something` fails if
# any of them stops matching any module, because a signal that matches nothing is decoration that
# reads as coverage -- the same failure mode as the exemption list naming a module that is gone.
#
# NOT included, deliberately, and each was measured before it was dropped:
#   * `SoloParamRepository::instance()` (immutable) -- params.rs and minibaker.rs read rows and write
#     nothing. Including it would flag two modules that a load cannot break.
#   * `GameDataMan::instance_mut()` / `WorldChrMan::instance_mut()` / `FieldArea::instance_mut()` /
#     `CSWorldGeomMan::instance_mut()` -- deathlink, flask, upgrades, auto_equip, fast_travel,
#     fogwall. These mutate LIVE game objects, which a load tears down and rebuilds; there is no
#     param file to re-stream over them, and the modules re-derive from observed state each tick.
#   * a DONE-latch probe (`static X: AtomicBool` + `.store(true, ...)`). It would have discriminated
#     nothing today -- every one of the 18 writers latches -- and requiring it would trade a false
#     positive (loud, fixable) for a false NEGATIVE (silent, four bugs deep). Fail closed instead: a
#     writer that genuinely re-applies every tick is cheap to exempt WITH A REASON.
# ---------------------------------------------------------------------------------------------
_WRITE_SIGNALS = [
    ("SoloParamRepository::instance_mut()",
     re.compile(r"SoloParamRepository::instance_mut\s*\("),
     "the mutable param-repo borrow -- every ShopLineupParam / ItemLotParam / EquipParam* / "
     "SpEffectParam write in this crate goes through it, typed setter or raw offset alike"),
    ("FMG swap_category / extend_swap_overrides",
     re.compile(r"\b(?:swap_category|extend_swap_overrides)\s*\("),
     "the FMG half. shop_preview (the 2026-08-03 miss) writes ONLY through these -- it never "
     "touches the param repo, so a param-only heuristic reproduces the exact hole"),
    ("&mut SoloParamRepository in a signature",
     re.compile(r":\s*&mut\s+SoloParamRepository\b"),
     "a HELPER that writes through a borrow its caller owns (shop_value). It has no pass and no "
     "latch of its own, so it is exempt -- but it must be SEEN, or the next such helper hides a "
     "write behind a module name nothing scans"),
]

# Modules whose re-arm is deliberately NOT on the in-world edge, and which a map load provably
# cannot break. Each needs a REASON, and the reason must be checkable by someone reading the module.
#
# The bar for landing here is NOT "the gate is inconvenient" -- it is "a map load cannot break this
# module". The class this file screens for is specifically: WE WRITE GAME STATE, a load streams the
# param file (or the FMG block) back in and reverts the write, and a DONE latch stops us re-applying.
#
# (`lock_hints` lived here until 2026-08-03 with the reason "not a param writer at all". That is now
# DERIVED rather than asserted -- it matches no write signal, so the scan never considers it, and an
# entry naming it would be permanently stale. Its method-shaped `self.lock_hints.reset()` is still
# pinned, as a probe of the DIAGNOSTIC, by test_the_method_shape_is_still_detected.)
_EDGE_EXEMPT = {
    "fmg_inject": (
        "MEASURED INERT, 2026-08-04, and this is a RULING on the old _UNRULED_WRITERS row rather "
        "than a deletion of it -- `test_fmg_inject_is_still_inert` re-derives every clause below on "
        "each run, so it cannot rot into prose the way the 2026-07-31 shop_preview exemption did. "
        "CLAIMED: fmg_inject's MODE_INJECT path names SYNTHETIC goods rows (category-stripped id > "
        "er_codec::SYNTHETIC_GOODS_MIN_ID = 3,780,000, carrying the AP location id in the two "
        "`vagrant*` fields), `params::synthetic_goods_ids()` only ever SCANS for them, and NOTHING "
        "in the client creates one: `.set_vagrant_*(` is called nowhere, the baker that used to "
        "bake such rows retired 2026-07-01, and the client README calls itself pure-runtime. "
        "Vanilla supplies none either -- gen_inputs.db's `vanilla_er/EquipParamGoods.csv` (2326 "
        "rows) tops out at the real id 2,220,010, exactly the bound SYNTHETIC_GOODS_MIN_ID's own "
        "comment claims, plus the sentinel row 999999999, which `is_synthetic_goods` rejects "
        "because `CATEGORY_GOODS | 999999999` = 0x7B9AC9FF carries a 0x7 category nibble, not 0x4. "
        "So `injects` is always empty and the block this module swaps in is an IDENTITY rebuild, "
        "validated against the game's own lookup on CHECK_IDS before the swap. A load reverting an "
        "identity swap costs nothing, and every FMG write the player can SEE is published by "
        "check_lots::dress_placeholder and shop_preview through extend_swap_overrides -- both of "
        "which ARE re-armed on the edge. Re-arming this module would leak one VirtualAlloc'd "
        "GoodsName block (4302 entries) per map load for no behavioural change. "
        "WHAT WOULD INVALIDATE IT: anything that starts creating synthetic goods rows. The client "
        "now logs `FMG-inject: INERT -- 0 synthetic goods ids` at WARN on every session that finds "
        "none, so the DISAPPEARANCE of that line is the signal -- at which point the swap stops "
        "being an identity swap and this module needs a reset() and an edge call like the rest."
    ),
    "shop_value": (
        "pure helper: every write is through a `&mut SoloParamRepository` its CALLER borrowed "
        "(shop_sell / shop_repoint), and it holds no static latch of any kind -- grep it for "
        "`static` and there is none. It runs exactly when its caller runs, so its re-arm IS its "
        "caller's re-arm, and both callers are on the edge."
    ),
}

# ---------------------------------------------------------------------------------------------
# THE DEBT LEDGER. Frozen at EIGHT on 2026-08-03 when the scan was re-keyed from reset()-definers to
# writers; DISCHARGED to zero on 2026-08-04. Seven of the eight (shop_flags, upgrade_cost,
# notif_ticker, no_weapon_reqs, no_equip_load, no_fall_damage, scadu_blessing) were given the same
# edge re-arm as their siblings, per Alaric's ruling that "resets for everything should be handled in
# the same way"; the eighth (fmg_inject) was measured INERT and moved to _EDGE_EXEMPT, where
# test_fmg_inject_is_still_inert checks its reason instead of trusting it.
#
# KEEP THIS DICT. An empty ledger is not a dead one: a row here is how a NEW writer whose ruling is
# genuinely unknown gets enumerated rather than either turning the gate red on landing (which teaches
# people to switch it off) or hiding in _EDGE_EXEMPT next to modules that were actually measured.
# Anything that lands here must say what is CLAIMED and what is UNKNOWN, separately.
#
# THIS LIST IS A RATCHET. `test_the_debt_ledger_only_shrinks` FAILS when an entry gains an edge
# re-arm and is not deleted, so it cannot silently become an exemption list. Adding a row is a
# reviewable line in a diff with a reason attached; it is not a quiet green.
#
# Each reason states what is CLAIMED and what is UNKNOWN, separately. Alaric rules; the gate does not.
# ---------------------------------------------------------------------------------------------
_UNRULED_WRITERS = {}  # module -> reason. EMPTY since 2026-08-04; see the note above.


@unittest.skipUnless(_ROOT is not None, REPO_ONLY_REASON)
class ClientResetsAreCalled(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(_SRC):
            raise unittest.SkipTest("client not checked out beside the repo")
        with open(os.path.join(_SRC, "core.rs"), encoding="utf-8") as fh:
            cls.core = fh.read()

        # THE EDGE BLOCK, by both anchors, each required to appear EXACTLY once. A missing or
        # duplicated anchor is a scan failure and must read as one -- silently falling back to the
        # whole file is the bug this scoping exists to remove.
        for anchor in (_EDGE_OPEN, _EDGE_CLOSE):
            n = cls.core.count(anchor)
            if n != 1:
                raise AssertionError(
                    "core.rs contains the in-world-edge anchor %r %d times, expected exactly 1. "
                    "The edge block moved or was renamed; re-point _EDGE_OPEN/_EDGE_CLOSE. Do NOT "
                    "widen this back to a whole-file search -- that is what let a connect-scoped "
                    "scadu_blessing::reset() read as an edge reset." % (anchor, n))
        o = cls.core.index(_EDGE_OPEN)
        c = cls.core.index(_EDGE_CLOSE, o)
        cls.edge = cls.core[o:c]

        # WRITERS, keyed on the hazard. `contract_gen.rs` is generated and `core.rs` is the caller.
        cls.writers = {}   # module -> [signal label, ...]
        cls.bodies = {}
        for fn in sorted(os.listdir(_SRC)):
            if not fn.endswith(".rs") or fn in ("core.rs", "contract_gen.rs"):
                continue
            with open(os.path.join(_SRC, fn), encoding="utf-8") as fh:
                body = fh.read()
            cls.bodies[fn[:-3]] = body
            hits = [label for label, rx, _why in _WRITE_SIGNALS if rx.search(body)]
            if hits:
                cls.writers[fn[:-3]] = hits

    # -- the gate ------------------------------------------------------------------------------

    def test_every_writer_is_rearmed_on_the_in_world_edge(self):
        """A writer with no edge re-arm applies once on connect and is silently gone after the
        first load. FOUR shipped that way; the fourth had no reset() for the old gate to find."""
        self.assertTrue(self.writers, "found no client module writing game state -- the scan broke")
        missing = sorted(m for m in self.writers
                         if m not in _EDGE_EXEMPT
                         and m not in _UNRULED_WRITERS
                         and ("crate::%s::reset()" % m) not in self.edge)
        if not missing:
            return

        # SAY WHICH KIND OF MISSING. This gate matches exactly one call shape --
        # `crate::<mod>::reset()`, the free function, INSIDE the edge block -- and its failure text
        # used to read "core.rs never calls it" for every miss. For `lock_hints` (2026-07-31) that
        # sentence was simply FALSE: core.rs calls `self.lock_hints.reset()`, because LockHints is a
        # struct held as a field, not a free function. The gate was right to fail and wrong about
        # why, which sent the reader looking for a missing call that was sitting there. A guard is a
        # derivation too, and it will lie to you just as happily. So: name the shape that IS there.
        #
        # We deliberately do NOT accept `self.<field>.reset()`, nor a `crate::<mod>::reset()` that
        # sits outside the edge block. Accepting either would let a CONNECT-scoped reset pass green,
        # which is the shop_stock bug exactly. Fail closed, and name the shape so the fix is obvious.
        no_reset, off_edge, method_shaped, uncalled, other_edge_call = [], [], [], [], []
        for m in missing:
            if not re.search(r"pub fn reset\s*\(", self.bodies[m]):
                no_reset.append(m)
            elif ("crate::%s::reset()" % m) in self.core:
                off_edge.append(m)
            elif re.search(r"\.%s\.reset\(\)" % re.escape(m), self.core):
                method_shaped.append(m)
            else:
                # DEFINES reset(), and NOTHING in core.rs calls it in any shape. This bucket exists
                # because it used to fall through into `no_reset` and print "NO reset() AT ALL",
                # which is false and sends the reader to write a function that is already there.
                # That is the same lying-diagnostic failure lock_hints exposed on 2026-07-31, one
                # branch over. Found by running mutation M2 (delete the edge call, keep the fn).
                uncalled.append(m)
            named = sorted(set(re.findall(r"crate::%s::([a-z_0-9]+)\(" % m, self.edge)))
            if named and named != ["reset"]:
                other_edge_call.append("%s -> %s" % (m, named))

        detail = []
        if no_reset:
            detail.append(
                "  NO reset() AT ALL, and it writes game state: %s\n"
                "    -> this is the shop_preview shape (2026-08-03). Add `pub fn reset()` clearing "
                "the DONE latch, and call `crate::<mod>::reset()` from the in_world edge block in "
                "core.rs." % no_reset)
        if uncalled:
            detail.append(
                "  DEFINES reset() and NOTHING calls it, in any shape: %s\n"
                "    -> dead code wearing the shape of a safeguard; this is shop_stock 2026-07-29 "
                "exactly. Call `crate::<mod>::reset()` from the in_world edge block." % uncalled)
        if off_edge:
            detail.append(
                "  reset() EXISTS and core.rs calls it, but OUTSIDE the in_world edge block: %s\n"
                "    -> a connect-scoped or seed-scoped reset does not survive a map load. Call it "
                "from the edge block too (scadu_blessing is the exemplar)." % off_edge)
        if method_shaped:
            detail.append(
                "  called as a METHOD (`self.<field>.reset()`), which this gate does not accept as "
                "an edge re-arm: %s\n"
                "    -> that call may be seed-scoped or connect-scoped. If a map load cannot break "
                "the module, add it to _EDGE_EXEMPT with the reason; if it writes game state, "
                "re-arm it on the in_world edge too." % method_shaped)
        if other_edge_call:
            detail.append(
                "  NOTE: the edge block already calls something else on this module: %s\n"
                "    -> if that call IS the re-arm, rename it `reset()` (this gate matches one "
                "shape on purpose) or exempt with the reason." % other_edge_call)

        self.assertFalse(
            missing,
            "%d client module(s) write game state with no `crate::<mod>::reset()` inside core.rs's "
            "in_world edge block: %s.\n%s\n"
            "A map load reverts param and FMG writes and each writer latches DONE after one pass, "
            "so a re-arm that never runs on the in_world edge means the write applies once on "
            "connect and silently never again -- the shop_sell (07-24), shop_icon and shop_stock "
            "(07-29) and shop_preview (08-03) bug, four times over.\n"
            "If a map load genuinely cannot break the module, add it to _EDGE_EXEMPT WITH A REASON "
            "a reader can check. If you do not know, add it to _UNRULED_WRITERS with what is "
            "claimed and what is unknown -- and say so in the PR."
            % (len(missing), missing, "\n".join(detail)))

    def test_every_accepted_writer_actually_defines_reset(self):
        """The other half of the same coin: an edge CALL to a reset() that does not exist.

        The gate above matches the CALL SITE, because that is where three of the four bugs lived.
        But a rename or a delete on the client side would leave the call site untouched and this
        file green -- the mirror image of the hole that shipped shop_preview. Rust would not link,
        so this is not a shipping risk; it IS a scan-integrity risk, and it is what makes the rule-7
        mutation ("delete `pub fn reset()` from shop_stock.rs") produce a RED here rather than a
        silent pass. Cheap to check, so check it.
        """
        accepted = sorted(m for m in self.writers
                          if ("crate::%s::reset()" % m) in self.edge)
        self.assertTrue(accepted, "no writer is re-armed on the edge at all -- the scan broke")
        undefined = sorted(m for m in accepted
                           if not re.search(r"pub fn reset\s*\(", self.bodies[m]))
        self.assertFalse(
            undefined,
            "core.rs's in_world edge block calls `crate::<mod>::reset()` for %s, but the module "
            "defines no `pub fn reset(`. Either the re-arm was renamed (re-point the call) or it "
            "was deleted (that module is now the shop_preview shape -- give it a reset() back)."
            % undefined)

    # -- the lists stay honest -----------------------------------------------------------------

    def test_the_exemptions_still_exist(self):
        """An exemption for a module that is gone hides the next real omission behind stale prose."""
        stale = sorted(m for m in _EDGE_EXEMPT if m not in self.writers)
        if stale:
            import warnings
            warnings.warn("_EDGE_EXEMPT names %s, which the write scan no longer classifies as "
                          "writers -- prune them so the list keeps meaning something." % stale)

    def test_every_exemption_and_ledger_row_carries_a_reason(self):
        """A bare module name is an assertion with no evidence. Both lists are {module: reason}."""
        for name, table in (("_EDGE_EXEMPT", _EDGE_EXEMPT), ("_UNRULED_WRITERS", _UNRULED_WRITERS)):
            for mod, reason in table.items():
                self.assertIsInstance(reason, str, "%s[%r] must be a reason string" % (name, mod))
                self.assertGreaterEqual(
                    len(reason.split()), 12,
                    "%s[%r] reason is %d words -- too short to be checkable. Say what is CLAIMED "
                    "and, if you do not know, what is UNKNOWN." % (name, mod, len(reason.split())))
        overlap = sorted(set(_EDGE_EXEMPT) & set(_UNRULED_WRITERS))
        self.assertFalse(overlap, "%s are both exempt and unruled -- pick one" % overlap)

    def test_the_debt_ledger_only_shrinks(self):
        """THE RATCHET. _UNRULED_WRITERS is a backlog, not a second exemption list.

        It was frozen at 8 entries on 2026-08-03, the day the scan was re-keyed from
        reset()-definers to writers, and emptied on 2026-08-04 when Alaric ruled that every latched
        writer gets the same edge re-arm. A row that has been FIXED must be deleted, or the list stops
        describing the debt and starts hiding it -- which is precisely what happened to the old
        _EDGE_EXEMPT on 2026-07-31, when noticing that shop_preview had lost its reset() led to
        deleting the entry instead of raising the alarm.
        """
        resolved = sorted(m for m in _UNRULED_WRITERS
                          if ("crate::%s::reset()" % m) in self.edge)
        self.assertFalse(
            resolved,
            "%s now re-arm on the in_world edge -- DELETE their _UNRULED_WRITERS rows. A ledger "
            "that keeps fixed rows is a list nobody trusts, and the next real omission hides in "
            "it." % resolved)
        gone = sorted(m for m in _UNRULED_WRITERS if m not in self.writers)
        self.assertFalse(
            gone,
            "%s no longer match any write signal (module deleted, or rewritten to stop writing) -- "
            "delete their _UNRULED_WRITERS rows." % gone)
        # Not a failure: the point of the ledger is that someone READS it. Guarded, because an
        # unconditional "0 client writer(s) still have NO ruling: []" is noise that trains the
        # reader to skip the one line that will matter on the day the list is non-empty again.
        if _UNRULED_WRITERS:
            import warnings
            warnings.warn(
                "%d client writer(s) still have NO in-world-edge re-arm and NO ruling: %s. Each is "
                "a candidate for the shop_sell/shop_icon/shop_stock/shop_preview bug. See the "
                "reasons in _UNRULED_WRITERS."
                % (len(_UNRULED_WRITERS), sorted(_UNRULED_WRITERS)))

    # -- the scan itself is pinned -------------------------------------------------------------

    def test_the_scan_is_not_vacuous(self):
        """If a regex or the layout changes this must fail loudly, not pass with zero findings."""
        self.assertGreaterEqual(
            len(self.writers), 12,
            "only %d game-state writer(s) found; measured 18 against client 19e586b (2026-08-03). "
            "The scan is matching almost nothing and a green run here would mean nothing."
            % len(self.writers))
        # assertIn/assertRegex NOT used against self.edge: their failure message embeds the whole
        # ~4 KB block, which buries the one sentence that matters. Same reason as the note in
        # test_the_method_shape_is_still_detected. Found by running mutations M2 and M3.
        self.assertTrue(
            "crate::shop_stock::reset()" in self.edge,
            "shop_stock::reset() is the regression this file was written for, and it is NOT called "
            "from core.rs's in_world edge block (%r .. %r). Somewhere-in-core.rs is not enough: a "
            "connect-scoped reset does not survive a map load." % (_EDGE_OPEN, _EDGE_CLOSE))

    def test_every_write_signal_matches_something(self):
        """A signal that matches nothing is decoration that reads as coverage.

        The FMG signal is the one that matters here: drop it and shop_preview -- which never touches
        the param repo -- becomes invisible again, which is the whole 2026-08-03 miss.
        """
        for label, rx, why in _WRITE_SIGNALS:
            hits = sorted(m for m, body in self.bodies.items() if rx.search(body))
            self.assertTrue(
                hits,
                "write signal %r matched NO client module. It is either obsolete (delete it and "
                "say why in this docstring) or the crate renamed the primitive (re-point it). "
                "Reason it exists: %s" % (label, why))

    def test_shop_preview_is_the_motivating_case(self):
        """CONTRIBUTING rule 11: the case that motivated the change IS the acceptance test.

        shop_preview is the module the old gate could not see -- it writes three FMG categories and
        defined no reset(), so `if re.search(r"pub fn reset\\(", body)` skipped it entirely. Pin all
        three facts the fix depends on: it is classified a WRITER, it is classified by the FMG
        signal specifically (a param-only heuristic reproduces the hole), and it is re-armed.
        """
        self.assertIn("shop_preview", self.writers,
                      "shop_preview is no longer classified as a game-state writer -- the scan has "
                      "regressed to the hole that shipped the 2026-08-03 bug")
        self.assertIn("FMG swap_category / extend_swap_overrides", self.writers["shop_preview"],
                      "shop_preview must be caught by the FMG signal: it makes no param-repo write "
                      "at all, so a param-only scan misses it exactly as the old one did")
        self.assertTrue(
            "crate::shop_preview::reset()" in self.edge,
            "shop_preview::reset() is not called from core.rs's in_world edge block. That is the "
            "FOURTH instance of this bug (client PR #29); if it has been reverted, revert the "
            "revert. (assertTrue, not assertIn: assertIn would dump the whole ~4 KB edge block.)")

    def test_fmg_inject_is_still_inert(self):
        """THE EXEMPTION'S EVIDENCE, re-derived every run instead of believed.

        fmg_inject is the one former _UNRULED_WRITERS row that did NOT become a reset. The ruling is
        that its MODE_INJECT path can never inject, so the block it swaps in is an IDENTITY rebuild
        and a map load reverting it costs nothing. That is a claim about the CLIENT, and a claim
        about the client parked in a comment is exactly what went stale on 2026-07-31 -- so pin the
        three facts it rests on. If any of them changes, this fails and the exemption must be
        re-argued or replaced with a reset() + an edge call.
        """
        self.assertIn("fmg_inject", self.writers,
                      "fmg_inject no longer matches any write signal -- it has stopped writing "
                      "game state entirely, so prune its _EDGE_EXEMPT row rather than leaving a "
                      "reason for a hazard that is gone")

        # 1. NOTHING CREATES A SYNTHETIC ROW. `set_vagrant_*` are the setters that would write an AP
        #    location id into a goods row's two carrier fields, which is what makes a row synthetic.
        #    Matched as a METHOD CALL (`.set_vagrant_x(`) on purpose: the module doc and the reason
        #    above both mention the name in prose, and a bare-name match would find those and read
        #    as coverage. The getters (`row.vagrant_item_lot_id()`) are reads and are expected.
        callers = sorted(m for m, body in self.bodies.items()
                         if re.search(r"\.set_vagrant_\w+\s*\(", body))
        self.assertFalse(
            callers,
            "%s call a `set_vagrant_*` setter, so the client can now CREATE synthetic goods rows. "
            "fmg_inject's MODE_INJECT path is no longer inert and its swap is no longer an identity "
            "rebuild: give it `pub fn reset()` clearing DONE and call `crate::fmg_inject::reset()` "
            "from core.rs's in_world edge block, and move it out of _EDGE_EXEMPT." % callers)

        # 2. THE ID SOURCE IS SCAN-ONLY. `params.rs` supplies `synthetic_goods_ids()` and matches no
        #    write signal at all (it borrows `SoloParamRepository::instance()`, immutable), so it
        #    reports rows the game already has -- it never adds one.
        self.assertIn("params", self.bodies, "params.rs is gone; re-point this check")
        self.assertNotIn(
            "params", self.writers,
            "params.rs now matches a write signal. It is fmg_inject's only source of synthetic ids "
            "and was scan-only; if it writes, re-derive the inertness ruling from scratch.")

        # 3. THE CLIENT SAYS SO OUT LOUD. Tolerance requires telemetry: a permanently-zero path that
        #    reports success is the failure mode this project keeps paying for, so the module warns
        #    when it finds no synthetic ids. The DISAPPEARANCE of that line is the in-game signal
        #    that this exemption has expired, which only works if the line is actually there.
        # assertTrue, NOT assertIn: fmg_inject.rs is ~1100 lines and assertIn embeds the whole
        # haystack in the failure, burying the one sentence that matters. Same reason as the notes
        # on self.edge and self.core elsewhere in this file. Found by running the mutation.
        body = self.bodies["fmg_inject"]
        self.assertTrue(
            "FMG-inject: INERT" in body,
            "fmg_inject no longer logs its INERT condition. The exemption above tells the reader to "
            "watch for that line going missing from a session log; without it in the source, a "
            "missing line means nothing and the ruling has no in-game check behind it.")
        self.assertTrue(
            re.search(r'log::warn!\(\s*\n?\s*"FMG-inject: INERT', body),
            "the INERT line is no longer a `log::warn!` -- at info level it scrolls past in a "
            "612k-line session log, which is the same as not logging it")

    def test_the_method_shape_is_still_detected(self):
        """`lock_hints` is the module that exposed the LYING DIAGNOSTIC -- reset() defined as a
        METHOD on a struct field, called as `self.lock_hints.reset()`, reported as "never calls it".

        It is no longer in the gate's universe (it writes no game state, so the scan does not
        consider it), but the diagnostic branch that names the method shape is still live for the
        next struct-held writer. Pin the probe itself: if this call shape leaves core.rs, the
        failure text silently reverts to asserting a falsehood about whatever module lands in it.
        """
        # assertRegex, NOT used here on purpose: its failure message embeds the whole haystack, and
        # core.rs is ~220 KB -- the diagnostic would be unreadable. Found by running the mutation.
        self.assertTrue(re.search(r"\.lock_hints\.reset\(\)", self.core),
                        "the method-call shape this test exists to describe is gone from core.rs; "
                        "re-point this exemplar at whatever module now has a method-shaped reset()")
        self.assertNotIn("crate::lock_hints::reset()", self.core,
                         "lock_hints gained a free-function reset -- re-point this exemplar")


if __name__ == "__main__":
    # The `generators` CI job runs this file as a SCRIPT and pipes it through `tail -5`, so a
    # `warnings.warn` emitted mid-run is scrolled off the log and the debt ledger reads as absent.
    # A backlog nobody can see is a dormant oracle -- the exact failure mode the client-main-drift
    # job's comment argues against. Print it LAST, after unittest's summary, in two lines.
    import sys
    _prog = unittest.main(exit=False)
    if _ROOT is not None and os.path.isdir(_SRC) and _UNRULED_WRITERS:
        print("[client-resets] %d writer(s) with NO in-world-edge re-arm and NO ruling: %s"
              % (len(_UNRULED_WRITERS), ", ".join(sorted(_UNRULED_WRITERS))))
        print("[client-resets] each is a shop_sell/shop_icon/shop_stock/shop_preview candidate; "
              "reasons are in _UNRULED_WRITERS in this file.")
    sys.exit(0 if _prog.result.wasSuccessful() else 1)
