-- ============================================================================
-- Mini-baker CE probe: infinite Stonesword Key at Twin Maiden Husks  (self-contained)
-- ============================================================================
-- Goal: prove the two things the runtime "mini-baker" needs before we write any Rust:
--   (1) sellQuantity = -1 on a live ShopLineupParam row = UNLIMITED purchases, and
--   (2) an edited row shows + buys in the shop UI.
--
-- This version INLINES the param-access helpers (GetParamBasePtr / GetParamTable /
-- ParamIdToAddress, lifted from the Hexinton v6.0 table) so it does NOT depend on any table
-- cheat entry being enabled first. It only needs a save loaded. ShopMenu (the convenience
-- shop opener) DOES live in the table -- if it isn't available we fall back to "visit Twin Maiden".
--
-- What it does to ShopLineupParam row 100102 (Twin Maiden Husks' Stonesword Key slot):
--   * reads equipId/value/evStock/sellQty back FIRST as an offset self-check
--     (should be 8000 / 5000 / 110020 / 1 -- if not, stop and report; offsets are wrong),
--   * sellQuantity -> -1 (unlimited), value -> 100 runes (cheap), eventFlag_forStock -> 0 (always stock),
--   * opens a Purchase menu (if ShopMenu is available) showing just that row.
--
-- REQUIREMENTS:
--   * a save is loaded (params in memory).  Hexinton table loaded = optional (only for ShopMenu).
--   * AP client NOT connected -- shop_flags.rs clamps sellQuantity back to 1 on check rows.
--
-- HOW TO RUN: Table > Show Cheat Table Lua Script > paste > Execute.
-- Result (BEFORE / AFTER / ShopMenu status) prints to Cheat Engine's title bar. Reverts on reload.
-- ============================================================================

local ID = 100102  -- Twin Maiden Husks Stonesword Key slot
-- SHOP_LINEUP_PARAM_ST offsets: equipId 0x00, value 0x04, eventFlag_forStock 0x0C, sellQuantity 0x14 (s16)
local OFF_EQUIP, OFF_VALUE, OFF_STOCKFLAG, OFF_SELLQTY = 0x00, 0x04, 0x0C, 0x14

-- ---- inlined param access (Hexinton v6.0) --------------------------------------------------
local function GetParamBasePtr()
  local exebase = getAddress("eldenring.exe")
  local exesize = getModuleSize("eldenring.exe")
  local ms = createMemScan()
  ms.setOnlyOneResult(true)
  local pat = "48 8B 0D ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? E8 ?? ?? ?? ?? 48 85 C0 0F 84 ?? ?? ?? ?? 48 8B 80 80 00 00 00 48 8B 90 80 00 00 00"
  ms.firstScan(soExactValue, vtByteArray, nil, pat, nil, exebase, exebase + exesize, '+X', fsmNotAligned, '1', true, false, false, false)
  ms.waitTillDone()
  local found = ms.getOnlyResult()
  ms.destroy()
  if not found then return nil end
  return found + 7 + readInteger(found + 3, true)
end

local function GetParamTable(ParamBase, Index)
  local hdr = readQword(ParamBase + Index * 72 + 0x88)
  if not hdr then return nil end
  return readQword(readQword(hdr + 0x80) + 0x80), readString(readQword(hdr + 24), 128, true)
end

local function ParamIdToAddress(TableBase, wantId)
  local n = readSmallInteger(TableBase + 10)
  for i = 0, n - 1 do
    if readInteger(TableBase + 64 + 24 * i) == wantId then
      return TableBase + readInteger(TableBase + 64 + 24 * i + 8)
    end
  end
  return 0
end
-- --------------------------------------------------------------------------------------------

local function run()
  local basePtr = GetParamBasePtr()
  if not basePtr then return "FAIL: could not find param base (game loaded? correct exe?)" end
  local ParamBase = readQword(basePtr)

  local slBase
  for i = 0, 184 do
    local b, name = GetParamTable(ParamBase, i)
    if name == "ShopLineupParam" then slBase = b; break end
  end
  if not slBase then return "FAIL: ShopLineupParam table not found" end

  local row = ParamIdToAddress(slBase, ID)
  if not row or row == 0 then return "FAIL: ShopLineupParam row " .. ID .. " not found" end

  local before = string.format(
    "BEFORE id=%d equipId=%d value=%d evStock=%d sellQty=%d (expect 8000/5000/110020/1)",
    ID, readInteger(row + OFF_EQUIP), readInteger(row + OFF_VALUE),
    readInteger(row + OFF_STOCKFLAG), readSmallInteger(row + OFF_SELLQTY))

  writeSmallInteger(row + OFF_SELLQTY, -1)   -- unlimited
  writeInteger(row + OFF_VALUE, 100)         -- cheap
  writeInteger(row + OFF_STOCKFLAG, 0)       -- always available

  local after = string.format(
    "AFTER equipId=%d value=%d evStock=%d sellQty=%d",
    readInteger(row + OFF_EQUIP), readInteger(row + OFF_VALUE),
    readInteger(row + OFF_STOCKFLAG), readSmallInteger(row + OFF_SELLQTY))

  -- inlined "Purchase Item" shop opener (Hexinton v6.0 / game 2.02). Force-opens a purchase menu
  -- for lineup id range [ID,ID], decoupled from which merchant naturally shows the row.
  local function openPurchaseMenu(startId, endId)
    local game_addr = getAddress("eldenring.exe")
    local fun_addr  = game_addr + 0x80e770          -- "Purchase Item" shop function
    local mem = allocateMemory(0xA0, game_addr)
    executeCodeEx(0, 100, fun_addr, "", startId, endId, mem)
    deAlloc(mem)
  end

  local ok, err = pcall(function() openPurchaseMenu(ID, ID) end)
  local shopMsg = ok and ("Purchase menu opened for row " .. ID .. " -- buy Stonesword Keys repeatedly")
                       or ("shop-open err: " .. tostring(err))

  return before .. "  ||  " .. after .. "  ||  " .. shopMsg
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
