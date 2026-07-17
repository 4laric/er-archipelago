-- ============================================================================
-- Player world-coordinate probe v3 (map-overlay feasibility, calibration)  -- self-contained
-- ============================================================================
-- Confirmed so far:
--   * player ChrIns  = WorldChrMan + 0x1E508
--   * live tile-LOCAL position {x,y,z} floats at  ChrIns ->0x190 ->0x68 +0x70
--   * current overworld tile id (little-endian dword {sub,YY,XX,area}) at  ChrIns + 0x38
--     -> XX = (id>>16)&0xFF, YY = (id>>8)&0xFF, area = (id>>24)&0xFF  (overworld area 60/61)
--
-- This v3 composes GLOBAL coords the same way our datamine does (gx = XX*256 + localX, gz = YY*256 +
-- localZ) and prints a copy-pasteable REPORT line. We read it at a few known graces to fit the small
-- constant offset between the live physics frame and our datamine (MSB) frame -- then the companion
-- overlay places the live player and the datamined checks on ONE map.
--
-- HOW TO RUN: stand ON a grace you can name, Execute, copy the REPORT line from CE's Lua output.
-- Do it at 3-4 graces spread across a few tiles (e.g. The First Step, Church of Elleh, Gatefront,
-- Agheel Lake South). Paste all the REPORT lines back with each grace's name.
-- ============================================================================

local WCM_AOB     = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88"
local PLAYER_OFF  = 0x1E508
local COORD_DEREF = { 0x190, 0x68 }
local COORD_XOFF  = 0x70
local TILE_OFF    = 0x38            -- ChrIns + 0x38 : map-id dword (little-endian {sub,YY,XX,area})

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

local function run()
  local wcm = resolveWorldChrMan()
  if not wcm or wcm == 0 then return "FAIL: WorldChrMan not resolved (save loaded?)" end
  local chrins = readQword(wcm + PLAYER_OFF)
  if not chrins or chrins == 0 then return "FAIL: player ChrIns null" end

  local p = chrins
  for _, off in ipairs(COORD_DEREF) do
    p = readQword(p + off)
    if not p or p == 0 then return "FAIL: coord chain broke" end
  end
  local x, y, z = readFloat(p + COORD_XOFF), readFloat(p + COORD_XOFF + 4), readFloat(p + COORD_XOFF + 8)

  local id   = readInteger(chrins + TILE_OFF, false)   -- unsigned dword
  local area = (id >> 24) & 0xFF
  local XX   = (id >> 16) & 0xFF
  local YY   = (id >> 8)  & 0xFF
  local sub  =  id        & 0xFF

  if area ~= 60 and area ~= 61 then
    print(string.format("WARN: tile dword at +0x%X = 0x%08X decodes area=%d (not 60/61); you may be", TILE_OFF, id, area))
    print("      in a legacy/interior map -- overworld only for now.")
  end

  local gx = XX * 256 + x
  local gz = YY * 256 + z
  print("------------------------------------------------------------")
  print(string.format("  tile  m%d_%02d_%02d_%02d", area, XX, YY, sub))
  print(string.format("  local x=%.3f  y=%.3f  z=%.3f", x, y, z))
  print(string.format("REPORT  tile=m%d_%02d_%02d  local=(%.3f, %.3f)  global=(%.2f, %.2f)  <-- grace=?",
                      area, XX, YY, x, z, gx, gz))
  print("------------------------------------------------------------")
  return string.format("global gx=%.1f gz=%.1f (tile m%d_%02d_%02d) -- copy the REPORT line + grace name",
                       gx, gz, area, XX, YY)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
print(ok and tostring(res) or ("ERR: " .. tostring(res)))
