"""Structured degradation ledger for the coverage gate (hand-authored -- NOT generated).

Two escape hatches, both self-cleaning so a hole that becomes fixable forces the gate to say
"remove it" (the ledger can never rot into a permanent excuse):

  * QUARANTINE      -- a location EXCLUDED from the pool entirely (gen_data / a feature must actually
                       drop it). An entry is a promise that the location is NOT emitted. If a
                       quarantined location IS still emitted and now passes every coverage check,
                       coverage._quarantine_violations reports it: the reason is gone, delete the entry
                       (and stop excluding the location).

  * ACCEPTED_LEAKS  -- a location that IS emitted and detectable but is KNOWINGLY unsuppressable
                       (its vanilla ware leaks). Legal ONLY when the location is FILLER-classified
                       (no big-ticket tag) -- an advancement/useful location may never knowingly leak.
                       If the location later gains a suppression mechanism, or stops being filler, the
                       gate reports it for removal.

Entry schema (both dicts): ``{ap_id: {"reason": str, "issue": str, "date": "YYYY-MM-DD"}}``.
``reason`` = why it's here; ``issue`` = the tracker/memory tag to resolve it; ``date`` = when it was
accepted (ground truth expires -- date it like a dump file, per CONTRIBUTING "Verification").

Both are EMPTY today: the greenfield tree emits a derived acquisition flag and a checkItemFlags
suppression entry for every ware-bearing location, so nothing needs quarantining or an accepted leak.
The one open gap (Stormveil Castle's bogus open flag 200) is a REGION-open data bug to fix in
gen_data, not a per-location leak, so it is not laundered through this ledger -- the gate reports it
as a live region violation until the flag is allocated.
"""

# ap_id -> {"reason", "issue", "date"}. Excluded from the pool; see module docstring.
QUARANTINE = {}

# ap_id -> {"reason", "issue", "date"}. Emitted + detectable but knowingly unsuppressable; FILLER only.
ACCEPTED_LEAKS = {}


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
