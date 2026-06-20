#!/usr/bin/env python3
r"""
patch_client_global_scadu_blessing.py  (run on Windows, in the repo root)

P1 CLIENT half of SPEC-global-scadutree-blessing.md. DEFAULT OFF: does nothing unless
slot_data global_scadutree_blessing != off (see patch_apworld_global_scadu_blessing.py).

When enabled, on each in-world tick the client:
  1. counts held Scadutree Fragments (goods 2010000 stack quantity in the bag),
  2. converts that to a Scadutree Blessing combat level via the vanilla cost curve
     (cumulative [0,1,3,5,7,9,11,13,15,17,20,23,26,29,32,35,38,41,44,47,50]),
  3. writes the game's stored combat blessing byte at PlayerGameData + 0xFC
     (resolved from the Hexinton/TGA cheat table: GameDataMan -> +0x08 -> +0xFC),
so the DLC blessing buff applies in the BASE game. The engine recomputes the
20000100+N speffect from this stored byte on the next map load / grace rest.

Safety: only ever RAISES the stored level (never reduces), so it can't stomp a real
revered level in a DLC seed and never causes a transient down-flicker. Combat track
only (Alaric runs summons off). Reuses the auto_upgrade inventory-walk shape + the same
in-world settle gate, so it inherits the crash-on-load hardening.

Edits (idempotent, CRLF/LF-safe, makes .bak per file):
  - er_gamehook.h            : declare SetGlobalScaduBlessing / TickGlobalScaduBlessing
  - er_gamehook_win.cpp      : the global, setter, and TickGlobalScaduBlessing() impl
  - ArchipelagoInterface.cpp : parse the slot_data option
  - Core.cpp                 : call TickGlobalScaduBlessing() in the in-world poll
"""
import os, sys, shutil

REPO = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(REPO, "Dark-Souls-III-Archipelago-client", "archipelago-client")
HDR  = os.path.join(CLIENT, "er_gamehook.h")
WIN  = os.path.join(CLIENT, "er_gamehook_win.cpp")
IFACE = os.path.join(CLIENT, "ArchipelagoInterface.cpp")
CORE = os.path.join(CLIENT, "Core.cpp")


def load(path):
    if not os.path.isfile(path):
        sys.exit(f"ERROR: not found: {path}")
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def nl_of(text):
    return "\r\n" if "\r\n" in text else "\n"


def insert_after(text, anchor_line, new_lines, path):
    nl = nl_of(text)
    anchor = anchor_line + nl
    if text.count(anchor) != 1:
        sys.exit(f"ERROR in {os.path.basename(path)}: anchor not unique "
                 f"({text.count(anchor)}x): {anchor_line!r}")
    block = "".join(l + nl for l in new_lines)
    return text.replace(anchor, anchor + block, 1)


def insert_before(text, anchor_line, new_lines, path):
    nl = nl_of(text)
    anchor = anchor_line + nl
    if text.count(anchor) != 1:
        sys.exit(f"ERROR in {os.path.basename(path)}: anchor not unique "
                 f"({text.count(anchor)}x): {anchor_line!r}")
    block = "".join(l + nl for l in new_lines)
    return text.replace(anchor, block + anchor, 1)


def save(path, text):
    shutil.copy2(path, path + ".bak_globalscadu")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    with open(path, "r", encoding="utf-8", newline="") as f:
        if f.read() != text:
            sys.exit(f"ERROR: write-back mismatch on {path} (truncation?). Restore the .bak.")
    print(f"  patched: {os.path.relpath(path, REPO)}  (.bak_globalscadu written)")


# ---- er_gamehook.h : declarations (space-indented, col-0 decls) ------------------------
hdr = load(HDR)
if "SetGlobalScaduBlessing" in hdr:
    print("er_gamehook.h already declares SetGlobalScaduBlessing; skipping.")
else:
    hdr = insert_after(
        hdr,
        "void RefreshAutoUpgradeTargets();                                  // recompute targets from live inventory",
        [
            "",
            "// Global Scadutree Blessing (slot_data global_scadutree_blessing; SPEC-global-scadutree-blessing.md).",
            "// mode: 0=off, 1=player_only, 2=scaled. When != off, TickGlobalScaduBlessing() (called each in-world",
            "// tick from Core) counts held Scadutree Fragments, converts to a blessing level via the vanilla cost",
            "// curve, and RAISES the game's stored combat blessing byte (PlayerGameData +0xFC) so the DLC blessing",
            "// buff applies in the base game. Never reduces the stored level. Combat track only (v1).",
            "void SetGlobalScaduBlessing(int mode);",
            "void TickGlobalScaduBlessing();",
        ],
        HDR,
    )
    save(HDR, hdr)


