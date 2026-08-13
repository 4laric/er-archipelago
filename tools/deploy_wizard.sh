#!/usr/bin/env bash
# deploy_wizard.sh -- put the right wizard at /er/ and /er/beta/ on the host box.
#
# THE PROBLEM THIS CLOSES. The wizard is a static page and was deployed by copying it whenever
# somebody copied it, while the apworld ships on a tag. On 2026-08-08 the live page offered 44
# options and the newest tag had 42, and an option the installed apworld has never heard of does not
# fail -- Archipelago prints one line among ~50 loader errors and generates the seed WITHOUT it.
# See SPEC-publishing-pipeline.md.
#
# So: two channels, both built from a REF rather than from whatever was lying around.
#
#     /er/wizard.html        <- wizard/wizard.html at the STABLE tag (release/CHANNELS.tsv)
#     /er/beta/wizard.html   <- wizard/wizard.html at main
#     /er/checks.html        <- er-archipelago-check-browser.html at the STABLE tag
#     /er/beta/checks.html   <- er-archipelago-check-browser.html at main
#     /er/report.html        <- wizard/report.html at the STABLE tag
#     /er/questlines.html    <- er-archipelago-questline-dag.html at the STABLE tag
#     /er/beta/questlines.html <- er-archipelago-questline-dag.html at main
#     /er/landing.html       <- wizard/landing.html at the STABLE tag       (--landing only)
#
# !! THE LANDING PAGE GOES IN ER_STATIC_DIR, NOT AT THE FILESYSTEM ROOT, AND THAT WAS A BUG.
# It first shipped writing ${ER_ROOT_DIR}/index.html on the assumption that peliarch served `/`
# from a static directory. It does not: `/` is a Flask route (webgui/app.py), and Caddy does
# `reverse_proxy web:8080` for everything -- so that file would have been written and never
# served, and nobody would have found out until the front page failed to change.
#
# The app now serves ER_STATIC_DIR/landing.html at `/` (peliarch PR #11), which is the same
# directory and the same atomic, tag-pinned install that wizard.html and checks.html already
# use. One directory, three pages, one deploy.
#
#   ER_STATIC_DIR=/srv/er ./tools/deploy_wizard.sh --landing
#
# ---- --site : ship a page fix WITHOUT cutting a release ----------------------------------------
#
#   ./tools/deploy_wizard.sh --site        # landing.html + report.html, from MAIN, in seconds
#
# THE PROBLEM IT SOLVES. A typo on the landing page needed a tag, a CHANNELS promotion and a full
# deploy, because every artifact here is pinned to the STABLE tag. That is right for the wizard and
# wrong for a page that describes nothing.
#
# !! IT IS DELIBERATELY NOT "all the static pages". The wizard MUST NOT get ahead of the released
# apworld: Archipelago does not error on an option the installed apworld has never heard of, it
# prints one line among fifty and generates the seed WITHOUT it (SPEC-publishing-pipeline.md 2.1).
# The check browser and the questline DAG are joins over committed generator output, so a newer
# copy describes a corpus the released build does not have. All three stay on stable, always.
#
# THE SPLIT IS DERIVED, NOT A LIST SOMEONE MAINTAINS. A page is COUPLED if it carries an option
# surface (`er-options-metadata`) or a data stamp (`inputs_hash`); it is FREE if it carries
# neither. test_gf_publish_channels asserts SITE_PAGES below is EXACTLY the free set, in BOTH
# directions -- so a page that gains a stamp stops being shippable this way on the commit that
# gives it one, and a new page with no stamp cannot be silently left out.
#
# !! --landing FAILS UNTIL v0.4.0 IS TAGGED, and that is correct. It fetches from the STABLE tag,
# and wizard/landing.html does not exist at v0.3.10. The failure is loud ("fetch failed: landing
# stable (v0.3.10)") rather than a page silently not appearing. Promote stable first.
#
# THE CHECK BROWSER AND THE QUESTLINE DAG ARE PINNED THE SAME WAY AND FOR THE SAME REASON. Both are
# pure joins over committed generator output, so a copy from a different ref than the wizard beside
# it describes a different corpus -- the exact skew SPEC-publishing-pipeline.md measured on the
# wizard, one file over. Together they are ~3.2 MB, so `--no-checks` exists for a cron that runs
# oftener than the data moves; it skips both.
#
# !! THE QUESTLINE DAG IS HERE BECAUSE IT WAS ONLY EVER ON THE BOX BY ACCIDENT. Until 2026-08-13 the
# host served it because the Dockerfile's `ertools` stage BAKED it into the image at build time --
# so it existed, unpinned to any tag, and would have vanished the moment /er-static became a bind
# mount fed by this script. It was found by listing the container's directory before mounting over
# it, not by anything that would have told us afterwards. A file that only exists because of a build
# step nobody remembers is one rebuild from gone.
#
# It FETCHES, it does not build: the box needs no checkout, no python, no node. Nothing here is
# specific to peliarch except the default target, so it also works for any other host.
#
#   ER_STATIC_DIR=/srv/er ./tools/deploy_wizard.sh
#   ER_STATIC_DIR=/srv/er ./tools/deploy_wizard.sh --dry-run
#   ./tools/deploy_wizard.sh --stable-only          # promote stable, leave beta alone
#
# Cron it if you like -- `beta` tracks main, so on a daily-stable project this wants to run at least
# as often as you merge:
#   */15 * * * *  ER_STATIC_DIR=/srv/er /opt/er/deploy_wizard.sh >>/var/log/er-deploy.log 2>&1
#
# !! THE INSTALL IS ATOMIC (write .tmp, then `mv`). A wizard is one 2 MB file that a browser can be
# mid-GET on; `curl -o` straight onto the served path serves a truncated page for the length of the
# download, and a half-parsed wizard renders as a blank div rather than an error anybody reports.
set -euo pipefail

