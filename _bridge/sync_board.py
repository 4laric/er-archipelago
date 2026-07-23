#!/usr/bin/env python3
"""
sync_board.py - two-way bridge between cards.json and GitHub issues (4laric/er-archipelago).

MODEL (board-authoritative + pull state):
  * cards.json is the SOURCE OF TRUTH for content: title, desc, pri, cat, and the active column
    (ready/blocked/progress/backlog). These are PUSHED to issues every sync (board wins).
  * GitHub is the source of truth for: open/closed, assignee, comment count. These are PULLED back
    into cards.json (and shown on the board).
  * The done<->open axis is 3-way merged against .sync-snapshot.json so a change on EITHER side
    propagates: close an issue -> card goes Done; mark a card Done -> issue closes. A true conflict
    (both sides changed to different states) keeps the BOARD value and is logged.

LINKING: an issue is matched to a card by (1) card.issue number, else (2) a hidden "<!-- card:ID -->"
  marker in the body, else (3) normalized title. First run adopts pre-existing issues by title and
  stamps the marker so later matching survives title/desc edits.

Regenerates er-archipelago-kanban.html from board.template.html each run.

Stdlib only (urllib) - no pip install. Runs anywhere python3 does.

Usage:
    export GH_TOKEN=ghp_xxx            # (Windows: set GH_TOKEN=...)
    python sync_board.py --dry-run     # preview every action, write nothing
    python sync_board.py               # full reconcile: pull state, push content, regen board
    python sync_board.py --mode push   # only board -> issues
    python sync_board.py --mode pull   # only issues -> board
    python sync_board.py --self-test   # run offline logic tests, no network
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PRIORITIES = ["P0", "P1", "P2", "P3"]
ACTIVE_COLS = ("ready", "blocked", "progress", "backlog")
MARKER_RE = re.compile(r"<!--\s*card:([A-Za-z0-9\-_]+)\s*-->")
LEAD_RE = re.compile(r"^[^0-9A-Za-z(]+")  # leading run of non-alnum/non-'(' (emoji, arrows, spaces)


# ---------------------------------------------------------------- pure helpers
def norm(title):
    """Normalized title for matching: drop leading emoji/symbols, lower, strip."""
    return LEAD_RE.sub("", title or "").strip().lower()


def push_title(title):
    """Title actually written to the issue: drop leading emoji/symbols, keep case."""
    return LEAD_RE.sub("", title or "").strip()


def labels_for(card):
    ls = [card["pri"], "area:" + re.sub(r"\s+", "-", card["cat"].lower())]
    if card["col"] != "done":
        ls.append("status:" + card["col"])
    return ls


def body_for(card):
    foot = (
        "\n\n---\n_Area: {cat} | Priority: {pri} | Board column: {col} | synced from cards.json_"
        .format(cat=card["cat"], pri=card["pri"], col=card["col"])
    )
    marker = "\n\n<!-- card:{} -->".format(card["id"])
    return (card.get("desc") or "") + foot + marker


def label_color(name):
    return {
        "P0": "ef4444", "P1": "f59e0b", "P2": "3b82f6", "P3": "6b7280",
    }.get(name) or ("8b5cf6" if name.startswith("status:") else "0e8a16" if name.startswith("area:") else "ededed")


def reconcile(prev, board_done, gh_done):
    """
    3-way merge of the done<->open bit. Returns (action, final_done).
    action in: none | close | reopen | pull_done | pull_reopen | conflict
      close/reopen  -> push the issue state to match the board
      pull_done/pull_reopen -> move the card to match GitHub
      conflict -> both sides changed to different states; keep board, push it
    prev is None on first sight (no snapshot) -> board is authoritative.
    """
    if prev is None:
        if board_done == gh_done:
            return ("none", board_done)
        return ("close" if board_done else "reopen", board_done)
    board_changed = board_done != prev
    gh_changed = gh_done != prev
    if board_changed and not gh_changed:
        return ("close" if board_done else "reopen", board_done)
    if gh_changed and not board_changed:
        return ("pull_done" if gh_done else "pull_reopen", gh_done)
    # both changed, or neither
    if board_done != gh_done:
        return ("conflict", board_done)
    return ("none", board_done)


# ---------------------------------------------------------------- GitHub I/O
class GitHubError(Exception):
    def __init__(self, status, message):
        super().__init__("HTTP {}: {}".format(status, message))
        self.status = status
        self.message = message


class GitHub:
    """Thin GitHub client. All network goes through _call(), which tests monkeypatch."""

    def __init__(self, owner, repo, token, delay=0.6, dry=False):
        self.base = "https://api.github.com/repos/{}/{}".format(owner, repo)
        self.token = token
        self.delay = delay
        self.dry = dry

    def _call(self, method, url, body=None):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", "token " + self.token)
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        req.add_header("User-Agent", "er-board-bridge")
        if data is not None:
            req.add_header("Content-Type", "application/json; charset=utf-8")
        try:
            with urllib.request.urlopen(req) as r:
                raw = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail).get("message", detail)
            except Exception:
                pass
            raise GitHubError(e.code, detail)
        return json.loads(raw) if raw else None

    def _pause(self):
        if not self.dry and self.delay:
            time.sleep(self.delay)

    def ping(self):
        return self._call("GET", self.base)

    def list_issues(self):
        out, page = [], 1
        while True:
            batch = self._call("GET", "{}/issues?state=all&per_page=100&page={}".format(self.base, page))
            if not batch:
                break
            out.extend(i for i in batch if "pull_request" not in i)
            if len(batch) < 100:
                break
            page += 1
        return out

    def ensure_label(self, name):
        if self.dry:
            return
        try:
            self._call("POST", self.base + "/labels", {"name": name, "color": label_color(name)})
        except GitHubError as e:
            if e.status != 422:  # 422 == already exists
                raise

    def create_issue(self, title, body, labels):
        self._pause()
        return self._call("POST", self.base + "/issues", {"title": title, "body": body, "labels": labels})

    def update_issue(self, number, title, body, labels):
        self._pause()
        return self._call("PATCH", "{}/issues/{}".format(self.base, number),
                          {"title": title, "body": body, "labels": labels})

    def set_state(self, number, state):
        self._pause()
        return self._call("PATCH", "{}/issues/{}".format(self.base, number), {"state": state})


# ---------------------------------------------------------------- sync
def index_issues(issues):
    by_num, by_marker, by_norm = {}, {}, {}
    for i in issues:
        by_num[i["number"]] = i
        m = MARKER_RE.search(i.get("body") or "")
        if m:
            by_marker[m.group(1)] = i
        n = norm(i.get("title") or "")
        by_norm.setdefault(n, i)
    return by_num, by_marker, by_norm


def link_issue(card, by_num, by_marker, by_norm):
    if card.get("issue") and card["issue"] in by_num:
        return by_num[card["issue"]]
    if card["id"] in by_marker:
        return by_marker[card["id"]]
    return by_norm.get(norm(card["title"]))


def same_labels(a, b):
    return sorted(a) == sorted(b)


def run_sync(cards, snapshot, gh, mode="sync", dry=False, log=print):
    issues = gh.list_issues()
    log("  {} issue(s) on the repo.".format(len(issues)))
    by_num, by_marker, by_norm = index_issues(issues)

    if mode != "pull":
        want = set()
        for c in cards:
            want.update(labels_for(c))
        for l in sorted(want):
            gh.ensure_label(l)

    stat = dict(created=0, updated=0, closed=0, reopened=0, pulled=0, adopted=0, conflicts=0)
    new_snap = {}

    for c in cards:
        iss = link_issue(c, by_num, by_marker, by_norm)
        board_done = c["col"] == "done"

        # ---- create ----
        if iss is None:
            if mode == "pull":
                new_snap[c["id"]] = {"done": board_done, "issue": None}
                continue
            log("CREATE  {}  [{}]".format(c["id"], c["col"]))
            if not dry:
                created = gh.create_issue(push_title(c["title"]), body_for(c), labels_for(c))
                c["issue"] = created["number"]
                c["assignee"], c["comments"] = None, 0
                if board_done:
                    gh.set_state(created["number"], "closed"); stat["closed"] += 1
            stat["created"] += 1
            new_snap[c["id"]] = {"done": board_done, "issue": c.get("issue")}
            continue

        c["issue"] = iss["number"]
        gh_done = iss["state"] == "closed"
        if not MARKER_RE.search(iss.get("body") or ""):
            stat["adopted"] += 1
        prev = snapshot.get(c["id"], {}).get("done") if c["id"] in snapshot else None

        # ---- reconcile the done<->open bit ----
        if mode == "push":
            final_done = board_done
            if board_done != gh_done:
                _push_state(gh, iss["number"], board_done, c["id"], "push", dry, log, stat)
        elif mode == "pull":
            final_done = gh_done
            if gh_done != board_done:
                _move_card(c, gh_done); stat["pulled"] += 1
                log("PULL    #{} {} -> {} (github)".format(iss["number"], c["id"], c["col"]))
        else:
            action, final_done = reconcile(prev, board_done, gh_done)
            if action in ("close", "reopen"):
                _push_state(gh, iss["number"], board_done, c["id"], "board", dry, log, stat)
            elif action in ("pull_done", "pull_reopen"):
                _move_card(c, gh_done); stat["pulled"] += 1
                log("PULL    #{} {} -> {} (github)".format(iss["number"], c["id"], c["col"]))
            elif action == "conflict":
                stat["conflicts"] += 1
                log("CONFLICT #{} {}: board={} github={} -> keeping BOARD".format(
                    iss["number"], c["id"], board_done, gh_done))
                _push_state(gh, iss["number"], board_done, c["id"], "conflict", dry, log, stat)

        # ---- push content (board authoritative) ----
        if mode != "pull":
            wt, wb, wl = push_title(c["title"]), body_for(c), labels_for(c)
            cur = [x["name"] for x in (iss.get("labels") or [])]
            if iss.get("title") != wt or iss.get("body") != wb or not same_labels(cur, wl):
                log("UPDATE  #{} {}".format(iss["number"], c["id"]))
                if not dry:
                    gh.update_issue(iss["number"], wt, wb, wl)
                stat["updated"] += 1

        # ---- pull display fields ----
        if mode != "push":
            a = iss.get("assignee")
            c["assignee"] = a["login"] if a else None
            c["comments"] = int(iss.get("comments") or 0)

        new_snap[c["id"]] = {"done": final_done, "issue": c["issue"]}

    return stat, new_snap


def _push_state(gh, number, board_done, cid, why, dry, log, stat):
    if board_done:
        log("CLOSE   #{} {} ({})".format(number, cid, why))
        if not dry:
            gh.set_state(number, "closed")
        stat["closed"] += 1
    else:
        log("REOPEN  #{} {} ({})".format(number, cid, why))
        if not dry:
            gh.set_state(number, "open")
        stat["reopened"] += 1


def _move_card(card, gh_done):
    if gh_done:
        if card["col"] != "done":
            card["activeCol"] = card["col"]
        card["col"] = "done"
    else:
        card["col"] = card.get("activeCol") or "ready"


# ---------------------------------------------------------------- board regen
def regen_board(cards, template_path, out_path):
    tpl = Path(template_path).read_text(encoding="utf-8")
    payload = json.dumps(cards, ensure_ascii=False, indent=2).replace("</", "<\\/")
    Path(out_path).write_text(tpl.replace("__CARDS_JSON__", payload), encoding="utf-8")


# ---------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description="Two-way board <-> GitHub issues bridge.")
    ap.add_argument("--owner", default="4laric")
    ap.add_argument("--repo", default="er-archipelago")
    ap.add_argument("--mode", choices=["sync", "push", "pull"], default="sync")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-regen", action="store_true")
    ap.add_argument("--board-out", default="")
    ap.add_argument("--delay-ms", type=int, default=600)
    ap.add_argument("--self-test", action="store_true", help="run offline logic tests and exit")
    args = ap.parse_args(argv)

    here = Path(__file__).resolve().parent
    if args.self_test:
        import test_sync_board
        return test_sync_board.run()

    cards_path = here / "cards.json"
    tpl_path = here / "board.template.html"
    snap_path = here / ".sync-snapshot.json"
    board_out = args.board_out or (here / "er-archipelago-kanban.html")

    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Set GH_TOKEN to a token with 'repo' scope first.")

    cards = json.loads(cards_path.read_text(encoding="utf-8"))
    snapshot = json.loads(snap_path.read_text(encoding="utf-8")) if snap_path.exists() else {}

    gh = GitHub(args.owner, args.repo, token, delay=args.delay_ms / 1000.0, dry=args.dry_run)
    try:
        gh.ping()
    except GitHubError as e:
        sys.exit("Cannot reach {}/{} - {}".format(args.owner, args.repo, e))

    print("Fetching issues...")
    stat, new_snap = run_sync(cards, snapshot, gh, mode=args.mode, dry=args.dry_run)

    if not args.dry_run:
        cards_path.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        snap_path.write_text(json.dumps(new_snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.no_regen:
        regen_board(cards, tpl_path, board_out)
        print("Regenerated {}".format(board_out))

    tag = " (DRY RUN - nothing written)" if args.dry_run else ""
    print("\nDone{}. created={created} updated={updated} closed={closed} reopened={reopened} "
          "pulled={pulled} adopted={adopted} conflicts={conflicts}".format(tag, **stat))
    if stat["conflicts"]:
        print("Review the CONFLICT lines above - the board value was kept.")


if __name__ == "__main__":
    main()
