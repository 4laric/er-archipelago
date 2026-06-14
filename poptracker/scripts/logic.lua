-- Region reachability logic (M1).
--
-- Consumes the GENERATED region_graph.lua (REGION_ADJ / REGION_LOCK_GATES / REGION_KEY_GATES /
-- REGION_GATE_CODES / REGION_ROOT). The generated locations.json gives every region node the access
-- rule "$can_reach_<slug>"; the metatable shim at the bottom routes all of them to can_reach().
--
-- Model: BFS from REGION_ROOT over REGION_ADJ. To enter a region you must satisfy its gates:
--   * KEY gates (Academy Glintstone Key, Rusty Key, shackles, ...) apply in ALL logic modes.
--   * LOCK gates (region_lock items) apply only when region gating is active (world_logic < 3).
-- Sub-regions inherit reachability automatically (a cave behind Caelid is reachable only once
-- Caelid itself is). Region-LEVEL only in M1; per-location item rules are M2 (need the apworld
-- declarative-rules refactor). A slug absent from the graph (1 known data gap) defaults to reachable
-- rather than greying out.

REGION_ADJ        = REGION_ADJ or {}
REGION_LOCK_GATES = REGION_LOCK_GATES or {}
REGION_KEY_GATES  = REGION_KEY_GATES or {}
REGION_GATE_CODES = REGION_GATE_CODES or {}
REGION_ROOT       = REGION_ROOT or "limgrave"
WORLD_LOGIC       = WORLD_LOGIC   -- set by autotracking.on_clear; nil before connect => gating on

-- Set of slugs the graph knows about (nodes + neighbors + gated regions).
local KNOWN = nil
local function known()
  if KNOWN then return KNOWN end
  KNOWN = {}
  for k, nbrs in pairs(REGION_ADJ) do
    KNOWN[k] = true
    for _, n in ipairs(nbrs) do KNOWN[n] = true end
  end
  for k in pairs(REGION_LOCK_GATES) do KNOWN[k] = true end
  for k in pairs(REGION_KEY_GATES) do KNOWN[k] = true end
  return KNOWN
end

local function gatingActive()
  if WORLD_LOGIC == nil then return true end
  local n = tonumber(WORLD_LOGIC)
  if n ~= nil then return n < 3 end                 -- 0/1/2 gate; 3 = open_world
  return tostring(WORLD_LOGIC) ~= "open_world"
end

local function hasItem(code)
  local o = Tracker:FindObjectForCode(code)
  if not o then return false end
  if o.Active == true then return true end
  return (o.AcquiredCount or 0) > 0
end

local function gatesOk(slug)
  local keys = REGION_KEY_GATES[slug]
  if keys then for _, c in ipairs(keys) do if not hasItem(c) then return false end end end
  if gatingActive() then
    local locks = REGION_LOCK_GATES[slug]
    if locks then for _, c in ipairs(locks) do if not hasItem(c) then return false end end end
  end
  return true
end

local function computeReachable()
  local reach, queue, head = {}, {}, 1
  if gatesOk(REGION_ROOT) then reach[REGION_ROOT] = true; queue[1] = REGION_ROOT end
  while head <= #queue do
    local cur = queue[head]; head = head + 1
    local nbrs = REGION_ADJ[cur]
    if nbrs then
      for _, nx in ipairs(nbrs) do
        if not reach[nx] and gatesOk(nx) then reach[nx] = true; queue[#queue + 1] = nx end
      end
    end
  end
  return reach
end

-- Cache the reachable set; recompute only when the collected-gate signature (or logic mode) changes.
-- Cheap (~50 gate lookups per call) and correct for both auto-tracking and manual item toggles.
local _sig, _reach
local function signature()
  local s = gatingActive() and "g" or "o"
  for _, c in ipairs(REGION_GATE_CODES) do if hasItem(c) then s = s .. "|" .. c end end
  return s
end

function can_reach(slug)
  if not known()[slug] then return AccessibilityLevel.Normal end   -- not in graph => no gating data
  local cur = signature()
  if cur ~= _sig then _reach = computeReachable(); _sig = cur end
  if _reach[slug] then return AccessibilityLevel.Normal end
  return AccessibilityLevel.None
end

-- PopTracker resolves "$can_reach_<slug>" to a global `can_reach_<slug>`; bind them all to
-- can_reach(slug) via __index so the generator doesn't emit 161 stubs.
setmetatable(_G, {
  __index = function(_, key)
    local slug = key:match("^can_reach_(.+)$")
    if slug then return function() return can_reach(slug) end end
    return nil
  end
})