REPO="${ER_REPO:-4laric/er-archipelago}"
RAW="https://raw.githubusercontent.com/${REPO}"
DEST="${ER_STATIC_DIR:-/srv/er}"
DRY=0
STABLE_ONLY=0
NO_CHECKS=0
LANDING=0
SITE_ONLY=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --stable-only) STABLE_ONLY=1 ;;
    --no-checks) NO_CHECKS=1 ;;
    --landing) LANDING=1 ;;
    --site) SITE_ONLY=1 ;;
    -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
    *) echo "unknown argument: $a" >&2; exit 2 ;;
  esac
done

say() { printf '%s\n' "$*"; }
# Rule 4: a filter with no tally is a lie. Skips are counted and reported at the end.
SKIPPED_ARTIFACTS=0
# !! `die` exits the SHELL, so install_one's RETURN trap does not run and its .tmp survives --
# in the directory the web server is serving. A stale `wizard.html.ab12cd.tmp` is fetchable and
# is a half-written page under a name nothing will ever clean up. Track the in-flight temp file
# globally and clear it on EXIT as well, so an abort leaves the directory as it found it.
CURRENT_TMP=""
trap 'rm -f "$CURRENT_TMP"' EXIT
die() { printf 'deploy_wizard: %s\n' "$*" >&2; exit 1; }

# ---- which tag is stable? Read it from the ledger AT MAIN, so the answer comes from the same place
# the repo records it and a promotion is a commit rather than an argument typed on a box.
ledger="$(curl -fsSL "${RAW}/main/release/CHANNELS.tsv")" || die "could not fetch release/CHANNELS.tsv"
stable_tag="$(printf '%s\n' "$ledger" | awk -F'\t' '!/^#/ && $1=="stable" { t=$2 } END { print t }')"
[ -n "$stable_tag" ] || die "no stable row in release/CHANNELS.tsv"
say "channels: stable -> ${stable_tag} | beta -> main"

