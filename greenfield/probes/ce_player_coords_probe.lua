-- ============================================================================
-- Player world-coordinate probe v2 (map-overlay feasibility, step 2)  -- self-contained
-- ============================================================================
-- Step 1 confirmed: WorldChrMan resolves, and the player's LIVE tile-local position reads from
--   WorldChrMan + 0x1E508  (player ChrIns)  ->  +0x190 -> +0x68  ->  {x,y,z} floats at +0x70.
-- Small values (|x|,|z| < ~256) => tile-LOCAL, so global gx/gz = currentTileXX*256 + localX (and YY,z).
-- This v2:
--   (1) reads the confirmed local x/y/z a few times (proves it's live + stable), and
--   (2) HUNTS the current overworld tile id (m60_XX_YY) in the player struct, so we can compose global.
--
-- ER stores a map id as 4 bytes {area, b1, b2, sub}. Overworld => area = 60 (0x3C) or 61 (0x3D),
-- b1/b2 = tile column/row (~0x20..0x40), sub = 0..2. We scan the ChrIns window for that signature and
-- print every candidate with its decoded tile + byte offset, so you pick the one matching where you are.
--
-- HOW TO RUN: load a save, stand on a grace you can name (ideally The First Step = tile m60_42_36, or
-- any grace you can find in item_grace_coords.tsv). Table > Show Cheat Table Lua Script > paste >
-- Execute. Read CE's Lua-engine output.
--
-- REPORT BACK: (a) the x/y/z printed, (b) which grace you're standing on, (c) the tile-candidate line(s)
-- whose decoded m60_XX_YY matches your real location. That nails the tile-field offset + confirms the
-- frame; after that, live global coords are just tile*256 + local, and the companion overlay is plumbing.
-- ============================================================================

local WCM_AOB     = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88"
local PLAYER_OFF  = 0x1E508          -- WorldChrMan -> local player ChrIns (confirmed step 1)
local COORD_DEREF = { 0x190, 0x68 }  -- ChrIns -> physics module -> coord block
local COORD_XOFF  = 0x70             -- {x,y,z} floats
local SCAN_BYTES  = 0x3000           -- ChrIns window to sweep for the map-id signature

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

local function readCoords(chrins)
  local p = chrins
  for _, off in ipairs(COORD_DEREF) do
    p = readQword(p + off)
    if not p or p == 0 then return nil end
  end
  return readFloat(p + COORD_XOFF), readFloat(p + COORD_XOFF + 4), readFloat(p + COORD_XOFF + 8)
end

-- scan the ChrIns window for an overworld map-id byte signature {60|61, XX, YY, sub}
local function huntTile(chrins)
  local out = {}
  local buf = readBytes(chrins, SCAN_BYTES, true)
  if not buf then return out end
  for i = 1, #buf - 3 do
    local a, b, c, d = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
    -- forward {area, XX, YY, sub}
    if (a == 60 or a == 61) and b >= 0x20 and b <= 0x42 and c >= 0x20 and c <= 0x42 and d <= 2 then
      out[#out + 1] = string.format("chrins+0x%X  fwd  m%d_%02d_%02d_%02d", i - 1, a, b, c, d)
    end
    -- reversed {sub, YY, XX, area}
    if (d == 60 or d == 61) and c >= 0x20 and c <= 0x42 and b >= 0x20 and b <= 0x42 and a <= 2 then
      out[#out + 1] = string.format("chrins+0x%X  rev  m%d_%02d_%02d_%02d", i - 1, d, c, b, a)
    end
  end
  return out
end

local function run()
  local wcm = resolveWorldChrMan()
  if not wcm or wcm == 0 then return "FAIL: WorldChrMan not resolved (save loaded?)" end
  local chrins = readQword(wcm + PLAYER_OFF)
  if not chrins or chrins == 0 then return "FAIL: player ChrIns null at WorldChrMan+0x1E508" end

  print("---- live local position (read x3; should be steady if you stand still) ----")
  for _ = 1, 3 do
    local x, y, z = readCoords(chrins)
    if not x then return "FAIL: coord chain broke (0x190->0x68 +0x70)" end
    print(string.format("  local x=%.3f  y=%.3f  z=%.3f", x, y, z))
  end

  local tiles = huntTile(chrins)
  print(string.format("---- map-id candidates in ChrIns window (%d found) ----", #tiles))
  local shown = 0
  for _, t in ipairs(tiles) do
    print("  " .. t); shown = shown + 1
    if shown >= 40 then print("  ... (truncated)"); break end
  end
  if #tiles == 0 then
    print("  none -- map id may live outside the ChrIns (WorldBlockChr / CSFD4). Report the x/y/z + your")
    print("  grace name anyway; I can also widen the scan or read it from your Hexinton table's Map ID.")
  end
  return string.format("coords OK; %d tile-id candidate(s) -- report the one matching your location", #tiles)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
print(ok and tostring(res) or ("ERR: " .. tostring(res)))
