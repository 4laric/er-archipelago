-- ============================================================================
-- Mini-baker repurpose: turn the Twin Maiden Husks' Blue Cipher Ring slot into an
-- INFINITE Stonesword Key.  Row 101801 (equipId 105 Blue Cipher Ring, value 1000, sellQty 1).
-- ============================================================================
-- Offsets confirmed live: equipId 0x00 (s32), value 0x04 (s32), sellQuantity 0x14 (s16).
-- equipType (0x17) is already 3 (goods) and Stonesword Key is goods, so no type change needed.
-- Edit: equipId -> 8000 (Stonesword Key), value -> 100 (cheap), sellQuantity -> -1 (infinite).
-- eventFlag_forStock left as 60290 (already set -- the slot is currently visible).
--
-- REQUIREMENTS: save loaded, AP client disconnected. Non-destructive (reverts on reload).
-- HOW TO RUN: paste into Table > Show Cheat Table Lua Script > Execute.
-- Then CLOSE and REOPEN the Twin Maidens shop -- the Blue Cipher Ring slot is now a Stonesword Key
-- for 100 runes. Buy it repeatedly and confirm the quantity never drops.
-- Result (BEFORE/AFTER) prints to CE title bar.
-- ============================================================================

local ID = 101801
local OFF_EQUIP, OFF_VALUE, OFF_SELLQTY = 0x00, 0x04, 0x14
local STONESWORD_KEY = 8000

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

local function run()
  local basePtr = GetParamBasePtr(); if not basePtr then return "FAIL: param base" end
  local ParamBase = readQword(basePtr)
  local slBase
  for i = 0, 184 do
    local b, name = GetParamTable(ParamBase, i)
    if name == "ShopLineupParam" then slBase = b; break end
  end
  if not slBase then return "FAIL: ShopLineupParam table" end
  local row = ParamIdToAddress(slBase, ID); if row == 0 then return "FAIL: row " .. ID end

  local before = string.format("BEFORE equipId=%d value=%d sellQty=%d (expect 105/1000/1)",
    readInteger(row + OFF_EQUIP), readInteger(row + OFF_VALUE), readSmallInteger(row + OFF_SELLQTY))

  writeInteger(row + OFF_EQUIP, STONESWORD_KEY)
  writeInteger(row + OFF_VALUE, 100)
  writeSmallInteger(row + OFF_SELLQTY, -1)

  local after = string.format("AFTER equipId=%d value=%d sellQty=%d",
    readInteger(row + OFF_EQUIP), readInteger(row + OFF_VALUE), readSmallInteger(row + OFF_SELLQTY))

  return before .. "  ||  " .. after .. "  ||  reopen Twin Maidens -> Stonesword Key @100, buy repeatedly"
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
