#!/usr/bin/env python3
"""Offline tests for sync_board.py. No network - GitHub is mocked. Run: python sync_board.py --self-test"""
import json
import tempfile
from pathlib import Path

import sync_board as S


class FakeGitHub:
    """In-memory GitHub: records calls, simulates an issue store."""
    def __init__(self, issues=None, delay=0, dry=False):
        self.issues = {i["number"]: i for i in (issues or [])}
        self._next = (max(self.issues) if self.issues else 0) + 1
        self.dry = dry
        self.calls = []

    def ping(self):
        return {}

    def list_issues(self):
        return [dict(i) for i in self.issues.values()]

    def ensure_label(self, name):
        self.calls.append(("label", name))

    def create_issue(self, title, body, labels):
        n = self._next; self._next += 1
        self.issues[n] = {"number": n, "title": title, "body": body,
                          "labels": [{"name": x} for x in labels], "state": "open",
                          "assignee": None, "comments": 0}
        self.calls.append(("create", n, title, tuple(labels)))
        return {"number": n}

    def update_issue(self, number, title, body, labels):
        i = self.issues[number]
        i.update(title=title, body=body, labels=[{"name": x} for x in labels])
        self.calls.append(("update", number))

    def set_state(self, number, state):
        self.issues[number]["state"] = state
        self.calls.append(("state", number, state))


FAILED = []
def check(name, cond):
    print(("  PASS " if cond else "  FAIL ") + name)
    if not cond:
        FAILED.append(name)


def issue(number, title, body="", state="open", labels=None, assignee=None, comments=0):
    return {"number": number, "title": title, "body": body, "state": state,
            "labels": [{"name": x} for x in (labels or [])], "assignee": assignee, "comments": comments}


