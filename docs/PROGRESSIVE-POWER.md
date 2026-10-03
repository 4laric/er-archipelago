# Progressive power — branch status

Issue [#1637](https://github.com/4laric/er-archipelago/issues/1637).

Implemented: `progressive_talismans: true` (default off). The 16 supported numbered
families replace their existing seed rewards one-for-one. Copies pay base,
+1, +2, +3 in that order; small seeds can stop at an earlier rank. The
option does not add missing ranks or spend the seed's reserved stone supply.
DLC gear exclusions still apply. Different named talismans, such as
Dragoncrest Greatshield Talisman, remain separate. Arsenal Charm is not a
ladder: its base is absent from the grant catalogue. Family start inventory and
vanilla placement reject with an actionable option error.

Talismans use the existing receipt ledger, so sold or discarded gear is not
resurrected. The native grant path preserves accessory-category IDs instead
of converting them into goods. The seed requires `progressive_talismans_v1`
and refuses older clients.

Not implemented: native weapon upgrade and Rune Level hard caps. The tested
`er-logic::power_caps::Ladder` models two proposed tracks (regular +3→+25,
somber +1→+10) and Rune Level 30→150, with up to ten unlocks sized to kept
regions. These numbers are prototypes, not player options or active limits.

The enforcement gate must precede the engine's upgrade/level-up transaction,
including purchasing several levels in one menu visit. Grant-time weapon
clamping alone permits blacksmith bypasses. Blocking the level-up menu only
after the current level reaches its cap permits a multi-level bypass.
Reverting stats after purchase risks losing spent runes and is unacceptable.
Neither incomplete mechanism is advertised as a hard cap on this branch.

Remaining work: verify and implement native transaction/menu limits, preserve
owned gear and stats, show the currently unlocked limits, wire virtual AP
unlock receipts to the ladders, and smoke-test the running game before making
the two hard-cap options available. Defaults must continue to behave normally.

Automated validation for the implemented portion: 15 focused world tests,
28 metadata/grouping/contract tests, 31 successful native generation runs
(three feature sweeps plus 14 regression configurations across two seeds),
1,556 pure client tests and 130 Windows client tests. The DLL builds; formatting
and default/profile Clippy checks pass. The running game has not been smoke-tested.
