-- ============================================================================
-- ShopLineupParam offset-mapper: dump one known row's dwords so we can locate the real field offsets.
-- ============================================================================
-- RELOAD THE GAME FIRST (reverts our earlier param edits to vanilla), AP client disconnected.
-- Row 100680 vanilla values (from ShopLineupParam.csv):
--   equipId=8000  value=3000  mtrlId=-1  eventFlag_forStock=160800  eventFlag_forRelease=0
--   sellQuantity=3  equipType=3  costType=0  setNum=1  value_Magnification=1.0
-- We dump signed int32 at every 4-byte offset 0x00..0x3C; match those numbers to the fields above
-- to find where sellQuantity (=3) and eventFlag_forStock (=160800) actually live.
-- HOW TO RUN: Table > Show Cheat Table Lua Script > paste > Execute. Result -> CE title bar.
-- ============================================================================

local ID = 100680

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

  local parts = {}
  for off = 0, 0x3C, 4 do
    parts[#parts + 1] = string.format("%X=%d", off, readInteger(row + off, true))
  end
  return "row " .. ID .. "  " .. table.concat(parts, " ")
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