# ---- er_gamehook_win.cpp : global + setter + impl (space-indented) ---------------------
win = load(WIN)
if "TickGlobalScaduBlessing" in win:
    print("er_gamehook_win.cpp already has TickGlobalScaduBlessing; skipping.")
else:
    impl = [
        "",
        "// ===== global Scadutree Blessing (slot_data global_scadutree_blessing) ======================",
        "// SPEC-global-scadutree-blessing.md (P1). Count held Scadutree Fragments -> blessing level via",
        "// the vanilla cost curve -> write the stored combat blessing byte at PlayerGameData + 0xFC so the",
        "// 20000100+N buff applies in the base game (the engine recomputes the speffect from this byte on",
        "// the next map load / grace rest). Offset from the Hexinton/TGA CE table: GameDataMan -> +0x08 ->",
        "// +0xFC (signed byte). NOTE: 0xFC is relative to the client's resolved `pgd`; this assumes the",
        "// client's pgd == the table's [GameDataMan+0x08]. If the buff never applies, verify that first.",
        "namespace {",
        "    int g_globalScaduBlessing = 0;   // 0=off, 1=player_only, 2=scaled",
        "    const uintptr_t kScaduCombatLevelOff = 0xFC;   // PlayerGameData + 0xFC (combat blessing, byte)",
        "    // cumulative Scadutree Fragments required to REACH each combat level (0..20):",
        "    const int kScaduCum[21] = {0,1,3,5,7,9,11,13,15,17,20,23,26,29,32,35,38,41,44,47,50};",
        "}",
        "",
        "// POD-only SEH write helper (keeps __try out of the spdlog-using tick fn; see SehReadI32).",
        "static inline bool SehWriteU8(void* p, uint8_t v) {",
        "    __try { *reinterpret_cast<volatile uint8_t*>(p) = v; return true; }",
        "    __except (EXCEPTION_EXECUTE_HANDLER) { return false; }",
        "}",
        "",
        "void SetGlobalScaduBlessing(int mode) {",
        "    g_globalScaduBlessing = (mode == 1 || mode == 2) ? mode : 0;",
        '    spdlog::info("global_scadu_blessing: {}", g_globalScaduBlessing ? "ENABLED" : "off");',
        "}",
        "",
        "void TickGlobalScaduBlessing() {",
        "    using namespace hooks;",
        "    if (!g_globalScaduBlessing) return;",
        "    if (!Ready() || !g_gameDataManPtrLoc) return;",
        "    // Throttle: this walks the bag; once a second is plenty for a stored-byte watchdog.",
        "    static uint64_t s_lastTick = 0;",
        "    uint64_t now = GetTickCount64();",
        "    if (s_lastTick != 0 && now - s_lastTick < 1000) return;",
        "    s_lastTick = now;",
        "",
        "    uintptr_t gdm = 0, pgd = 0;",
        "    if (!SafeRead(g_gameDataManPtrLoc, gdm) || gdm < 0x10000) return;",
        "    if (!SafeRead(gdm + GAMEDATAMAN_PGD_OFF, pgd) || pgd < 0x10000) return;",
        "",
        "    // Both AP fragment items ('Scadutree Fragment' / '... x2') share goods id 2010000, so the bag",
        "    // holds ONE stack whose quantity = total fragments. In the bag, goods carry the category nibble.",
        "    const uint32_t kFragFull = 2010000u | CATEGORY_GOODS;",
        "    int fragQty = 0; bool found = false;",
        "    int lo = (g_invContainerOff >= 0) ? g_invContainerOff : INV_SCAN_OFF_LO;",
        "    int hi = (g_invContainerOff >= 0) ? g_invContainerOff : (INV_SCAN_OFF_HI - 0x60);",
        "    for (int off = lo; off <= hi && !found; off += 8) {",
        "        uintptr_t cont = pgd + off; int32_t slotCount = 0;",
        "        if (!SafeRead(cont + INV_SLOTCOUNT_OFF, slotCount)) continue;",
        "        if (slotCount <= 0 || slotCount > INV_MAX_SLOTS) continue;",
        "        uintptr_t primary = 0, overflow = 0;",
        "        if (!SafeRead(cont + INV_PRIMARY_PTR_OFF, primary) || primary < 0x10000) continue;",
        "        if ((primary & 0x3) != 0) continue;",
        "        SafeRead(cont + INV_OVERFLOW_PTR_OFF, overflow);",
        "        const uintptr_t arrays[2] = { primary, overflow };",
        "        const int       counts[2] = { slotCount, INV_MAX_SLOTS };",
        "        for (int a = 0; a < 2 && !found; ++a) {",
        "            uintptr_t arr = arrays[a]; if (arr < 0x10000) continue;",
        "            size_t okEntries = SafeRegionLen(arr, (size_t)counts[a] * INV_ENTRY_STRIDE) / INV_ENTRY_STRIDE;",
        "            for (size_t i = 0; i < okEntries; ++i) {",
        "                const uint8_t* e = reinterpret_cast<const uint8_t*>(arr + i * INV_ENTRY_STRIDE);",
        "                int32_t itemId = 0, qty = 0;",
        "                if (!SehReadI32(e + INV_ENTRY_ID_OFF, itemId)) break;   // array freed mid-walk -> bail",
        "                if (static_cast<uint32_t>(itemId) != kFragFull) continue;",
        "                if (!SehReadI32(e + INV_ENTRY_QTY_OFF, qty)) break;",
        "                if (qty < 0) qty = 0; if (qty > 0x270F) qty = 0x270F;",
        "                fragQty = qty; found = true;",
        "                if (g_invContainerOff < 0) g_invContainerOff = off;   // cache the bag",
        "                break;",
        "            }",
        "        }",
        "    }",
        "    // No fragment stack found this tick -> hold 0; never write a transient 0 (avoids flicker if the",
        "    // walk raced a realloc). Once you hold >=1 fragment, found==true and we set the level.",
        "    if (!found) return;",
        "",
        "    int level = 0;",
        "    for (int L = 20; L >= 0; --L) { if (fragQty >= kScaduCum[L]) { level = L; break; } }",
        "",
        "    uint8_t cur = 0;",
        "    if (!SafeRead(pgd + kScaduCombatLevelOff, cur)) return;",
        "    // Only ever RAISE the stored level: never stomp a real DLC revere, never down-flicker.",
        "    if (static_cast<int>(cur) >= level) return;",
        "    if (SehWriteU8(reinterpret_cast<void*>(pgd + kScaduCombatLevelOff), static_cast<uint8_t>(level)))",
        '        spdlog::info("global_scadu_blessing: frags={} -> blessing level {} (PGD+0xFC, was {})",',
        "                     fragQty, level, static_cast<int>(cur));",
        "}",
        "",
    ]
    win = insert_before(win, "}} // namespace er_ap::game", impl, WIN)
    save(WIN, win)


