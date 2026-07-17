-- ============================================================================
-- Player world-coordinate probe (map-overlay feasibility, step 1)  -- self-contained
-- ============================================================================
-- Goal: prove we can stream the LIVE player world position (gx, gy, gz) and that it lands in the
-- SAME coordinate frame our datamine emits (greenfield/item_grace_coords.tsv). If yes, a companion
-- map overlay ("you are here" + remaining AP checks on our own Lands Between map) is just plumbing:
-- we already have every check's gx/gz and the exact tile transform (gx = tileXX*256 + localX).
--
-- WHY A SWEEP: the WorldChrMan static pointer resolves from a version-STABLE AOB, but the offset from
-- WorldChrMan to the local player's coordinate block drifts between game patches. Rather than hardcode
-- one (maybe-stale) chain, this tries the documented candidates and prints every one that yields a
-- finite, in-range position. You then eyeball which candidate matches where you're standing.
--
-- HOW TO RUN: load a save, stand ON a known grace (pick one you can find in item_grace_coords.tsv),
-- then Table > Show Cheat Table Lua Script > paste > Execute. Read the result in CE's title bar
-- (and the full dump in the Lua engine output). Report back the line that looks right.
--
-- WHAT TO REPORT: the (x, y, z) that matches your location + which grace you stood on. I'll compare
-- it to that grace's gx/gy/gz in our data to confirm the frames line up (and pin the sign/axis order).
-- ============================================================================

-- WorldChrMan static pointer (this AOB has been stable across ER patches incl. the DLC era)
local WCM_AOB = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88"

-- Candidate offset from WorldChrMan -> local-player ChrIns, across versions (most-common first).
local PLAYER_OFFSETS = { 0x10EF8, 0x10FF8, 0x1E508, 0x1E7C8, 0x1E7D8, 0x1E9D0 }

-- Candidate chains ChrIns -> coordinate block. The block is 3 contiguous floats {x,y,z}; we read at
-- each candidate base. (0x190->0x68 = the classic CSChrPhysicsModule path; others are direct blocks.)
local COORD_CHAINS = {
  { name = "phys 0x190->0x68 +0x70", deref = {0x190, 0x68}, xoff = 0x70 },
  { name = "phys 0x190->0x68 +0x80", deref = {0x190, 0x68}, xoff = 0x80 },
  { name = "direct +0x6B8",          deref = {},            xoff = 0x6B8 },
  { name = "direct +0x70",           deref = {},            xoff = 0x70  },
}

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
  -- instruction: 48 8B 05 <rel32>; RIP-relative target = hit + 7 + rel32; that slot holds WorldChrMan
  local wcm_slot = hit + 7 + readInteger(hit + 3, true)
  return readQword(wcm_slot)
end

local function finite(f)
  return f == f and f ~= math.huge and f ~= -math.huge
end

local function plausible(x, y, z)
  -- overworld local coords sit within a tile-ish range; guard against garbage/NaN
  return finite(x) and finite(y) and finite(z)
     and math.abs(x) < 1e6 and math.abs(y) < 1e6 and math.abs(z) < 1e6
     and (math.abs(x) + math.abs(z)) > 0.01
end

local function readChain(chrins, chain)
  local p = chrins
  for _, off in ipairs(chain.deref) do
    p = readQword(p + off)
    if not p or p == 0 then return nil end
  end
  local bx = p + chain.xoff
  local x, y, z = readFloat(bx), readFloat(bx + 4), readFloat(bx + 8)
  if x == nil or y == nil or z == nil then return nil end
  return x, y, z
end

local function run()
  local wcm = resolveWorldChrMan()
  if not wcm or wcm == 0 then return "FAIL: WorldChrMan not resolved (save loaded? correct exe/version?)" end

  local hits = {}
  for _, po in ipairs(PLAYER_OFFSETS) do
    local chrins = readQword(wcm + po)
    if chrins and chrins ~= 0 then
      for _, chain in ipairs(COORD_CHAINS) do
        local x, y, z = readChain(chrins, chain)
        if x and plausible(x, y, z) then
          local tileXX = math.floor(x / 256)   -- our overworld tile column (m60_XX_..)
          local tileYY = math.floor(z / 256)
          hits[#hits + 1] = string.format(
            "player+0x%X | %-22s | x=%.2f y=%.2f z=%.2f | tile m60_%02d_%02d",
            po, chain.name, x, y, z, tileXX, tileYY)
        end
      end
    end
  end

  if #hits == 0 then
    return "WorldChrMan OK (0x" .. string.format("%X", wcm) ..
           ") but NO candidate chain gave sane coords -- enable your Hexinton table's Position/" ..
           "Coordinates entry and report its address; I'll wire a direct reader."
  end
  print("---- player-coord candidates (report the one matching your spot) ----")
  for _, h in ipairs(hits) do print(h) end
  return string.format("%d candidate(s) printed to Lua output -- pick the one matching your location", #hits)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
print(ok and tostring(res) or ("ERR: " .. tostring(res)))
