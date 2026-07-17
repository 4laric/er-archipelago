-- ============================================================================
-- Player world-coordinate probe v4 (map-overlay feasibility, GLOBAL coords)  -- self-contained
-- ============================================================================
-- The Hexinton v6.1 table settles it. There are three position fields off the local-player pointer:
--   * Local Coords  ->190 ->68 +0x70    -- rebased/anchor-relative (what v1-v3 read; NOT world pos)
--   * Chunk Coords  ->D0->18->a8->68... -- the rebasing chunk origin
--   * Global Coords            +0x6B0   -- the TRUE continuous world position  <-- what we want
--   * LastGoodGlobalCoords     +0x6C4   -- last valid global (survives loading screens)
-- All three hang off the same local-player base we already resolve:
--   chrins = [[WorldChrMan] + 0x1E508]   (confirmed: gives the right Local coords + tile at +0x38)
--
-- This reads Global (chrins+0x6B0/6B4/6B8) + LastGood (chrins+0x6C4/6C8/6CC), plus Local + tile for
-- context, and prints a REPORT line. Stand on a known grace: Global X/Z should match that grace's
-- datamine global (gx, gz) from item_grace_coords.tsv -- e.g. The First Step (10739, 9162),
-- Agheel Lake North (10928, 9528), Gatefront (10766, 9582). If they line up, the companion overlay
-- is done bar the drawing: player + every check share one frame.
-- ============================================================================

local WCM_AOB    = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88"
local PLAYER_OFF = 0x1E508
local TILE_OFF   = 0x38

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
  return readFloat(base + off), readFloat(base + off + 4), readFloat(base + off + 8)
end

local function run()
  local wcm = resolveWorldChrMan()
  if not wcm or wcm == 0 then return "FAIL: WorldChrMan not resolved (save loaded?)" end
  local chrins = readQword(wcm + PLAYER_OFF)
  if not chrins or chrins == 0 then return "FAIL: player ChrIns null" end

  -- tile (little-endian dword {sub,YY,XX,area} at +0x38)
  local id = readInteger(chrins + TILE_OFF, false)
  local area, XX, YY = (id >> 24) & 0xFF, (id >> 16) & 0xFF, (id >> 8) & 0xFF

  local gx, gy, gz = trip(chrins, 0x6B0)          -- Global Coords
  local lgx, lgy, lgz = trip(chrins, 0x6C4)        -- LastGoodGlobalCoords
  -- Local (rebased) for reference: chrins ->0x190 ->0x68 +0x70
  local pm = readQword(chrins + 0x190); pm = pm and readQword(pm + 0x68)
  local lx, ly, lz
  if pm and pm ~= 0 then lx, ly, lz = trip(pm, 0x70) end

  print("------------------------------------------------------------")
  print(string.format("  tile         m%d_%02d_%02d", area, XX, YY))
  if lx then print(string.format("  local (reb.) x=%.2f  y=%.2f  z=%.2f", lx, ly, lz)) end
  print(string.format("  GLOBAL       x=%.2f  y=%.2f  z=%.2f", gx, gy, gz))
  print(string.format("  lastGoodGlob x=%.2f  y=%.2f  z=%.2f", lgx, lgy, lgz))
  print(string.format("REPORT  global=(%.2f, %.2f)  tile=m%d_%02d_%02d  <-- grace=?", gx, gz, area, XX, YY))
  print("------------------------------------------------------------")
  return string.format("GLOBAL gx=%.1f gz=%.1f -- compare to the grace's datamine (gx,gz)", gx, gz)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
print(ok and tostring(res) or ("ERR: " .. tostring(res)))
