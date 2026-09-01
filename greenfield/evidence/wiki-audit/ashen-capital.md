# Ashen Capital transformed-area route audit

This bounded #1273 slice records two independently authored walkthrough leads for Leyndell's
vanilla transition to the Ashen Capital. It is an audit-only comparison with the Archipelago
world-state implementation: it changes no logic and does not add Maliketh to any AP requirement.
Both claims remain `lead_only` with `game_version=unknown`.

## Sources and reproducibility

`sources.tsv` pins immutable Internet Archive captures for the PowerPyx and EIP Gaming Ashen
Capital walkthroughs. Retrieve either `revision_url` with
`curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL` and compare the complete response body with
the recorded SHA-256. No source prose is redistributed; the registry contains short paraphrases
and citation anchors only.

PowerPyx credits Gage and publishes a March 28, 2022 timestamp, but exposes no article modification
timestamp. EIP credits DanielD and exposes June 11, 2022 publication and February 5, 2025
modification dates. The publishers and authorship families are independent. Neither page states a
compatible Elden Ring patch version, so agreement is useful discovery evidence but not v1.17 proof.

## Vanilla route leads

Both walkthroughs state that defeating Maliketh changes or unlocks the ash-covered capital and
automatically transports the player there. The registry separates those into two claims because
world transformation/access and the one-time transport are different runtime behaviors.

The sources also discuss checks and lost pre-ash pickups. Those statements are intentionally out of
scope: this slice does not infer individual check reachability, event flags, recovery routes, or
which Royal Capital pickups become unavailable.

## Archipelago comparison boundary

The vanilla Maliketh route must not become AP logic. The current project deliberately owns the
finale world-state through its synthetic burn/open-flag handling and tests that handling separately
in `test_gf_ashen_capital_lock.py`, `test_gf_capital_reconciler.py`, and
`test_gf_grace_gates.py`. The guide claims neither prove nor contradict that replacement contract.

Accordingly, these leads cannot justify requiring Maliketh, Farum Azula, Leyndell, a vanilla warp,
or any other story prerequisite in a generated world. Any future accepted predicate still needs
versioned game-data or live-runtime evidence plus a project rule and regression-test witness.