def run():
    print("reconcile table:")
    table = [
        # (prev, board_done, gh_done) -> (action, final)
        ((None, False, False), ("none", False)),
        ((None, True,  False), ("close", True)),
        ((None, False, True ), ("reopen", False)),
        ((False, False, False), ("none", False)),
        ((False, True,  False), ("close", True)),      # board marked done -> close issue
        ((False, False, True ), ("pull_done", True)),  # contributor closed -> card to done
        ((False, True,  True ), ("none", True)),        # both moved to done, agree
        ((True, True,  False), ("pull_reopen", False)),# contributor reopened -> card active
        ((True, False, True ), ("reopen", False)),      # board moved out of done -> reopen
        ((True, False, False), ("none", False)),
        ((True, True,  True ), ("none", True)),
    ]
    for (args, want) in table:
        got = S.reconcile(*args)
        check("reconcile{} == {}".format(args, want), got == want)

    print("helpers:")
    check("norm strips emoji+lower", S.norm("⭐⭐ v0.2 - SHIPPED") == "v0.2 - shipped")
    check("push_title keeps case", S.push_title("\U0001f9f9 Remove the guard") == "Remove the guard")
    c = {"id": "x", "col": "ready", "pri": "P1", "cat": "Region Locks", "desc": "d"}
    check("labels_for active", S.labels_for(c) == ["P1", "area:region-locks", "status:ready"])
    c2 = {"id": "y", "col": "done", "pri": "P2", "cat": "Shops", "desc": "d"}
    check("labels_for done (no status)", S.labels_for(c2) == ["P2", "area:shops"])
    check("body_for has marker", "<!-- card:x -->" in S.body_for(c))

    print("scenario: fresh repo -> create all, done card closed")
    cards = [
        {"id": "a", "col": "ready", "pri": "P1", "cat": "Shops", "title": "⭐ Alpha", "desc": "aa",
         "issue": None, "assignee": None, "comments": 0, "activeCol": None},
        {"id": "b", "col": "done", "pri": "P2", "cat": "Data", "title": "Beta", "desc": "bb",
         "issue": None, "assignee": None, "comments": 0, "activeCol": None},
    ]
    gh = FakeGitHub()
    stat, snap = S.run_sync(cards, {}, gh, mode="sync", log=lambda *a: None)
    check("2 created", stat["created"] == 2)
    check("done card closed", stat["closed"] == 1 and gh.issues[cards[1]["issue"]]["state"] == "closed")
    check("labels sent are per-card (not the whole array)",
          any(k == ("create",) or (k[0] == "create" and k[3] == ("P1", "area:shops", "status:ready")) for k in gh.calls))
    check("card 'a' linked to a number", isinstance(cards[0]["issue"], int))
    check("snapshot records done bits", snap["a"]["done"] is False and snap["b"]["done"] is True)

    print("scenario: adopt pre-existing issues by title (no marker), stamp marker via update")
    cards = [{"id": "a", "col": "ready", "pri": "P1", "cat": "Shops", "title": "⭐ Alpha", "desc": "aa",
              "issue": None, "assignee": None, "comments": 0, "activeCol": None}]
    gh = FakeGitHub([issue(7, "Alpha", body="old body no marker", labels=["P1"])])
    stat, snap = S.run_sync(cards, {}, gh, mode="sync", log=lambda *a: None)
    check("adopted, not created", stat["created"] == 0 and cards[0]["issue"] == 7)
    check("counted as adopted", stat["adopted"] == 1)
    check("content updated (marker added)", stat["updated"] == 1 and "<!-- card:a -->" in gh.issues[7]["body"])

    print("scenario: pull - contributor closed an issue -> card moves to Done")
    cards = [{"id": "a", "col": "ready", "pri": "P1", "cat": "Shops", "title": "Alpha", "desc": "aa",
              "issue": 7, "assignee": None, "comments": 0, "activeCol": None}]
    gh = FakeGitHub([issue(7, "Alpha", body="b <!-- card:a -->", state="closed",
                           labels=["P1", "area:shops", "status:ready"], assignee={"login": "mop"}, comments=3)])
    stat, snap = S.run_sync(cards, {"a": {"done": False, "issue": 7}}, gh, mode="sync", log=lambda *a: None)
    check("card moved to done", cards[0]["col"] == "done" and cards[0]["activeCol"] == "ready")
    check("assignee + comments pulled", cards[0]["assignee"] == "mop" and cards[0]["comments"] == 3)
    check("pulled counted", stat["pulled"] == 1)

    print("scenario: push - board marked a card Done -> issue closes")
    cards = [{"id": "a", "col": "done", "pri": "P1", "cat": "Shops", "title": "Alpha", "desc": "aa",
              "issue": 7, "assignee": None, "comments": 0, "activeCol": "ready"}]
    gh = FakeGitHub([issue(7, "Alpha", body="b <!-- card:a -->", state="open",
                           labels=["P1", "area:shops", "status:ready"])])
    stat, snap = S.run_sync(cards, {"a": {"done": False, "issue": 7}}, gh, mode="sync", log=lambda *a: None)
    check("issue closed by board change", gh.issues[7]["state"] == "closed" and stat["closed"] == 1)

    print("scenario: no-op - board and github agree, nothing written")
    cards = [{"id": "a", "col": "done", "pri": "P1", "cat": "Shops", "title": "Alpha", "desc": "aa",
              "issue": 7, "assignee": None, "comments": 0, "activeCol": "ready"}]
    body = S.body_for(cards[0])
    gh = FakeGitHub([issue(7, S.push_title("Alpha"), body=body, state="closed",
                           labels=["P1", "area:shops"])])
    stat, snap = S.run_sync(cards, {"a": {"done": True, "issue": 7}}, gh, mode="sync", log=lambda *a: None)
    writes = [c for c in gh.calls if c[0] in ("create", "update", "state")]
    check("idempotent: zero writes on a clean sync", writes == [])

    print("scenario: dry-run makes no writes")
    cards = [{"id": "z", "col": "ready", "pri": "P3", "cat": "Data", "title": "New", "desc": "d",
              "issue": None, "assignee": None, "comments": 0, "activeCol": None}]
    gh = FakeGitHub(dry=True)
    stat, snap = S.run_sync(cards, {}, gh, mode="sync", dry=True, log=lambda *a: None)
    check("dry-run: create planned but no store write", stat["created"] == 1 and len(gh.issues) == 0)

    print("regen_board:")
    with tempfile.TemporaryDirectory() as d:
        tpl = Path(d) / "t.html"
        tpl.write_text("<script>const CARDS = __CARDS_JSON__;</script>", encoding="utf-8")
        out = Path(d) / "o.html"
        S.regen_board([{"id": "a", "col": "ready", "pri": "P1", "cat": "X", "title": "T", "desc": "</script> trick"}],
                      str(tpl), str(out))
        html = out.read_text(encoding="utf-8")
        check("placeholder consumed", "__CARDS_JSON__" not in html)
        check("no raw </script> breakout in payload", "</script> trick" not in html and "<\\/script> trick" in html)

    print("local (board-only) cards:")
    local_card = {"id": "done-archive-pointer", "col": "done", "pri": "P3", "cat": "Infra",
                  "title": "Completed work archived", "desc": "signpost, not work", "local": True}
    real_card = {"id": "real-work", "col": "ready", "pri": "P1", "cat": "Infra",
                 "title": "Real work", "desc": "d"}

    gh = FakeGitHub([])
    stat, snap = S.run_sync([dict(local_card), dict(real_card)], {}, gh, log=lambda *a: None)
    created = [c for c in gh.calls if c[0] == "create"]
    check("local card creates no issue", len(created) == 1 and created[0][2] == "Real work")
    check("local card opens no state call", not [c for c in gh.calls if c[0] == "state"])
    check("local counted, not created", stat["local"] == 1 and stat["created"] == 1)
    check("local card still gets a snapshot row", snap["done-archive-pointer"]["issue"] is None)

    # BREAK THE FIX: without the flag the same card DOES create an issue (and closes it,
    # since it sits in Done) -- which is the noise the flag exists to prevent.
    unflagged = dict(local_card); unflagged.pop("local")
    gh2 = FakeGitHub([])
    S.run_sync([unflagged], {}, gh2, log=lambda *a: None)
    check("without the flag it creates AND closes (fix is load-bearing)",
          any(c[0] == "create" for c in gh2.calls) and any(c[0] == "state" and c[2] == "closed"
                                                           for c in gh2.calls))

    # A local card that already carries an issue must NOT be silently unlinked.
    linked = dict(local_card); linked["issue"] = 42
    gh3 = FakeGitHub([issue(42, "Completed work archived", "<!-- card:done-archive-pointer -->")])
    logged = []
    _, snap3 = S.run_sync([linked], {}, gh3, log=lambda m: logged.append(m))
    check("local card with an issue warns instead of orphaning",
          any("marked local but carries issue" in m for m in logged))
    check("local card with an issue leaves the issue untouched",
          not [c for c in gh3.calls if c[0] in ("update", "state")]
          and snap3["done-archive-pointer"]["issue"] == 42)

    print("")
    if FAILED:
        print("FAILED: {} test(s): {}".format(len(FAILED), ", ".join(FAILED)))
        return 1
    print("ALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
