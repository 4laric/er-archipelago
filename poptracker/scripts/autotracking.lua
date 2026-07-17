-- Archipelago auto-tracking glue for the ER-AP PopTracker pack.
-- Registers the AP handlers and threads slot_data into the logic flags. Loads AFTER ap_map.lua,
-- loc_map.lua, loc_dlc.lua and logic.lua (see init.lua), so the id tables and logic_invalidate()
-- are already defined.
--
-- dlc_only support (the point of this build): on connect to a dlc_only seed every NON-DLC check is
-- auto-cleared, because the apworld keeps base-game locations only as locked-vanilla transit with no
-- checks -- they are never sent and would otherwise sit forever as phantom outstanding sections.
-- Mechanism = auto-clear on connect (set AvailableChestCount = 0), the same call on_location uses.
-- Back-compat: a missing slot_data key is treated as 0, so older servers behave exactly as before.

local function num(opt, key)
  local v = opt and opt[key]
  if v == true then return 1 end
  if v == false then return 0 end
  return tonumber(v) or 0
end

local function clear_section(code)
  local s = Tracker:FindObjectForCode(code)
  if s and s.AvailableChestCount ~= nil then
    s.AvailableChestCount = 0
    return true
  end
  return false
end

-- Mark every non-DLC check done (dlc_only: base regions carry no real checks on this seed).
local function dlc_only_autoclear()
  local cleared, total = 0, 0
  for ap_id, code in pairs(AP_LOC_ID_TO_SECTION) do
    total = total + 1
    if not AP_LOC_DLC[ap_id] then
      if clear_section(code) then cleared = cleared + 1 end
    end
  end
  print(string.format("[ER-AP] dlc_only: auto-cleared %d/%d non-DLC checks", cleared, total))
end

function on_clear(slot_data)
  local opt = (slot_data and slot_data.options) or {}
  WORLD_LOGIC    = num(opt, "world_logic")
  WORLD_DLC_ONLY = num(opt, "dlc_only")
  WORLD_ENABLE_DLC = num(opt, "enable_dlc")
  WORLD_POOL     = num(opt, "location_pool")
  if logic_invalidate then logic_invalidate() end
  print(string.format("[ER-AP] clear: world_logic=%d dlc_only=%d enable_dlc=%d location_pool=%d",
    WORLD_LOGIC, WORLD_DLC_ONLY, WORLD_ENABLE_DLC, WORLD_POOL))
  if WORLD_DLC_ONLY == 1 then
    dlc_only_autoclear()
  end
end

-- PopTracker AP item handler. Signature: (index, item_id, item_name, player_number).
function on_item(index, item_id, item_name, player_number)
  local code = AP_ITEM_ID_TO_CODE[item_id]
  if not code then return end
  local o = Tracker:FindObjectForCode(code)
  if not o then return end
  if o.Type == "toggle" then
    o.Active = true
  elseif o.Type == "consumable" then
    o.AcquiredCount = (o.AcquiredCount or 0) + 1
  elseif o.Type == "progressive" then
    o.CurrentStage = (o.CurrentStage or 0) + 1
  elseif o.Active ~= nil then
    o.Active = true
  end
end

-- PopTracker AP location handler. Signature: (location_id, location_name).
function on_location(location_id, location_name)
  local code = AP_LOC_ID_TO_SECTION[location_id]
  if code then clear_section(code) end
end

if Archipelago then
  Archipelago:AddClearHandler("clear", on_clear)
  Archipelago:AddItemHandler("item", on_item)
  Archipelago:AddLocationHandler("location", on_location)
  print("[ER-AP] autotracking handlers registered")
else
  print("[ER-AP] WARNING: Archipelago interface not available; autotracking disabled")
end
