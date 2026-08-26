"""`--path <artifacts-root>` -- ONE spelling of "read the corpus from over there".

Every tool that reads the extracted `elden_ring_artifacts/` tree hardcoded
`<repo>/elden_ring_artifacts` and, one at a time, three of them grew a private `--artifacts` flag
with a private validation message. That is N copies of a decision, which is how two of them ended
up disagreeing about the param-dir layout (see `datamine_item_grace_coords._param_dir`). The corpus
is licensing-restricted and .gitignore'd, so it lives WHEREVER its owner keeps it -- moving it must
not mean editing tools.

Usage, in a tool that already has a `_set_artifacts_root(path)` seam:

    import artifacts_root                      # tools/ is on sys.path (see the callers)
    ...
    artifacts_root.add_path_argument(ap)       # adds --path, and --artifacts as the older spelling
    ...
    root = artifacts_root.resolve(args.path)
    if root:
        _set_artifacts_root(root)

The DEFAULT never moves: absent the flag the tool reads `<repo>/elden_ring_artifacts`, exactly as
before. There is deliberately NO environment-variable fallback: an invisible input is how a scan
reads a stale corpus and writes a plausible table (`ER_EVENT_DIR` already costs us that on the
EMEVD side). If the root moved, SAY SO on the command line, where the run's transcript records it.
"""
import os

DIRNAME = "elden_ring_artifacts"

_HELP = ("read the extracted artifacts corpus from DIR instead of <repo>/%s "
         "(the default is unchanged; there is no env-var fallback)" % DIRNAME)


def default_root(repo):
    """The unchanged default: the corpus directory beside the repo's own root."""
    return os.path.join(repo, DIRNAME)


def add_path_argument(parser, artifacts_alias=True, extra_help=""):
    """Add `--path DIR` (and, where a tool already shipped it, `--artifacts DIR` as an ALIAS of the
    same dest, so every command in docs/PLAYAREA-ITEM-SCAN.md keeps working verbatim)."""
    names = ["--path"]
    if artifacts_alias:
        names.append("--artifacts")
    help_text = _HELP
    if artifacts_alias:
        help_text += "; --artifacts is the older spelling of this same flag"
    if extra_help:
        help_text += "; " + extra_help
    parser.add_argument(*names, dest="path", metavar="DIR", default=None, help=help_text)


def resolve(value):
    """`None` when the flag was not passed (keep the default). Otherwise an absolute path that IS a
    directory -- a typo'd root must stop the run, not scan an empty tree and write a table."""
    if not value:
        return None
    path = os.path.abspath(os.path.expanduser(value))
    if not os.path.isdir(path):
        raise SystemExit("FATAL: --path %s is not a directory" % value)
    return path


# ---------------------------------------------------------------- MSB DISCOVERY
# WHY THIS IS HERE AND NOT IN EACH TOOL. `--path` said WHERE the corpus is; it never said where the
# witchy'd MSBs sit INSIDE it, and every tool answered that privately: grace_ground read `map/`
# only, arena_graces read `map/` + `mapstudio/`, merchant_shops read `mapstudio/` +
# `map/mapstudio/`, msb_item_regions read `mapstudio/` + the root, item_grace_coords read all
# three. So an export whose MSB dirs sit FLAT under `<root>/mapstudio/` -- which is the shape
# WitchyBND actually produced for Alaric on 2026-08-26 -- ran six tools two ways: three found the
# corpus and three said `FATAL: no witchy'd m60/m61 MSBs under <root>/map`. That is N copies of one
# decision disagreeing, the same class of bug `--path` itself was written to kill.
#
# ONE ordered candidate list, and a hit is DEMONSTRATED, not assumed: a candidate counts only when
# it DIRECTLY contains `m??_??_??_??-msb-dcx` children. That is what makes the bare-root layout
# safe to accept -- an artifacts root full of unrelated siblings (`_pilot`, `breakgeom`, `m00`,
# `m60`) is not mistaken for an MSB dir, because none of those names is a witchy MSB dir.
#
#   <root>/map            the layout grace_ground and the grace tables were derived from
#   <root>/mapstudio      the layout WitchyBND produces when it is pointed at the map dir
#   <root>/map/mapstudio  the legacy nesting merchant_shops has always accepted
#   <root>                the witchy export dropped straight into the corpus root
#
# `msb_dir()` is for the tools that scan ONE dir (first hit wins). `msb_dirs()` is for the tools
# that scan SEVERAL and dedupe by map id -- their reason is real (2026-07: `mapstudio/` held only
# 66 of the 118 boss maps while `map/` held all of them, and reading one of the two would have
# reported 52 arenas "missing"), so this returns every candidate that holds MSBs, in order.
import re as _re

_MSB_DIR_RE = _re.compile(r"^m\d\d_\d\d_\d\d_\d\d-msb-dcx$")

MSB_SUBDIRS = ("map", "mapstudio", os.path.join("map", "mapstudio"), "")


def msb_candidates(root):
    """Every place a witchy'd MSB tree is accepted under `root`, in search order."""
    return [os.path.join(root, s) if s else root for s in MSB_SUBDIRS]


def holds_msb_dirs(path):
    """True when `path` DIRECTLY contains witchy MSB directories. Existence is not enough: the
    bare-root candidate would otherwise match every root ever passed."""
    if not path or not os.path.isdir(path):
        return False
    try:
        names = os.listdir(path)
    except OSError:
        return False
    return any(_MSB_DIR_RE.match(n) and os.path.isdir(os.path.join(path, n)) for n in names)


def msb_dirs(root):
    """Every candidate under `root` that actually holds witchy'd MSB dirs, in search order.
    Empty when none does -- callers keep their own default and FATAL with `msb_search_report`."""
    return [c for c in msb_candidates(root) if holds_msb_dirs(c)]


def msb_dir(root):
    """The FIRST candidate that holds witchy'd MSB dirs, or None. For one-dir scanners."""
    for c in msb_candidates(root):
        if holds_msb_dirs(c):
            return c
    return None


def msb_search_report(root):
    """The lines a FATAL must carry: every location tried, so `no MSBs found` is actionable
    without reading this file. A message that names one path teaches the reader the wrong layout."""
    return "; ".join("tried %s" % c for c in msb_candidates(root))
