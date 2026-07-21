"""Structured degradation ledger for the coverage gate (hand-authored -- NOT generated).

Two escape hatches, both self-cleaning so a hole that becomes fixable forces the gate to say
"remove it" (the ledger can never rot into a permanent excuse):

  * QUARANTINE      -- a location EXCLUDED from the pool entirely (gen_data / a feature must actually
                       drop it). An entry is a promise that the location is NOT emitted. If a
                       quarantined location IS still emitted and now passes every coverage check,
                       coverage._quarantine_violations reports it: the reason is gone, delete the entry
                       (and stop excluding the location).

  * ACCEPTED_LEAKS  -- a location that IS emitted and detectable but is KNOWINGLY unsuppressable
                       (its vanilla ware leaks / double-dips). Legal ONLY when the location is
                       FILLER-classified (no contract IMPORTANT_LOCATION_TYPES / surface tag) -- an
                       important location may never knowingly leak. If the location later gains a
                       suppression mechanism, or stops being filler, the gate reports it for removal.

Entry schema (both dicts): ``{ap_id: {"reason": str, "issue": str, "date": "YYYY-MM-DD"}}``.
``reason`` = why it's here; ``issue`` = the tracker/memory tag to resolve it; ``date`` = when it was
accepted (ground truth expires -- date it like a dump file, per CONTRIBUTING "Verification").

Both are EMPTY today, ON PURPOSE. The 2026-07-14 re-derivation of the gate found a small set of
ware-bearing locations with no suppression mechanism (their flags appear in NO ItemLotParam row, so
there is no lot to blank, and their wares are farmable goods, so id-keyed suppression is correctly
declined). Those are REAL, still-undecided findings: they live as the encoded suppression BASELINE in
tests/test_coverage_gate.py -- visible in every report -- rather than being laundered through this
ledger before anyone decided to accept them. Move an entry here only once it is a considered decision.
"""

# ap_id -> {"reason", "issue", "date"}. Excluded from the pool; see module docstring.
QUARANTINE = {}

# ap_id -> {"reason", "issue", "date"}. Emitted + detectable but knowingly unsuppressable; FILLER only.
ACCEPTED_LEAKS = {
    7772051: {   # Shadow Keep :: Rune Arc - near Storehouse, First Floor (f21017010)
        "reason": "Rune Arc (filler) whose vanilla ware is handed by an EMEVD award that bypasses the "
                  "blanked ItemLotParam lot 21010010 (gen_data.EVENT_AWARD_ITEM_FLAGS): the lot is a "
                  "decoy and the event delivers the item, so blanking suppresses nothing and it "
                  "double-dips. Rune Arc is a farmable good, so id-keyed suppression is (correctly) "
                  "declined and there is no delivery lot to blank -- no mechanism can suppress it. "
                  "Filler (a spare consumable, never progression), so the leak is tolerable.",
        "issue": "er-emevd-award-suppression-leak",
        "date": "2026-07-21",
    },
}


_REQUIRED_FIELDS = ("reason", "issue", "date")


def validate_ledger():
    """Return a list of problems with the ledger's OWN shape (every entry needs reason/issue/date, no
    ap_id may appear in both dicts). Raises nothing; the coverage test asserts the returned list is
    empty so a malformed entry fails at gen, not in-game."""
    problems = []
    for name, table in (("QUARANTINE", QUARANTINE), ("ACCEPTED_LEAKS", ACCEPTED_LEAKS)):
        for ap_id, meta in table.items():
            if not isinstance(ap_id, int):
                problems.append(f"{name}: ap_id {ap_id!r} must be an int")
            if not isinstance(meta, dict):
                problems.append(f"{name}[{ap_id}]: entry must be a dict"); continue
            for f in _REQUIRED_FIELDS:
                if not meta.get(f):
                    problems.append(f"{name}[{ap_id}]: missing required field {f!r}")
    both = set(QUARANTINE) & set(ACCEPTED_LEAKS)
    if both:
        problems.append(f"ap_id(s) in BOTH QUARANTINE and ACCEPTED_LEAKS: {sorted(both)}")
    return problems
