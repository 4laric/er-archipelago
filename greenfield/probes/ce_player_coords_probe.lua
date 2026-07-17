-- ============================================================================
-- Player world-coordinate probe v5 (map-overlay feasibility, GLOBAL coords, exact table path)
-- ============================================================================
-- Hexinton v6.1 defines: LocalPlayerOffset = 0x10EF8  (NOT the 0x1E508 v1-v4 used -- both reach the
-- player and both give valid LOCAL coords, but only the 0x10EF8 base carries the global block).
-- Table pointer paths (CE offsets resolve bottom-up; "0*10" == +0):
--   playerBase B2 = [ [ [WorldChrMan] + 0x10EF8 ] + 0 ]
--   Global Coords          = B2 + 0x6B0 / +0x6B4 / +0x6B8   (true continuous world position)
--   LastGoodGlobalCoords   = B2 + 0x6C4 / +0x6C8 / +0x6CC   (survives loading screens)
--   Local (rebased)        = [[B2 + 0x190] + 0x68] + 0x70
-- Also read the current tile from the 0x1E508 base (+0x38) for context.
--
-- Stand on a known grace; Global x/z should match that grace's datamine (gx, gz):
--   The First Step (10739, 9162) | Church of Elleh (10711, 9295) | Gatefront (10766, 9582)
--   Agheel Lake North (10928, 9528) | Agheel Lake South (11226, 9007)
-- ============================================================================

local WCM_AOB    = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88"
local LPO        = 0x10EF8    -- LocalPlayerOffset (global-bearing base)
local ALT_OFF    = 0x1E508    -- the base v1-v4 used (tile lives here at +0x38)

local function resolveWorldChrMan()
  local exebase = getAddress("eldenring.exe")
  local exesize = getModuleSize("eldenring.exe")
  local ms = createMemScan()
  ms.setOnlyOneResult(true)
  ms.firstScan(soExactValue, vtByteArray, nil, WCM_AOB, nil, exebase, exebase + exesize,
               '+X', fsmNotAligned, '1', true, false, false, false)
  ms.waitTillDone()
  local hit = ms.getOnlyResult()
  ms.destroy()
  if not hit then return nil end
  return readQword(hit + 7 + readInteger(hit + 3, true))
end

local function trip(base, off)
  if not base or base == 0 then return nil end
  return readFloat(base + off), readFloat(base + off + 4), readFloat(base + off + 8)
end

local function run()
  local wcm = resolveWorldChrMan()
  if not wcm or wcm == 0 then return "FAIL: WorldChrMan not resolved (save loaded?)" end

  -- table's global-bearing base:  B2 = [[[WorldChrMan]+10EF8]+0]
  local p = readQword(wcm + LPO)
  local B2 = p and p ~= 0 and readQword(p + 0) or nil
  if not B2 or B2 == 0 then return "FAIL: player base via 0x10EF8 is null" end

  -- tile from the 0x1E508 base (+0x38 little-endian {sub,YY,XX,area})
  local alt = readQword(wcm + ALT_OFF)
  local area, XX, YY = 0, 0, 0
  if alt and alt ~= 0 then
    local id = readInteger(alt + 0x38, false)
    area, XX, YY = (id >> 24) & 0xFF, (id >> 16) & 0xFF, (id >> 8) & 0xFF
  end

  local gx, gy, gz = trip(B2, 0x6B0)
  local lgx, lgy, lgz = trip(B2, 0x6C4)

  print("------------------------------------------------------------")
  print(string.format("  tile          m%d_%02d_%02d", area, XX, YY))
  print(string.format("  GLOBAL        x=%.2f  y=%.2f  z=%.2f", gx or 0/0, gy or 0/0, gz or 0/0))
  print(string.format("  lastGoodGlob  x=%.2f  y=%.2f  z=%.2f", lgx or 0/0, lgy or 0/0, lgz or 0/0))
  print(string.format("REPORT  global=(%.2f, %.2f)  tile=m%d_%02d_%02d  <-- grace=?", gx or 0/0, gz or 0/0, area, XX, YY))
  print("------------------------------------------------------------")
  return string.format("GLOBAL gx=%.1f gz=%.1f -- compare to the grace's datamine (gx,gz)", gx or 0/0, gz or 0/0)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
print(ok and tostring(res) or ("ERR: " .. tostring(res)))
