// AUTO-GENERATED from eldenring_gf/contract.py -- do not edit by hand.
// The apworld<->client slot_data contract, mirrored so the client validates the same shapes.
use serde_json::Value;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Shape {
    Any,
    Bool,
    BoolOrInt,
    IntList,
    ListvalIntMap,
    NestedGrants,
    ScalarIntMap,
    Str,
    TripleList,
}

pub struct ContractKey {
    pub name: &'static str,
    pub shape: Shape,
    pub required: bool,
    pub greenfield: bool,
}

pub const CONTRACT: &[ContractKey] = &[
    ContractKey { name: "apIdsToItemIds", shape: Shape::ScalarIntMap, required: true, greenfield: true },
    ContractKey { name: "locationFlags", shape: Shape::ScalarIntMap, required: true, greenfield: true },
    ContractKey { name: "regionOpenFlags", shape: Shape::ScalarIntMap, required: true, greenfield: true },
    ContractKey { name: "regionSphereTargets", shape: Shape::Any, required: false, greenfield: true },
    ContractKey { name: "areaLockFlags", shape: Shape::TripleList, required: true, greenfield: true },
    ContractKey { name: "lockRevealFlags", shape: Shape::ListvalIntMap, required: false, greenfield: true },
    ContractKey { name: "regionGraces", shape: Shape::ListvalIntMap, required: false, greenfield: true },
    ContractKey { name: "graceItems", shape: Shape::ScalarIntMap, required: false, greenfield: true },
    ContractKey { name: "startRegion", shape: Shape::Str, required: true, greenfield: true },
    ContractKey { name: "startGraces", shape: Shape::IntList, required: false, greenfield: true },
    ContractKey { name: "startItems", shape: Shape::IntList, required: false, greenfield: true },
    ContractKey { name: "reveal_all_maps", shape: Shape::Bool, required: false, greenfield: true },
    ContractKey { name: "goalLocations", shape: Shape::IntList, required: true, greenfield: true },
    ContractKey { name: "checkItemFlags", shape: Shape::ListvalIntMap, required: false, greenfield: true },
    ContractKey { name: "shopRowFlags", shape: Shape::ScalarIntMap, required: false, greenfield: true },
    ContractKey { name: "shopPreviewGoods", shape: Shape::ScalarIntMap, required: false, greenfield: true },
    ContractKey { name: "dungeonSweepFlags", shape: Shape::ListvalIntMap, required: false, greenfield: true },
    ContractKey { name: "progressiveGrants", shape: Shape::NestedGrants, required: false, greenfield: true },
    ContractKey { name: "death_link", shape: Shape::BoolOrInt, required: false, greenfield: true },
    ContractKey { name: "enable_dlc", shape: Shape::BoolOrInt, required: false, greenfield: true },
    ContractKey { name: "world_logic", shape: Shape::Str, required: false, greenfield: true },
    ContractKey { name: "locationIdsToKeys", shape: Shape::Any, required: false, greenfield: false },
    ContractKey { name: "naturalKeyTriggers", shape: Shape::Any, required: false, greenfield: false },
    ContractKey { name: "lockGrantItems", shape: Shape::Any, required: false, greenfield: false },
    ContractKey { name: "dungeonSweeps", shape: Shape::Any, required: false, greenfield: false },
    ContractKey { name: "itemCounts", shape: Shape::Any, required: false, greenfield: false },
];

fn is_int(v: &Value) -> bool { v.is_i64() || v.is_u64() }

fn shape_ok(shape: Shape, v: &Value) -> bool {
    match shape {
        Shape::ScalarIntMap => v.as_object().map_or(false, |o| o.values().all(is_int)),
        Shape::ListvalIntMap => v.as_object().map_or(false, |o| {
            o.values().all(|x| x.as_array().map_or(false, |a| a.iter().all(is_int)))
        }),
        Shape::TripleList => v.as_array().map_or(false, |a| {
            a.iter().all(|t| t.as_array().map_or(false, |t| t.len() == 3 && t.iter().all(is_int)))
        }),
        Shape::IntList => v.as_array().map_or(false, |a| a.iter().all(is_int)),
        Shape::Bool => v.is_boolean(),
        Shape::BoolOrInt => v.is_boolean() || v.as_i64().map_or(false, |n| n == 0 || n == 1),
        Shape::Str => v.is_string(),
        Shape::NestedGrants => v.as_object().map_or(false, |o| {
            o.values().all(|l| l.as_array().map_or(false, |l| l.iter().all(|e| {
                e.get("goods").map_or(false, is_int)
                    && e.get("flags").and_then(|f| f.as_array())
                        .map_or(false, |f| f.iter().all(is_int))
            })))
        }),
        Shape::Any => true,
    }
}

/// Validate an assembled slot_data object against the greenfield contract. Returns the list of
/// problems (missing-required + shape mismatches); empty == clean. Mirrors contract.py.
pub fn validate(sd: &Value) -> Vec<String> {
    let mut out = Vec::new();
    for k in CONTRACT {
        if !k.greenfield { continue; }
        match sd.get(k.name) {
            None => if k.required { out.push(format!("MISSING required key '{}'", k.name)); },
            Some(v) => if !shape_ok(k.shape, v) {
                out.push(format!("SHAPE '{}' expected {:?}", k.name, k.shape));
            },
        }
    }
    out
}