# ---- fetch + install one file, atomically, and only if it looks like the thing we asked for.
# !! THE SENTINEL CHECK IS NOT PARANOIA. raw.githubusercontent answers 404 with an HTML page and
# `curl -f` catches that, but a ref that exists and has no wizard, or a proxy that helpfully returns
# a login page, both arrive as 200 with a body. "Did I just install a login page as the wizard" is
# not a question you want answered by a player.
install_one() {  # ref, source path in repo, destination path, sentinel, label
  local ref="$1" src="$2" dst="$3" sentinel="$4" label="$5" tmp
  # mkdir BEFORE mktemp: the temp file has to be a sibling of the destination (mv across filesystems
  # is a copy, which is not atomic), and `beta/` does not exist on a first run.
  mkdir -p "$(dirname "$dst")"
  tmp="$(mktemp "${dst}.XXXXXX.tmp")"
  CURRENT_TMP="$tmp"
  # shellcheck disable=SC2064
  trap "rm -f '$tmp'; CURRENT_TMP=" RETURN
  # !! A 404 AT THE STABLE TAG IS NOT THE SAME FAILURE AS A 404 AT MAIN, and collapsing them
  # aborts a routine deploy every time a NEW page is added. main always carries the current set by
  # construction -- it is this repo -- so a missing file there is a real bug and stays fatal. A
  # stable TAG legitimately predates an artifact added after it was cut, and the honest answer is
  # "not in this release yet", not "the deploy is broken" and not a silently older copy.
  # Anything that is not a 404 -- network, DNS, a proxy, a ref that does not exist -- stays fatal
  # for every ref, because none of those mean what a 404 means.
  local http
  http="$(curl -sSL -w '%{http_code}' -o "$tmp" "${RAW}/${ref}/${src}")" || http="000"
  if [ "$http" = "404" ]; then
    if [ "$ref" = "main" ]; then
      die "${src} is MISSING at main -- that is this repo's own tree, so this is a bug, not a gap"
    fi
    say "  SKIP ${label}: ${src} is not in ${ref} yet (added after that tag was cut)"
    SKIPPED_ARTIFACTS=$((SKIPPED_ARTIFACTS + 1))
    return 0
  fi
  [ "$http" = "200" ] || die "fetch failed: ${label} (${ref}) -- HTTP ${http}"
  grep -q "$sentinel" "$tmp" \
    || die "fetched ${label} does not contain ${sentinel} -- refusing to install it"
  local bytes ver
  bytes="$(wc -c < "$tmp" | tr -d ' ')"
  ver="$(sed -n 's/.*"apworld_version": *"\([^"]*\)".*/\1/p' "$tmp" | head -1)"
  [ -n "$ver" ] || ver="(unstamped -- older than the version stamp)"
  if [ "$DRY" = "1" ]; then
    say "  DRY-RUN ${label}: would install ${bytes} bytes, apworld ${ver} -> ${dst}"
    return 0
  fi
  chmod 0644 "$tmp"
  mv -f "$tmp" "$dst"
  say "  ${label}: ${bytes} bytes, apworld ${ver} -> ${dst}"
}

[ "$DRY" = "1" ] || [ -d "$DEST" ] || die "ER_STATIC_DIR does not exist: ${DEST}"

# The landing page needs no separate target any more -- it lands in DEST beside the other two,
# and DEST is already checked above.

WIZ_SRC="wizard/wizard.html"
WIZ_SENTINEL='id="er-options-metadata"'
CHK_SRC="er-archipelago-check-browser.html"
# The check browser's own map container -- structural, and nothing a 200-with-a-login-page has.
CHK_SENTINEL='id="mapslot"'
# !! THE FREE SET: src:name:sentinel, space-separated. Pages carrying NEITHER an option surface
# NOR a data stamp, so they cannot skew against a released apworld and may ship from main at any
# time. Asserted against the files themselves by test_gf_publish_channels -- do not edit without
# reading that test.
SITE_PAGES="wizard/landing.html:landing.html:er-landing wizard/report.html:report.html:er-report"
RPT_SRC="wizard/report.html"
# The report builder's own form root. It is small and cheap, so it is NOT behind --no-checks:
# the one page a stuck player needs should never be the one a fast cron skipped.
RPT_SENTINEL='id="er-report"'
QDAG_SRC="er-archipelago-questline-dag.html"
# Likewise: the DAG page's own graph pane. Its `id="q"` search box would NOT do -- one letter is a
# string a login page can plausibly contain, and a sentinel that can pass by accident is not one.
QDAG_SENTINEL='id="mer"'

# ---- --site: the free pages only, from main, then stop. ----------------------------------------
if [ "$SITE_ONLY" = "1" ]; then
  say "site-only: the pages that carry no option surface and no data stamp, from main"
  for entry in $SITE_PAGES; do
    src="${entry%%:*}"; rest="${entry#*:}"; name="${rest%%:*}"; sentinel="${rest##*:}"
    install_one "main" "$src" "${DEST}/${name}" "id=\"${sentinel}\"" "site    ${name} (main)"
  done
  say ""
  say "The wizard, the check browser and the questline DAG were NOT touched: they are pinned to the"
  say "stable tag on purpose, and a copy ahead of the released apworld is the failure this whole"
  say "script exists to prevent. Run without --site to move those."
  exit 0
fi

install_one "$stable_tag" "$WIZ_SRC" "${DEST}/wizard.html" "$WIZ_SENTINEL" "wizard  stable (${stable_tag})"
install_one "$stable_tag" "$RPT_SRC" "${DEST}/report.html" "$RPT_SENTINEL" "report  stable (${stable_tag})"
[ "$NO_CHECKS" = "1" ] || {
  install_one "$stable_tag" "$CHK_SRC" "${DEST}/checks.html" "$CHK_SENTINEL" "checks  stable (${stable_tag})"
  install_one "$stable_tag" "$QDAG_SRC" "${DEST}/questlines.html" "$QDAG_SENTINEL" "qdag    stable (${stable_tag})"
}

if [ "$STABLE_ONLY" = "0" ]; then
  install_one "main" "$WIZ_SRC" "${DEST}/beta/wizard.html" "$WIZ_SENTINEL" "wizard  beta (main)"
  install_one "main" "$RPT_SRC" "${DEST}/beta/report.html" "$RPT_SENTINEL" "report  beta (main)"
  [ "$NO_CHECKS" = "1" ] || {
    install_one "main" "$CHK_SRC" "${DEST}/beta/checks.html" "$CHK_SENTINEL" "checks  beta (main)"
    install_one "main" "$QDAG_SRC" "${DEST}/beta/questlines.html" "$QDAG_SENTINEL" "qdag    beta (main)"
  }
fi

# The landing page ships from the STABLE tag like everything else a stranger lands on. Its links
# point at /er/ and /er/checks.html, so a landing page from main advertising a page that stable
# does not serve yet is the same skew one level up.
if [ "$LANDING" = "1" ]; then
  install_one "$stable_tag" "wizard/landing.html" "${DEST}/landing.html" \
    'id="er-landing"' "landing stable (${stable_tag})"
fi

if [ "$SKIPPED_ARTIFACTS" -gt 0 ]; then
  say ""
  say "!! ${SKIPPED_ARTIFACTS} artifact(s) were not in the stable tag and were NOT installed."
  say "   They ship on the next release. Promote stable in release/CHANNELS.tsv and rerun."
fi

cat <<'NOTE'

Live at:
  /                       stable   the landing page      (--landing only; served by the app
                                   from ER_STATIC_DIR/landing.html, not from the web root)
  /er/wizard.html         stable   the options wizard
  /er/report.html         stable   the bug report builder
  /er/checks.html         stable   the check browser
  /er/questlines.html     stable   the questline DAG
  /er/beta/wizard.html    beta
  /er/beta/checks.html    beta

The page works out which it is from its own URL and banners itself, so nothing here edits the HTML.

Note the trailing slash: `/er/` maps to wizard.html, but `/er/beta/` does NOT -- the Flask route is
`/er/<path:filename>` and "beta/" is not a file. Link the full path, or add a route for it.
NOTE
