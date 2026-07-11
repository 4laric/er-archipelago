-- ============================================================================
-- Mini-baker CE probe #2: prove sellQuantity = -1 == UNLIMITED stock  (no code exec, no crash)
-- ============================================================================
-- Approach: scan EVERY ShopLineupParam row and set sellQuantity = -1. Then open ANY merchant you
-- can reach (Kale at Church of Elleh, or the Twin Maiden Husks at Roundtable) and buy a normally
-- limited item several times. If its stock never runs out, -1 = infinite is confirmed -- which is the
-- last behavior the runtime mini-baker depends on. (The "which row does a shop display" question is a
-- row-ID-range thing I'll solve in the Rust spike; it isn't needed to confirm the stock behavior.)
--
-- Pure param writes only -- no game-function calls, so nothing to crash. Reverts on game reload.
--
-- REQUIREMENTS: a save loaded; AP client NOT connected (shop_flags.rs would re-clamp sellQuantity=1).
-- HOW TO RUN: Table > Show Cheat Table Lua Script > paste > Execute. Result -> CE title bar.
-- ============================================================================

local OFF_SELLQTY = 0x14  -- SHOP_LINEUP_PARAM_ST.sellQuantity (s16); confirmed via probe #1 readback

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

local function run()
  local basePtr = GetParamBasePtr()
  if not basePtr then return "FAIL: param base not found" end
  local ParamBase = readQword(basePtr)

  local slBase
  for i = 0, 184 do
    local b, name = GetParamTable(ParamBase, i)
    if name == "ShopLineupParam" then slBase = b; break end
  end
  if not slBase then return "FAIL: ShopLineupParam table not found" end

  local n = readSmallInteger(slBase + 10)
  local changed, alreadyInf = 0, 0
  for i = 0, n - 1 do
    local addr = slBase + readInteger(slBase + 64 + 24 * i + 8)
    local q = readSmallInteger(addr + OFF_SELLQTY)
    if q == -1 then
      alreadyInf = alreadyInf + 1
    else
      writeSmallInteger(addr + OFF_SELLQTY, -1)
      changed = changed + 1
    end
  end
  return string.format("ShopLineupParam rows=%d | set sellQty=-1 on %d (was already infinite: %d). "
    .. "Open ANY merchant and buy a limited item repeatedly -- it should never run out.",
    n, changed, alreadyInf)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