# ---- ArchipelagoInterface.cpp : parse the option (tab-indented) ------------------------
iface = load(IFACE)
if "global_scadutree_blessing" in iface:
    print("ArchipelagoInterface.cpp already parses global_scadutree_blessing; skipping.")
else:
    iface = insert_after(
        iface,
        "\t\t\t\ter_ap::game::SetAutoUpgrade(0);",
        [
            "\t\t\t// Global Scadutree Blessing (default off; patch_client_global_scadu_blessing.py).",
            "\t\t\tif (data.at(\"options\").contains(\"global_scadutree_blessing\"))",
            "\t\t\t\ter_ap::game::SetGlobalScaduBlessing(data.at(\"options\").at(\"global_scadutree_blessing\").get<int>());",
            "\t\t\telse",
            "\t\t\t\ter_ap::game::SetGlobalScaduBlessing(0);",
        ],
        IFACE,
    )
    save(IFACE, iface)


# ---- Core.cpp : tick the feature inside the in-world poll (tab-indented) ---------------
core = load(CORE)
if "TickGlobalScaduBlessing" in core:
    print("Core.cpp already calls TickGlobalScaduBlessing; skipping.")
else:
    core = insert_after(
        core,
        "\t\t\tPollLocationFlags();",
        [
            "",
            "\t\t\t// Global Scadutree Blessing (SPEC-global-scadutree-blessing.md): raise the stored",
            "\t\t\t// blessing level from held Scadutree Fragments so the buff applies in the base game.",
            "\t\t\t// No-op unless slot_data global_scadutree_blessing != off. MUST be in this settled",
            "\t\t\t// (InventoryInstance()!=0) block -- it reads/writes live PlayerGameData.",
            "\t\t\ter_ap::game::TickGlobalScaduBlessing();",
        ],
        CORE,
    )
    save(CORE, core)


print("""
DONE (client half).

Build + test:
  1) python patch_apworld_global_scadu_blessing.py   (if not already run)
  2) .\\build.ps1 -Clean -All                          (rebuild client + randomizer)
  3) In a yaml: global_scadutree_blessing: player_only ; generate + bake + play the BASE game.
  4) Hold Scadutree Fragments, rest at a grace (or reload), confirm the blessing buff applies
     (damage out up / in down) and the in-game blessing level matches the fragment curve.

If the buff never applies: the most likely cause is the pgd-base assumption. Confirm in CE that
the client's resolved PlayerGameData == the table's [GameDataMan+0x08]; if the client derefs a
different base, re-base kScaduCombatLevelOff accordingly (see SPEC P2 verification procedure).
""")
