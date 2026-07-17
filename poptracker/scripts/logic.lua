-- Region reachability for the ER-AP PopTracker pack.
-- Consumes the GENERATED scripts/region_graph.lua (REGION_ADJ / *_GATES / REGION_ALL / REGION_IS_DLC
-- / REGION_DLC_ROOT) and exposes one access-rule function per region: can_reach_<slug>.
-- locations.json references these as "$can_reach_<slug>".
--
-- Model: BFS from the start region over the directed region graph; a neighbour opens only when its
-- gate items are held. Key gates (vanilla progression, e.g. Academy Glintstone Key) always apply;
-- region-LOCK gates apply only when the seed runs region_lock logic (world_logic 0 or 2). On a
-- dlc_only seed the start region is Gravesite Plain (you begin in the DLC), so reachability
-- bootstraps from there instead of Limgrave.
--
-- WORLD_LOGIC / WORLD_DLC_ONLY are set by autotracking.lua:on_clear from slot_data; defaults below
-- keep the pack usable before a connection (nothing held -> only the start region is reachable).

WORLD_LOGIC = WORLD_LOGIC or 0       -- 0 region_lock, 1 open, 2 region_lock_bosses, 3 boss_logic
WORLD_DLC_ONLY = WORLD_DLC_ONLY or 0 -- 1 == dlc_only seed (Land of Shadow start)

local function lock_active()
  -- region-lock gates only bite under region_lock / region_lock_bosses (matches apworld _lock_logic)
  return WORLD_LOGIC == 0 or WORLD_LOGIC == 2
end

local function has_item(code)
  local o = Tracker:FindObjectForCode(code)
  if not o then return false end
  if o.Active ~= nil and o.Active then return true end
  if o.AcquiredCount ~= nil and o.AcquiredCount > 0 then return true end
  if o.CurrentStage ~= nil and o.CurrentStage > 0 then return true end
  return false
end

local function gate_open(region)
  local keys = REGION_KEY_GATES[region]
  if keys then
    for _, code in ipairs(keys) do
      if not has_item(code) then return false end
    end
  end
  if lock_active() then
    local locks = REGION_LOCK_GATES[region]
    if locks then
      for _, code in ipairs(locks) do
        if not has_item(code) then return false end
      end
    end
  end
  return true
end

local function compute_reach()
  local root = (WORLD_DLC_ONLY == 1) and REGION_DLC_ROOT or REGION_ROOT
  local reach = {}
  -- the start region is always reachable (you spawn there); its own gate is not required
  reach[root] = true
  local queue = { root }
  local head = 1
  while head <= #queue do
    local r = queue[head]; head = head + 1
    local nbrs = REGION_ADJ[r]
    if nbrs then
      for _, nb in ipairs(nbrs) do
        if not reach[nb] and gate_open(nb) then
          reach[nb] = true
          queue[#queue + 1] = nb
        end
      end
    end
  end
  return reach
end

-- Cache the reach set; recompute only when the gate-item set or the world flags change.
local _sig, _reach = nil, {}

local function signature()
  local parts = { tostring(WORLD_LOGIC), tostring(WORLD_DLC_ONLY) }
  for _, code in ipairs(REGION_GATE_CODES) do
    parts[#parts + 1] = has_item(code) and "1" or "0"
  end
  return table.concat(parts, ",")
end

local function ensure()
  local s = signature()
  if s ~= _sig then
    _reach = compute_reach()
    _sig = s
  end
end

-- Force a recompute next call (autotracking.lua calls this from on_clear after setting the flags).
function logic_invalidate()
  _sig = nil
end

-- Define one access-rule function per region slug: can_reach_<slug>() -> 1 reachable / 0 not.
for _, slug in ipairs(REGION_ALL) do
  _G["can_reach_" .. slug] = function()
    ensure()
    return _reach[slug] and 1 or 0
  end
end

print(string.format("[ER-AP] logic ready: %d regions, %d gate codes", #REGION_ALL, #REGION_GATE_CODES))
