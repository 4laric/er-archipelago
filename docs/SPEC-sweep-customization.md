# Sweep customization without a larger options wizard

Proposal, 2026-10-03. This is a design for future work, not an implemented option.
The generated sweep reference is the first delivery; custom definitions and the
tracker's pre-fight payout preview remain separate work.

## Player flow

Keep Dungeon Sweep's existing choices. Put **Customize sweeps…** beside its reference
link, opening a focused editor with the same region groups, original boss arenas and
searchable check lists as the reference. No individual boss becomes a wizard option.

Start from the current definitions. Offer a few presets inside the editor, then allow
individual sweep disabling and checked reassignment of existing candidate checks.
Show the before/after list and count for every affected boss, including checks left for
manual collection. Reset restores the shipped definitions. The wizard gets one summary:
“Custom sweeps: 3 changed, 1 disabled”, with Edit and Reset actions.

The presets must be executable mappings, not labels promising geographic precision
we do not have. In particular, “local only” must be based on accepted map/arena evidence,
not proximity to a Site of Grace. A Leyndell/sewer or Caria/dragon preset needs explicit
membership witnesses across the relevant region and map boundaries.

## One portable generation setting

Use one advanced OptionDict, provisionally `sweep_profile`, serialized by the editor
into the player's normal YAML. Empty means shipped behavior. Carry only overrides,
a format version and the source catalogue hash; never a local filesystem path or an
external URL that another host would have to fetch. YAML import/export preserves it.

Identity is an original arena's boss-defeat flag plus each check's acquisition flag.
Do not store positional AP IDs: retirement and older seeds make those unsuitable for
portable profiles. Display names are labels, never lookup keys. A profile built against
a changed catalogue needs explicit revalidation with a readable diff; generation must
refuse stale or ambiguous references rather than silently applying a different check.

This controls the seed at generation time. A runtime-only editor would change rewards
without updating placement, boss-key gates or the tracker contract, so it is unsuitable.
The client can consume the existing emitted sweep groups after the world resolves them;
confirm all existing client gates and implied sweep relationships before promising that
no client change is needed.

## Limits for the first supported version

Allow disabling groups and removing members first. Add reassignment only for checks
already admitted to sweeps, within the same audited arena/member region, and to a
known working trigger enabled by the selected Dungeon Sweep rung. Keep cross-region
transfers, new trigger flags and new check eligibility out of the first version.

Apply overrides once in the world-owned sweep resolver, before SweepSlot nomination.
Rung filtering, progression-surface cuts, Full Area Sweeps and arena reachability must
continue to use that same resolved mapping. Disabled groups cannot nominate a SweepSlot
or retain boss-key gates. Required boss-event gifts and other special attached rewards
must be protected from removal, based on their existing declared provenance, rather
than treating every generated member as freely editable.

Validation names the offending boss/check and the repair. Unknown flags, stale catalogue,
duplicate ownership, dead triggers, incompatible regions and attempts to edit protected
rewards produce an OptionError before fill. Reassignment needs reachability proof for
the destination arena; a same-region check alone is insufficient where physical gates
exist. The preview must distinguish candidate coverage from the final seed payout.

## Acceptance before shipping control

Prove empty profiles preserve existing slot data, and custom profiles resolve identically
for placement, SweepSlot pricing, boss-key gates and client payload. Exercise removals,
disabled groups, reassignments, missing regions, every sweep rung and surface/full-area
combinations in the option matrix and multi-seed fill regression. Reject stale profiles
and physically unreachable reassignments before fill. Verify YAML round trips and replay
the received groups through the client before calling the editor complete.
