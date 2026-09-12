# Sweep completion flag audit, 2026-09-12

The Scadutree Avatar report shows three groups still waiting after the boss kill.
The map script `m61_50_48_00.emevd.dcx.js`, event 2050480800, waits for the final
death, displays the defeat banner, then sets 2050480800. IDs 2050480810/11/12 are
health-bar/referred-damage entities. An older log showing 0810 eventually set
does not establish reliable completion; it was not sufficient grounds to retain
the proxy as the completion condition.

The generator merges the three already allocated groups onto 2050480800.
Comparison against trunk confirms exactly 16 links change trigger, all members
are preserved, and every unrelated group remains identical. Allocation still uses
the original healthbar roster so this does not re-deal Shadow Keep's other checks.
The final trigger is classified as a major boss by the existing achievement roster.

The companion client fixes existing seeds at the completion read. It preserves
their original member lists, identities and per-group lock gates; all three read
2050480800. Phase deaths and manually set proxy flags cannot grant a sweep early.
An already defeated boss is recognized on the next eligible poll.

## Similar-case audit

Ran `tools/audit_sweep_trigger_flags.py` over 589 bundled EMEVD scripts and all
245 healthbar keys (210 pre-fix active groups). Fixed its stale generated-table
path so the audit runs against the current layout.

Twenty keys have no setter found. Only the three Avatar proxies have active
groups. The other seventeen already have zero members:

- Fia champions: 12030810/11/12/13.
- Abductor Virgin: 16000861; Radagon: 19000810; Freyja: 20010852.
- Dungeon partners: 30100801, 30120801, 30140801, 31110801/02, 31150801,
  31180801, 31200801, 31220801/02.

Also compared every active trigger to `defeat_flags()` output. Four apparent
mismatches are parser limitations, not additional fixes:

- Messmer 21010800: m21_01 explicitly sets 21010800 after the banner. The
  parser's 21019205 comes from a separate NPC handler.
- Patches 31000800 and 31000850: m31_00 sets the corresponding boss flags;
  3683 is a separate quest/death state and must not replace them.
- 34100800: m34_10 sets both 9280 and 34100800 after the banner. Taking only
  the first flag mistakenly selects the achievement flag.

No other active instance was confirmed by this audit. Corpus setter presence is
not proof that every possible randomized encounter executes that setter; this is
a source audit, not live verification of every boss.
