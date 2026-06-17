-- Elden Ring Archipelago PopTracker pack -- entry point (M1 + M3a base map + M3c DLC map).
-- Pairs with tools/gen_poptracker.py + tools/build_map.py + tools/dlc_map.py
-- (regenerate on apworld/dump changes).

-- Generated logic data first, then the logic that consumes it.
ScriptHost:LoadScript("scripts/region_graph.lua")
ScriptHost:LoadScript("scripts/logic.lua")

-- Generated, churn-prone pack data (do NOT hand-edit; run tools/gen_poptracker.py):
Tracker:AddItems("items/items.json")
Tracker:AddLocations("locations/locations.json")  -- carries map_locations pins for the map variants

-- Shared generated item grid (referenced by every variant layout):
Tracker:AddLayouts("layouts/item_grid.json")

-- Variant-specific view. Each layout file defines "tracker_default"; load exactly one.
if Tracker.ActiveVariantUID == "map" then
  Tracker:AddMaps("maps/maps.json")              -- generated maps (Lands Between + Land of Shadow)
  Tracker:AddLayouts("layouts/map.json")          -- Lands Between map widget + item grid
elseif Tracker.ActiveVariantUID == "dlc_only" then
  Tracker:AddMaps("maps/maps.json")
  Tracker:AddLayouts("layouts/map_dlc.json")      -- Land of Shadow map widget + item grid
else
  Tracker:AddLayouts("layouts/items_only.json")   -- list-only (no map art)
end

-- Generated id tables (authoritative; ap_code == AP network id):
ScriptHost:LoadScript("scripts/ap_map.lua")    -- AP_ITEM_ID_TO_CODE
ScriptHost:LoadScript("scripts/loc_map.lua")   -- AP_LOC_ID_TO_SECTION
ScriptHost:LoadScript("scripts/loc_dlc.lua")   -- AP_LOC_DLC (DLC check ids; dlc_only auto-clear)

-- Auto-tracking (Archipelago) glue:
ScriptHost:LoadScript("scripts/autotracking.lua")
