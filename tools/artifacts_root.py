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
