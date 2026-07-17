-- ============================================================================
-- Player world-coordinate probe v6 (map-overlay feasibility, FIND global by known value)
-- ============================================================================
-- The Hexinton table's global offset (ChrIns+0x6B0) is stale for this game build -- it reads a pointer,
-- not coords (local coords + tile at their offsets still work). So instead of trusting an offset, we
-- FIND the global field by the value we already know: on a named grace, the player's world position ==
-- that grace's datamine (gx, gz). We sweep the player's own memory windows (the ChrIns struct + its
-- physics module) for a float pair matching the target, and report the offset -- version-proof, and
-- scoped to the player so we don't hit the dozens of nearby entities at similar coords.
--
-- SET THE TARGET to the grace you'll stand on (datamine gx, gz), then stand on it and Execute:
local TARGET_GX, TARGET_GZ = 10739.2, 9161.5   -- The First Step   (default)
--   Church of Elleh    10711.3, 9295.3
--   Gatefront          10765.6, 9582.2
--   Agheel Lake North  10928.0, 9528.1
--   Agheel Lake South  11225.8, 9007.3
local TOL = 18   -- meters of slack (you vs the grace's exact centre, + any live/datamine frame offset)
-- ============================================================================

local WCM_AOB    = "48 8B 05 ?? ?? ?? ?? 48 85 C0 74 0F 48 39 88"
local PLAYER_OFF = 0x1E508

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

local function fin(f) return f == f and f ~= math.huge and f ~= -math.huge end

-- sweep [base, base+size) for a float ~ TARGET_GX whose partner (z at +8, or +4) ~ TARGET_GZ
local function sweep(base, size, label, out)
  if not base or base == 0 then return end
  for o = 0, size - 12, 4 do
    local x = readFloat(base + o)
    if x and fin(x) and math.abs(x - TARGET_GX) <= TOL then
      local z8 = readFloat(base + o + 8)
      local z4 = readFloat(base + o + 4)
      if z8 and fin(z8) and math.abs(z8 - TARGET_GZ) <= TOL then
        out[#out+1] = string.format("%s+0x%X  x=%.2f (+8)z=%.2f  [x,y,z layout]", label, o, x, z8)
      elseif z4 and fin(z4) and math.abs(z4 - TARGET_GZ) <= TOL then
        out[#out+1] = string.format("%s+0x%X  x=%.2f (+4)z=%.2f  [x,z layout]", label, o, x, z4)
      end
    end
  end
end

local function run()
  local wcm = resolveWorldChrMan()
  if not wcm or wcm == 0 then return "FAIL: WorldChrMan not resolved (save loaded?)" end
  local chrins = readQword(wcm + PLAYER_OFF)
  if not chrins or chrins == 0 then return "FAIL: player ChrIns null" end
  local pm = readQword(chrins + 0x190); pm = pm and pm ~= 0 and readQword(pm + 0x68) or nil

  local out = {}
  sweep(chrins, 0x3000, "chrins", out)                       -- the ChrIns struct
  if pm then sweep(pm, 0x1000, "physmod", out) end            -- physics module (near local coords)

  print(string.format("---- hunting global (%.1f, %.1f) +/-%d in player memory ----", TARGET_GX, TARGET_GZ, TOL))
  if #out == 0 then
    print("  no match in ChrIns/physmod windows -- global may live off WorldChrMan or a world block.")
    print("  Tell me and I'll widen to a full targeted memscan, or read the table's live Global Coords.")
  else
    for _, h in ipairs(out) do print("  " .. h) end
  end
  return string.format("%d candidate offset(s) -- report them + confirm you're on the target grace", #out)
end

local ok, res = pcall(run)
getMainForm().Caption = ok and tostring(res) or ("ERR: " .. tostring(res))
print(ok and tostring(res) or ("ERR: " .. tostring(res)))
