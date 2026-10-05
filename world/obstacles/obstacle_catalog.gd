extends RefCounted
class_name ObstacleCatalog

## What the player must do about an obstacle:
## JUMP  - low enough to hop over (<= 1.1 m)
## SLIDE - hangs at 1.05 m or higher: slide (0.95 m tall) underneath, standing or jumping hits it
## DODGE - too tall / too long: change lane
enum Kind { JUMP, SLIDE, DODGE }

## Order matches ContentRegistry.obstacle_families() so ids like "wet_bridge_13" stay valid.
const FAMILY_ORDER := ["barrier", "traffic", "train", "low_beam", "gap", "drone", "gate", "container", "crane", "steam", "forklift", "laser", "wet_bridge", "market_cart", "scooter"]

## size = collider (width, height, depth); y = collider bottom above the road.
const FAMILIES := {
	"barrier":     {"model": "obstacle_barrier",   "kind": Kind.JUMP,  "size": Vector3(2.4, 1.0, 0.8),  "y": 0.0},
	"traffic":     {"model": "obstacle_traffic",   "kind": Kind.DODGE, "size": Vector3(1.9, 1.7, 4.2),  "y": 0.0},
	"train":       {"model": "obstacle_train",     "kind": Kind.DODGE, "size": Vector3(2.8, 3.4, 7.8),  "y": 0.0},
	"low_beam":    {"model": "obstacle_beam",      "kind": Kind.SLIDE, "size": Vector3(3.0, 1.3, 0.7),  "y": 1.05},
	"gap":         {"model": "obstacle_trench",    "kind": Kind.JUMP,  "size": Vector3(2.7, 0.6, 2.2),  "y": 0.0},
	"drone":       {"model": "obstacle_drone",     "kind": Kind.SLIDE, "size": Vector3(1.5, 0.7, 1.5),  "y": 1.15},
	"gate":        {"model": "obstacle_gate",      "kind": Kind.SLIDE, "size": Vector3(3.0, 1.25, 0.5), "y": 1.05},
	"container":   {"model": "obstacle_container", "kind": Kind.DODGE, "size": Vector3(2.3, 2.6, 5.8),  "y": 0.0},
	"crane":       {"model": "obstacle_crane",     "kind": Kind.SLIDE, "size": Vector3(1.9, 1.5, 1.9),  "y": 1.05},
	"steam":       {"model": "obstacle_steam",     "kind": Kind.DODGE, "size": Vector3(1.5, 1.9, 1.5),  "y": 0.0},
	"forklift":    {"model": "obstacle_forklift",  "kind": Kind.DODGE, "size": Vector3(1.5, 2.2, 3.4),  "y": 0.0},
	"laser":       {"model": "obstacle_laser",     "kind": Kind.JUMP,  "size": Vector3(2.8, 0.45, 0.3), "y": 0.15},
	"wet_bridge":  {"model": "obstacle_ramp",      "kind": Kind.JUMP,  "size": Vector3(2.7, 0.6, 2.9),  "y": 0.0},
	"market_cart": {"model": "obstacle_cart",      "kind": Kind.JUMP,  "size": Vector3(1.7, 1.1, 1.1),  "y": 0.0},
	"scooter":     {"model": "obstacle_scooter",   "kind": Kind.JUMP,  "size": Vector3(0.9, 1.05, 1.8), "y": 0.0}
}

## Which families dress each district (all three kinds are always available so patterns stay varied).
const DISTRICT_FAMILIES := {
	"old_quarter": ["barrier", "scooter", "market_cart", "traffic", "gap", "low_beam"],
	"transit_core": ["barrier", "train", "gate", "laser", "drone", "traffic"],
	"harbor_arc": ["container", "crane", "forklift", "wet_bridge", "barrier", "steam"],
	"industrial_belt": ["steam", "forklift", "crane", "container", "laser", "gap", "barrier"],
	"skyline_works": ["crane", "gate", "drone", "barrier", "low_beam", "laser"],
	"neon_market": ["market_cart", "scooter", "drone", "laser", "gate", "traffic"],
	"stormline": ["barrier", "wet_bridge", "drone", "traffic", "gap", "laser"],
	"central_spire": ["gate", "drone", "laser", "train", "low_beam", "barrier"]
}

static func definition(family: String) -> Dictionary:
	return FAMILIES.get(family, FAMILIES["barrier"])

static func kind_of(family: String) -> int:
	return int(definition(family)["kind"])

static func depth_of(family: String) -> float:
	var size: Vector3 = definition(family)["size"]
	return size.z

## "wet_bridge_13" -> "wet_bridge"
static func family_of(obstacle_id: String) -> String:
	var cut := obstacle_id.rfind("_")
	var family := obstacle_id.substr(0, cut) if cut > 0 else obstacle_id
	return family if FAMILIES.has(family) else "barrier"

## Same numbering as ContentRegistry.obstacle_families(): family index + 15 * variant (variant 0..3).
static func obstacle_id(family: String, variant: int) -> String:
	var index := FAMILY_ORDER.find(family)
	if index < 0:
		index = 0
	return "%s_%02d" % [FAMILY_ORDER[index], index + 1 + 15 * clampi(variant, 0, 3)]

static func families_for(district_id: String, kind: int) -> Array[String]:
	var result: Array[String] = []
	for family in DISTRICT_FAMILIES.get(district_id, FAMILY_ORDER):
		if kind_of(str(family)) == kind:
			result.append(str(family))
	if result.is_empty():
		for family in FAMILY_ORDER:
			if kind_of(str(family)) == kind:
				result.append(str(family))
	return result
