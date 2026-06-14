-- Elden Ring Archipelago PopTracker pack — entry point (M1).
-- Pairs with tools/gen_poptracker.py (regenerate items/locations/id-maps/region-graph on changes).

-- Generated logic data first, then the logic that consumes it.
ScriptHost:LoadScript("scripts/region_graph.lua")
ScriptHost:LoadScript("scripts/logic.lua")

-- Generated, churn-prone pack data (do NOT hand-edit; run tools/gen_poptracker.py):
Tracker:AddItems("items/items.json")
Tracker:AddLocations("locations/locations.json")

-- Layouts: item_grid.json is GENERATED; items_only.json is the stable hand-authored wrapper.
Tracker:AddLayouts("layouts/item_grid.json")
Tracker:AddLayouts("layouts/items_only.json")

-- Generated id tables (authoritative; ap_code == AP network id):
ScriptHost:LoadScript("scripts/ap_map.lua")    -- AP_ITEM_ID_TO_CODE
ScriptHost:LoadScript("scripts/loc_map.lua")   -- AP_LOC_ID_TO_SECTION

-- Auto-tracking (Archipelago) glue:
ScriptHost:LoadScript("scripts/autotracking.lua")
