# Gameplay-wiki audit pilot: Sellen/Jerren endings

This #1273 pilot examines the two mutually exclusive Sellen/Jerren ending choices named in #1271.
It normalizes only the terminal choice and reward paths. It does not attempt to encode the full
Sellen quest, and it makes no gameplay-rule change.

## Sources and reproducibility

`sources.tsv` records immutable Internet Archive revision URLs, page authors, publication and
modification dates, archive times, complete-response SHA-256 values, license disposition, and
version applicability. Retrieve a revision with
`curl --compressed -LsS -A "Mozilla/5.0" REVISION_URL` and compare its SHA-256. No source prose is
redistributed here; `leads.tsv` contains only short paraphrases and section anchors.

Game8 credits its Elden Ring walkthrough team. Gamer Guides credits Ben Chard and Claire Farnworth
on the Sellen page and Ben Chard on the Jerren page. Game8 and Gamer Guides are treated as two
independent author/publisher families. The two Gamer Guides pages remain one family, not two votes.
None of the pages states v1.17 applicability; their last recorded content updates predate v1.17, so
all findings remain `lead_only` with unknown game version.

## Findings

The independent guide families agree on two terminal routes outside the Raya Lucaria Grand Library:

1. The gold sign aids Sellen against Jerren. Defeating Jerren awards his Eccentric set. This pilot
   represents that route with Eccentric's Hood (AP 7770618).
2. The red sign aids Jerren against Sellen. After the battle, speaking to Jerren outside the library
   awards an Ancient Dragon Smithing Stone (AP 7773737).

These are mutually exclusive alternatives, not requirements that can be combined. Each normalized
lead includes Raya Lucaria Academy, the selected quest choice, and, for Jerren's reward, the final
conversation. Neither lead asserts that those immediate steps are sufficient without the preceding
quest.

## Comparison with current logic

Current generated data places Eccentric's Hood in Raya Lucaria Academy and allows the Rennala sweep
to grant it. That region label agrees with the terminal scene but does not encode the required ending
choice. The sweep is an Archipelago alternate and is outside the vanilla guides' scope.

The Ancient Dragon Smithing Stone at AP 7773737 is currently labeled Caelid near Smoldering Church.
Committed questline provenance identifies it as flag f400400 from Jerren talk lot 104000, but the
accepted world rule does not encode the red-sign choice or the post-battle conversation. The two
guide families therefore identify a concrete modeling gap and a likely misleading location label,
but cannot correct either on their own because they are unversioned gameplay prose.

Before changing logic, versioned in-game capture or script-level evidence must establish the full
quest prerequisites and terminal branch predicates. In particular, the earlier route spans multiple
regions and NPC states; collapsing it to Academy access plus one choice would under-gate both checks.
