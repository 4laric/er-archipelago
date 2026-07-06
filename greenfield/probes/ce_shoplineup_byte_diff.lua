-- ============================================================================
-- ShopLineupParam byte-diff: pin sellQuantity / equipType / costType offsets exactly.
-- ============================================================================
-- RELOAD the game first (vanilla values) and keep the AP client DISCONNECTED (it rewrites shop rows).
-- Dumps bytes 0x10..0x1F for two rows that differ in the fields we care about:
--   100680: eventFlag_forRelease=0        sellQuantity=3  equipType=3  costType=0  setNum=1
--   101962: eventFlag_forRelease=1050400800 sellQuantity=1  equipType=3  costType=1  setNum=1
-- The byte that reads 3 vs 1 = sellQuantity; the byte that reads 0 vs 1 = costType; the byte that is
-- 3 in both = equipType. (0x10 dword should read 0 for the first row and 1050400800 for the second.)
-- HOW TO RUN: Table > Show Cheat Table Lua Script > paste > Execute. Result -> CE title bar.
-- ============================================================================

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

local function bytesHex(addr, from, len)
  local b = readBytes(addr + from, len, true)
  local s = {}
  for i = 1, len do s[i] = string.format("%02X", b[i]) end
  return table.concat(s, " ")
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

  local r1 = ParamIdToAddress(slBase, 100680)
  local r2 = ParamIdToAddress(slBase, 101962)
  if r1 == 0 or r2 == 0 then return "FAIL: row missing" end
  -- label the byte columns 10..1F for easy reading
  return "off 10 11 12 13 14 15 16 17 18 19 1A 1B 1C 1D 1E 1F || "
      .. "100680: " .. bytesHex(r1, 0x10, 16) .. " || "
      .. "101962: " .. bytesHex(r2, 0x10, 16)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
