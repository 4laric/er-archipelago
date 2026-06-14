-- Archipelago auto-tracking glue (M1).
--
-- Authoritative + id-keyed via the GENERATED tables (tools/gen_poptracker.py reads the apworld's
-- real ap_codes): AP_ITEM_ID_TO_CODE for items, AP_LOC_ID_TO_SECTION for checks. No datapackage
-- or name-matching. Reachability lives in logic.lua (region graph); on_clear sets WORLD_LOGIC.

print("ER-AP autotracking loaded (M1)")

AP_ITEM_ID_TO_CODE   = AP_ITEM_ID_TO_CODE or {}
AP_LOC_ID_TO_SECTION = AP_LOC_ID_TO_SECTION or {}

-- ---- slot_data -> reachability model -------------------------------------------------------
function on_clear(slot_data)
  local opt = (slot_data and slot_data["options"]) or {}
  WORLD_LOGIC = opt["world_logic"]                 -- logic.lua reads this (nil => gating on)
  ENABLE_DLC  = opt["enable_dlc"]
  print(string.format("slot connected | world_logic=%s enable_dlc=%s ending=%s great_runes=%s",
    tostring(WORLD_LOGIC), tostring(ENABLE_DLC), tostring(opt["ending_condition"]),
    tostring(opt["great_runes_required"])))
end

-- ---- received items (id-keyed) -------------------------------------------------------------
function on_item(item_id)
  local code = AP_ITEM_ID_TO_CODE[item_id]
  if not code then return end
  local obj = Tracker:FindObjectForCode(code)
  if not obj then return end
  if obj.Type == "toggle" or obj.Type == "toggle_badged" then
    obj.Active = true
  elseif obj.Type == "consumable" then
    obj.AcquiredCount = math.min((obj.AcquiredCount or 0) + 1, obj.MaxQuantity or 99)
  end
end

-- ---- location checks (id-keyed, exact section clear) ---------------------------------------
function on_location(location_id)
  local code = AP_LOC_ID_TO_SECTION[location_id]   -- "@Region/Section" (slashes sanitized in gen)
  if not code then return end
  local obj = Tracker:FindObjectForCode(code)
  if obj then obj.AvailableChestCount = 0 end
end

-- ---- register handlers ---------------------------------------------------------------------
if Archipelago then
  Archipelago:AddClearHandler("on_clear", on_clear)
  Archipelago:AddItemHandler("on_item", on_item)
  Archipelago:AddLocationHandler("on_location", on_location)
else
  print("Archipelago interface unavailable (offline/manual mode)")
end
