#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patch_client_natural_triggers.py

Goal
----
Bloom a region's apparatus (graces + open flag + reveal flags + notify item)
when a DISJUNCTION of VANILLA triggers is satisfied, instead of when a
synthetic lock item is received. This lets "natural" keys (vanilla medallions,
vanilla event flags) gate a region without a dedicated AP lock item.

Slot-data schema (emitted by the apworld; tolerant if absent on older seeds):

    "naturalKeyTriggers": {
        "<LockName>": {
            "anyOf": [
                { "items": ["<item name>", ...], "flags": [<uint32 flag>, ...] },
                ...
            ]
        }
    }

Semantics:
  * A CLAUSE is satisfied when ALL its "items" have been received (by item
    NAME) AND ALL its "flags" return true from GetEventFlagState.
  * The trigger FIRES when ANY clause is satisfied (OR over clauses).
  * On first satisfaction (guarded on the region's open flag not yet set),
    BLOOM: push that lock's regionGraces[name] + regionOpenFlags[name] +
    lockRevealFlags[name] onto pendingGraceFlags, and queue lockNotifyItems[name]
    onto pendingNotifyGrants if present.
  * The open flag (save-persisted via SetEventFlag) doubles as the once-latch,
    so re-blooming is naturally skipped.

This reuses the SAME data tables the synthetic-lock path already populates
(regionGraces / regionOpenFlags / lockRevealFlags / lockNotifyItems), so the
apworld can express a lock as "natural-trigger" simply by adding a
naturalKeyTriggers entry instead of emitting a lock ITEM.

Touches three files (all additive):
  1. Core.h                  -- NKClause struct + naturalKeyTriggers + receivedItemNames members
  2. ArchipelagoInterface.cpp -- parse naturalKeyTriggers + maintain receivedItemNames
  3. Core.cpp                 -- EvaluateNaturalKeyTriggers() decl + def + call in settled poll

Conventions
-----------
* CRLF source; read as text in Python, back up to <file>.bak_<tag>, assert each
  anchor, .replace(), write back preserving newlines.
* Idempotent per file: a marker check skips an already-patched file.

Judgment calls / risks (see report):
* receivedItemNames is rebuilt from the items_received REPLAY on reconnect
  (items_handling 0b111 re-delivers the full stream), so it does NOT need
  separate persistence -- the open flag is the durable latch. If a clause is
  ITEM-only (no flags) and an item somehow were NOT replayed, the bloom could
  re-evaluate; but the open-flag guard makes a SECOND bloom a no-op anyway, and
  SetEventFlag is idempotent. We therefore do NOT add a persisted "bloomed" set.
* Flag reads (GetEventFlagState) happen ONLY inside the settled
  InventoryInstance()!=0 poll block, never mid-init (crash-on-load safety).
* Ordering: EvaluateNaturalKeyTriggers() runs immediately AFTER
  FlushPendingGraceFlags() in the same settled tick, so flags it pushes are
  flushed on the NEXT tick (one-tick latency, same as every other queued flag).
"""

import os
import sys

TAG = "natural_triggers"

CLIENT_DIR = r"C:\Users\alari\Documents\er-archipelago\Dark-Souls-III-Archipelago-client\archipelago-client"
CORE_H   = os.path.join(CLIENT_DIR, "Core.h")
IFACE    = os.path.join(CLIENT_DIR, "ArchipelagoInterface.cpp")
CORE_CPP = os.path.join(CLIENT_DIR, "Core.cpp")


# =====================================================================
# Generic CRLF-tolerant helpers
# =====================================================================
def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def backup(path, text):
    bak = path + ".bak_" + TAG
    if not os.path.exists(bak):
        write_text(bak, text)
        print("  backup written: {}".format(bak))
    else:
        print("  backup already exists: {}".format(bak))


def crlf_variants(s_crlf):
    """Return (crlf, lf) variants of a CRLF-authored string."""
    return s_crlf, s_crlf.replace("\r\n", "\n")


def insert_after(text, anchor_crlf, insert_crlf, what):
    """Insert insert_crlf right after anchor (matching newline style). Returns new text."""
    a_crlf, a_lf = crlf_variants(anchor_crlf)
    i_crlf, i_lf = crlf_variants(insert_crlf)
    if a_crlf in text:
        anchor, ins = a_crlf, i_crlf
    elif a_lf in text:
        anchor, ins = a_lf, i_lf
    else:
        raise RuntimeError("Anchor not found ({}). Aborting.".format(what))
    new_text = text.replace(anchor, anchor + ins, 1)
    if new_text == text:
        raise RuntimeError("replace() made no change for {} despite anchor match.".format(what))
    return new_text


# =====================================================================
# 1) Core.h  -- struct + members
# =====================================================================
COREH_MARKER = "naturalKeyTriggers"

# Anchor: the regionOpenFlags member declaration block (a stable, unique member
# in the slot-data map region). We insert the new struct + members right after it.
COREH_ANCHOR = (
    "\tstd::unordered_map<std::string, uint32_t> regionOpenFlags;\r\n"
)

COREH_INSERT = (
    "\r\n"
    "\t// Natural-key triggers (slot_data \"naturalKeyTriggers\"; SPEC-natural-locks.md): bloom a\r\n"
    "\t// region's apparatus when a DISJUNCTION of vanilla triggers is satisfied, instead of when\r\n"
    "\t// a synthetic lock ITEM arrives. LockName -> list of clauses; a clause is satisfied when\r\n"
    "\t// ALL its items were received (by NAME, via receivedItemNames) AND ALL its flags are set\r\n"
    "\t// (GetEventFlagState). ANY satisfied clause fires the bloom (push regionGraces/\r\n"
    "\t// regionOpenFlags/lockRevealFlags + lockNotifyItems for that LockName). The open flag is\r\n"
    "\t// the save-persisted once-latch. Evaluated in CCore::EvaluateNaturalKeyTriggers on a\r\n"
    "\t// settled in-world tick. Absent/empty on seeds that don't use natural keys.\r\n"
    "\tstruct NKClause { std::vector<std::string> items; std::vector<uint32_t> flags; };\r\n"
    "\tstd::unordered_map<std::string, std::vector<NKClause>> naturalKeyTriggers;\r\n"
    "\t// Item NAMES received this session (maintained in the received-items handler). Rebuilt\r\n"
    "\t// from the items_received replay on reconnect (items_handling 0b111 re-delivers all),\r\n"
    "\t// so no separate persistence is needed; the region open flag is the durable latch.\r\n"
    "\tstd::unordered_set<std::string> receivedItemNames;\r\n"
)


def patch_coreh():
    print("[Core.h]")
    text = read_text(CORE_H)
    if COREH_MARKER in text:
        print("  already applied: {} present".format(COREH_MARKER))
        return
    backup(CORE_H, text)
    new_text = insert_after(text, COREH_ANCHOR, COREH_INSERT, "Core.h regionOpenFlags member")
    write_text(CORE_H, new_text)
    print("  + struct NKClause, naturalKeyTriggers, receivedItemNames")


# =====================================================================
# 2) ArchipelagoInterface.cpp -- parse + maintain receivedItemNames
# =====================================================================
IFACE_PARSE_MARKER = "naturalKeyTriggers"

# (a) Parse: insert right after the regionOpenFlags parse block in slot-data handler.
IFACE_PARSE_ANCHOR = (
    "\t\tCore->regionOpenFlags.clear();\r\n"
    "\t\tif (data.contains(\"regionOpenFlags\")) {\r\n"
    "\t\t\tdata.at(\"regionOpenFlags\").get_to(Core->regionOpenFlags);\r\n"
    "\t\t\tif (!Core->regionOpenFlags.empty()) {\r\n"
    "\t\t\t\tspdlog::info(\"Region-open flags: {} region(s) will open on lock-item receipt\",\r\n"
    "\t\t\t\t\tCore->regionOpenFlags.size());\r\n"
    "\t\t\t}\r\n"
    "\t\t}\r\n"
)

IFACE_PARSE_INSERT = (
    "\r\n"
    "\t\t// Natural-key triggers (SPEC-natural-locks.md): tolerant parse -- older seeds omit the key.\r\n"
    "\t\t// LockName -> { \"anyOf\": [ {\"items\":[...],\"flags\":[...]}, ... ] }. A clause is satisfied\r\n"
    "\t\t// when all items were received AND all flags are set; ANY clause blooms the region. Reuses\r\n"
    "\t\t// the existing regionGraces/regionOpenFlags/lockRevealFlags/lockNotifyItems tables for the\r\n"
    "\t\t// bloom effect (see CCore::EvaluateNaturalKeyTriggers).\r\n"
    "\t\tCore->naturalKeyTriggers.clear();\r\n"
    "\t\tif (data.contains(\"naturalKeyTriggers\")) {\r\n"
    "\t\t\tfor (auto& kv : data.at(\"naturalKeyTriggers\").items()) {\r\n"
    "\t\t\t\tstd::vector<CCore::NKClause> clauses;\r\n"
    "\t\t\t\tif (kv.value().contains(\"anyOf\")) {\r\n"
    "\t\t\t\t\tfor (auto& c : kv.value().at(\"anyOf\")) {\r\n"
    "\t\t\t\t\t\tCCore::NKClause cl;\r\n"
    "\t\t\t\t\t\tif (c.contains(\"items\")) for (auto& it : c.at(\"items\")) cl.items.push_back(it.get<std::string>());\r\n"
    "\t\t\t\t\t\tif (c.contains(\"flags\")) for (auto& fl : c.at(\"flags\")) cl.flags.push_back(fl.get<uint32_t>());\r\n"
    "\t\t\t\t\t\tclauses.push_back(std::move(cl));\r\n"
    "\t\t\t\t\t}\r\n"
    "\t\t\t\t}\r\n"
    "\t\t\t\tCore->naturalKeyTriggers[kv.key()] = std::move(clauses);\r\n"
    "\t\t\t}\r\n"
    "\t\t\tif (!Core->naturalKeyTriggers.empty())\r\n"
    "\t\t\t\tspdlog::info(\"Natural-key triggers: {} region(s) bloom on vanilla trigger disjunction\",\r\n"
    "\t\t\t\t\tCore->naturalKeyTriggers.size());\r\n"
    "\t\t}\r\n"
)

# (b) Maintain receivedItemNames: insert at the TOP of the per-item handling, right
# after itemname/sender/location are computed and the log line is emitted.
IFACE_RECV_ANCHOR = (
    "\t\t\tspdlog::info(\"#{}: {} from {} - {}\", item.index, itemname, sender, location);\r\n"
)

IFACE_RECV_INSERT = (
    "\r\n"
    "\t\t\t// Maintain the received-NAME set for natural-key trigger evaluation. Rebuilt from the\r\n"
    "\t\t\t// items_received replay on reconnect (items_handling 0b111), so it needs no persistence.\r\n"
    "\t\t\tCore->receivedItemNames.insert(itemname);\r\n"
)


def patch_iface():
    print("[ArchipelagoInterface.cpp]")
    text = read_text(IFACE)
    if IFACE_PARSE_MARKER in text:
        print("  already applied: {} present".format(IFACE_PARSE_MARKER))
        return
    backup(IFACE, text)
    text = insert_after(text, IFACE_PARSE_ANCHOR, IFACE_PARSE_INSERT, "Iface regionOpenFlags parse block")
    text = insert_after(text, IFACE_RECV_ANCHOR, IFACE_RECV_INSERT, "Iface received-item log line")
    write_text(IFACE, text)
    print("  + naturalKeyTriggers parse, receivedItemNames.insert")


# =====================================================================
# 3) Core.cpp -- decl + def + call
# =====================================================================
CORECPP_MARKER = "EvaluateNaturalKeyTriggers"

# (a) Header decl: add to Core.h next to FlushPendingGraceFlags decl. (Done in Core.h
#     pass below by a second insert -- but the decl lives in Core.h's private section,
#     so we add it here in the Core.cpp pass via a dedicated Core.h edit to keep the
#     def + decl together.)
COREH_DECL_ANCHOR = (
    "\tstd::unordered_set<uint32_t> graceFlagsSetThisSession;\r\n"
    "\tVOID FlushPendingGraceFlags();\r\n"
)
COREH_DECL_INSERT = (
    "\r\n"
    "\t// Natural-key triggers (SPEC-natural-locks.md): on a settled in-world tick, evaluate each\r\n"
    "\t// naturalKeyTriggers entry; when ANY clause is satisfied (all items received AND all flags\r\n"
    "\t// set) and the region's open flag is not yet set, bloom that region (push graces/open/reveal\r\n"
    "\t// flags + notify item). The open flag is the once-latch. Flag reads only happen here, never\r\n"
    "\t// mid-init. Called right after FlushPendingGraceFlags in the settled poll block.\r\n"
    "\tVOID EvaluateNaturalKeyTriggers();\r\n"
)

# (b) Call site: right after FlushPendingGraceFlags() in the settled poll block.
CORECPP_CALL_ANCHOR = (
    "\t\t\tFlushPendingGraceFlags();\r\n"
)
CORECPP_CALL_INSERT = (
    "\r\n"
    "\t\t\t// Natural-key triggers: bloom regions whose vanilla trigger disjunction is now satisfied.\r\n"
    "\t\t\t// MUST be inside this settled (InventoryInstance()!=0) block -- it reads event flags.\r\n"
    "\t\t\tEvaluateNaturalKeyTriggers();\r\n"
)

# (c) Definition: insert right after the FlushPendingGraceFlags() definition's closing brace.
CORECPP_DEF_ANCHOR = (
    "\tpendingGraceFlags.swap(retry);\r\n"
    "\tif (setCount > 0) {\r\n"
    "\t\tspdlog::info(\"Region fusion: set {} grace warp flag(s) ({} pending)\", setCount, pendingGraceFlags.size());\r\n"
    "\t}\r\n"
    "}\r\n"
)
CORECPP_DEF_INSERT = (
    "\r\n"
    "// Natural-key triggers (SPEC-natural-locks.md): a region blooms when a DISJUNCTION of vanilla\r\n"
    "// triggers is satisfied, instead of when a synthetic lock item arrives. For each lock, a clause\r\n"
    "// is satisfied when ALL its items were received (by NAME) AND ALL its flags are set; ANY clause\r\n"
    "// fires the bloom. The region open flag (save-persisted via SetEventFlag in FlushPendingGraceFlags)\r\n"
    "// doubles as the once-latch -- once set, the guard below skips the lock forever, so re-blooming on\r\n"
    "// reconnect/replay is a no-op. Called ONLY from the settled InventoryInstance()!=0 poll block, so\r\n"
    "// GetEventFlagState is always valid (never mid-init). The bloom pushes flags onto pendingGraceFlags\r\n"
    "// (flushed next tick) + lockNotifyItems onto pendingNotifyGrants, exactly like the lock-item path.\r\n"
    "VOID CCore::EvaluateNaturalKeyTriggers() {\r\n"
    "\tif (naturalKeyTriggers.empty()) return;\r\n"
    "\tfor (const auto& nk : naturalKeyTriggers) {\r\n"
    "\t\tconst std::string& name = nk.first;\r\n"
    "\t\tconst std::vector<NKClause>& clauses = nk.second;\r\n"
    "\t\t// Guard: skip if this region has no open flag, or its open flag is already set (latch).\r\n"
    "\t\tauto openIt = regionOpenFlags.find(name);\r\n"
    "\t\tif (openIt == regionOpenFlags.end()) continue;\r\n"
    "\t\tif (er_ap::game::GetEventFlagState(openIt->second)) continue;  // already bloomed (latch)\r\n"
    "\t\t// Any clause satisfied? (all items received AND all flags set)\r\n"
    "\t\tbool fired = false;\r\n"
    "\t\tfor (const auto& cl : clauses) {\r\n"
    "\t\t\tbool ok = true;\r\n"
    "\t\t\tfor (const std::string& nm : cl.items) {\r\n"
    "\t\t\t\tif (!receivedItemNames.count(nm)) { ok = false; break; }\r\n"
    "\t\t\t}\r\n"
    "\t\t\tif (ok) {\r\n"
    "\t\t\t\tfor (uint32_t fl : cl.flags) {\r\n"
    "\t\t\t\t\tif (!er_ap::game::GetEventFlagState(fl)) { ok = false; break; }\r\n"
    "\t\t\t\t}\r\n"
    "\t\t\t}\r\n"
    "\t\t\tif (ok) { fired = true; break; }\r\n"
    "\t\t}\r\n"
    "\t\tif (!fired) continue;\r\n"
    "\t\t// BLOOM: queue this region's grace + open + reveal flags onto pendingGraceFlags (flushed\r\n"
    "\t\t// next tick by FlushPendingGraceFlags -> SetEventFlag), and its notify item if present.\r\n"
    "\t\tint queued = 0;\r\n"
    "\t\tauto graceIt = regionGraces.find(name);\r\n"
    "\t\tif (graceIt != regionGraces.end())\r\n"
    "\t\t\tfor (uint32_t fl : graceIt->second) { pendingGraceFlags.push_back(fl); ++queued; }\r\n"
    "\t\tpendingGraceFlags.push_back(openIt->second); ++queued;  // open flag = latch + fog gate cond\r\n"
    "\t\tauto revealIt = lockRevealFlags.find(name);\r\n"
    "\t\tif (revealIt != lockRevealFlags.end())\r\n"
    "\t\t\tfor (int32_t fl : revealIt->second) { pendingGraceFlags.push_back((uint32_t)fl); ++queued; }\r\n"
    "\t\tauto notifyIt = lockNotifyItems.find(name);\r\n"
    "\t\tif (notifyIt != lockNotifyItems.end())\r\n"
    "\t\t\tpendingNotifyGrants.push_back(notifyIt->second);\r\n"
    "\t\tspdlog::info(\"Natural-key '{}' satisfied: bloomed region ({} flag(s) queued)\", name, queued);\r\n"
    "\t}\r\n"
    "}\r\n"
)


def patch_corecpp():
    print("[Core.cpp]")
    text = read_text(CORE_CPP)
    if CORECPP_MARKER in text:
        print("  already applied: {} present".format(CORECPP_MARKER))
        return
    backup(CORE_CPP, text)
    text = insert_after(text, CORECPP_CALL_ANCHOR, CORECPP_CALL_INSERT, "Core.cpp FlushPendingGraceFlags() call site")
    text = insert_after(text, CORECPP_DEF_ANCHOR, CORECPP_DEF_INSERT, "Core.cpp FlushPendingGraceFlags() definition end")
    write_text(CORE_CPP, text)
    print("  + EvaluateNaturalKeyTriggers call + definition")


def patch_coreh_decl():
    """Second Core.h edit: add the EvaluateNaturalKeyTriggers private decl next to
    FlushPendingGraceFlags decl. Separate from patch_coreh's marker so it is its own
    idempotent unit (keyed on the decl text)."""
    print("[Core.h decl]")
    text = read_text(CORE_H)
    if "VOID EvaluateNaturalKeyTriggers();" in text:
        print("  already applied: EvaluateNaturalKeyTriggers decl present")
        return
    # No separate backup -- patch_coreh already backed Core.h up this run; but guard
    # in case patch_coreh was skipped (marker present) yet decl is missing.
    backup(CORE_H, text)
    new_text = insert_after(text, COREH_DECL_ANCHOR, COREH_DECL_INSERT, "Core.h FlushPendingGraceFlags decl")
    write_text(CORE_H, new_text)
    print("  + EvaluateNaturalKeyTriggers() decl")


def main():
    for p in (CORE_H, IFACE, CORE_CPP):
        if not os.path.isfile(p):
            print("ERROR: target not found: {}".format(p))
            return 1
    patch_coreh()
    patch_coreh_decl()
    patch_iface()
    patch_corecpp()
    print("done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
