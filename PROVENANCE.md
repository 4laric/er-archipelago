# Elden Ring Archipelago — Provenance & Permissions

*Local reference / not for commit to the public repo. Last updated 2026-07-05.*

## Bottom line

The project is legally clear to modify and redistribute. The only open issue is a
**Nexus Mods house-policy** matter — uploading work derived from another modder
(Bedrock) without that modder's explicit permission — which is separate from
copyright and is resolved by obtaining and documenting Bedrock's OK.

## License chain

The apworld is built on top of **Bedrock's Elden Ring apworld**, which is released
under the **MIT License**. MIT grants the right to use, modify, and redistribute,
including in derivative works, provided the copyright notice and license text are
retained. Building on and redistributing a modified version of Bedrock's apworld is
therefore permitted by the license.

    matt (upstream location set)  →  Bedrock's apworld (MIT)  →  this apworld (MIT-derived)

MIT compliance obligation on our side: ship Bedrock's original MIT license text and
copyright notice with the apworld, and attribute Bedrock as the upstream work.

## Layer-by-layer status

**Runtime client (Rust, `eldenring-archipelago`).** Original code. Resolves matt's
slot key `token1` → `getItemFlagId` and reads public param data
(`ShopLineupParam.eventFlag_forStock`) to map checks to event flags. No third-party
mod code, no AI-on-anyone's-source. This is the cleanest layer and is unambiguously
our own work — appropriate to host as the primary artifact.

**apworld.** Derived from Bedrock's MIT apworld (above). The underlying location set
ultimately traces upstream to matt's set; location descriptions are reworded/original
rather than copied. Our added logic — e.g. the `num_regions` archipelago mode — is
original. License-wise this layer is covered by MIT via Bedrock.

## The one actual issue: Nexus house policy

Nexus Mods enforces a permission rule that is stricter than, and independent of, the
software license:

> "Submission of existing user-submitted content without obtaining permission from
> the original author(s) is strictly prohibited." — Nexus File Submission Guidelines

> "The mere accreditation of an author is no substitute for receiving explicit
> permission to upload or modify someone else's content."

So an MIT license does **not** by itself satisfy Nexus. Because this apworld is built
on Bedrock's mod, Nexus policy requires **Bedrock's explicit permission** to host it
there — credit alone is not enough. Nexus also asks that permission be **documented**
(preferably a Nexus forum PM) so staff can verify it.

## Resolution paths

1. **Get Bedrock's explicit permission, documented.** Bedrock is active and engaged
   in the thread. A short written OK (ideally a Nexus PM, or a screenshot of a Discord
   confirmation) clears the house-policy issue directly. This is the cleanest fix.

2. **Split the distribution to match Archipelago convention.** Host only the original
   runtime client (the `.dll`) on Nexus, and publish the `.apworld` as a GitHub
   release — which is the standard AP distribution channel anyway (users install via
   the launcher's "Install APWorld" or by dropping it in `custom_worlds`). This keeps
   the unambiguously-original code on Nexus and moves the derived apworld off Nexus's
   permission surface. Retain Bedrock's MIT notice on the GitHub distribution.

3. **Both.** Do #2 for convention/cleanliness and still secure #1 for the record.

## Notes on thread claims (for accuracy)

- "Bedrock's code is a non-issue due to it not being under license" — imprecise. It
  *is* licensed (MIT); MIT is precisely what makes redistribution permitted.
- "They were using AI on matt's or natalie's code" — the derivation runs through
  Bedrock's MIT apworld, not a direct copy of matt's/natalie's source; the client is
  original and matt-free.
