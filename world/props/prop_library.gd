extends RefCounted
class_name PropLibrary

## Scenery generator for one track chunk. All randomness comes from the RNG passed in, which TrackManager
## seeds per chunk, so scenery never influences the (gameplay-critical) obstacle sequence.
## Buildings are authored with their street face on -Z; the left side of the road is rotated -90 degrees about
## Y and the right side +90 degrees so that face looks at the road.

const SIDEWALK_X := 7.3
const BUILDING_FACE_X := 9.6

const DISTRICT_BUILDINGS := {
	"old_quarter": ["building_c", "building_c", "building_a", "building_d"],
	"transit_core": ["building_a", "building_b", "building_a", "building_b"],
	"harbor_arc": ["building_d", "building_a", "building_d", "building_c"],
	"industrial_belt": ["building_d", "building_d", "building_a", "building_d"],
	"skyline_works": ["building_a", "building_b", "building_b", "building_a"],
	"neon_market": ["building_c", "building_a", "building_b", "building_c"],
	"stormline": ["building_a", "building_d", "building_a", "building_b"],
	"central_spire": ["building_b", "building_b", "building_a", "building_b"]
}
const BUILDING_DIMS := {  # (frontage along the road, depth away from the road)
	"building_a": Vector2(12.8, 12.8), "building_b": Vector2(12.8, 12.8),
	"building_c": Vector2(12.8, 9.6), "building_d": Vector2(19.2, 12.8)
}
const FAR_BUILDINGS := ["building_far_a", "building_far_b", "building_far_c", "building_far_d"]
const NEON_BY_DISTRICT := {
	"old_quarter": "neon_sign_a", "transit_core": "neon_sign_b", "harbor_arc": "neon_sign_b", "industrial_belt": "neon_sign_a",
	"skyline_works": "neon_sign_b", "neon_market": "neon_sign_c", "stormline": "neon_sign_b", "central_spire": "neon_sign_b"
}
const NEON_COLORS := {"neon_sign_a": Color(1.0, 0.45, 0.12), "neon_sign_b": Color(0.15, 0.8, 1.0), "neon_sign_c": Color(1.0, 0.2, 0.65)}

static func decorate(root: Node3D, district: Dictionary, length: float, random: RandomNumberGenerator, density: float, chunk_index: int) -> void:
	var district_id := str(district["id"])
	_buildings(root, district_id, length, random, density)
	_street_lights(root, length, random, chunk_index, district)
	_signs(root, district_id, length, random, density)
	_district_props(root, district_id, length, random, density, chunk_index)

static func _place(root: Node3D, model_id: String, pos: Vector3, side: int, visible_range: float, shadows: bool = false) -> Node3D:
	var node := ModelLibrary.instantiate(model_id, shadows)
	if node == null:
		return null
	node.position = pos
	node.rotation.y = float(side) * PI * 0.5            # -Z (street face) -> looks at the road
	ModelLibrary.set_visibility_range(node, visible_range)
	root.add_child(node)
	return node

static func _buildings(root: Node3D, district_id: String, length: float, random: RandomNumberGenerator, density: float) -> void:
	var palette: Array = DISTRICT_BUILDINGS.get(district_id, DISTRICT_BUILDINGS["old_quarter"])
	for side in [-1, 1]:
		var cursor := random.randf_range(0.0, 3.0)
		while cursor < length:
			var kind := str(palette[random.randi_range(0, palette.size() - 1)])
			var dims: Vector2 = BUILDING_DIMS[kind]
			var skip := random.randf() > density or random.randf() < 0.08      # alleys / low-detail devices
			if not skip:
				_place(root, kind, Vector3(float(side) * (BUILDING_FACE_X + dims.y * 0.5), 0.0, cursor + dims.x * 0.5), side, 200.0)
			cursor += dims.x + random.randf_range(0.2, 2.6)
		# second tier: tall towers far from the road (fog turns them into a skyline)
		var far_count := 1 if density < 0.7 else 2
		for i in far_count:
			var far_kind := str(FAR_BUILDINGS[random.randi_range(0, FAR_BUILDINGS.size() - 1)])
			var far_node := ModelLibrary.instantiate(far_kind, false)
			if far_node != null:
				far_node.position = Vector3(float(side) * random.randf_range(32.0, 64.0), 0.0, random.randf_range(0.0, length))
				far_node.rotation.y = float(random.randi_range(0, 3)) * PI * 0.5
				ModelLibrary.set_visibility_range(far_node, 340.0)
				root.add_child(far_node)

static func _street_lights(root: Node3D, length: float, random: RandomNumberGenerator, chunk_index: int, district: Dictionary) -> void:
	var accent: Color = district["accent"]
	var warm := Color(1.0, 0.82, 0.55, 0.55).lerp(Color(accent.r, accent.g, accent.b, 0.55), 0.18)
	for k in 2:
		var side := -1 if (chunk_index + k) % 2 == 0 else 1
		var z := length * (0.25 + 0.5 * float(k)) + random.randf_range(-2.0, 2.0)
		var lamp := _place(root, "street_light", Vector3(float(side) * SIDEWALK_X, 0.0, z), side, 190.0, false)
		if lamp == null:
			continue
		var head := Vector3(float(side) * (SIDEWALK_X - 2.9), 7.55, z)
		_light_pool(root, Vector3(head.x, 0.04, z), Vector2(9.5, 9.5), warm)
		_halo(root, head, 3.4, Color(1.0, 0.9, 0.7, 0.8))

static func _signs(root: Node3D, district_id: String, length: float, random: RandomNumberGenerator, density: float) -> void:
	var count := 2 if (district_id == "neon_market" and density > 0.7) else 1
	for i in count:
		var side := -1 if random.randf() < 0.5 else 1
		var model_id := str(NEON_BY_DISTRICT.get(district_id, "neon_sign_b"))
		var z := random.randf_range(6.0, maxf(7.0, length - 6.0))
		var sign := _place(root, model_id, Vector3(float(side) * (BUILDING_FACE_X - 0.1), 0.0, z), side, 170.0)
		if sign == null:
			continue
		var c: Color = NEON_COLORS[model_id]
		_light_pool(root, Vector3(float(side) * 5.4, 0.045, z), Vector2(5.5, 8.5), Color(c.r, c.g, c.b, 0.42))
		_halo(root, Vector3(float(side) * (BUILDING_FACE_X - 1.4), 5.4, z), 4.4, Color(c.r, c.g, c.b, 0.55))

static func _district_props(root: Node3D, district_id: String, length: float, random: RandomNumberGenerator, density: float, chunk_index: int) -> void:
	var side := -1 if random.randf() < 0.5 else 1
	var z := random.randf_range(4.0, maxf(5.0, length - 12.0))
	match district_id:
		"old_quarter":
			_place(root, "prop_market_stall", Vector3(float(side) * 7.7, 0.0, z), side, 150.0)
		"neon_market":
			_place(root, "prop_market_stall", Vector3(float(side) * 7.7, 0.0, z), side, 150.0)
			_place(root, "prop_market_stall", Vector3(float(-side) * 7.7, 0.0, z + 11.0), -side, 150.0)
		"transit_core":
			for k in 2:
				var s := -1 if (chunk_index + k) % 2 == 0 else 1
				_place(root, "prop_catenary_pole", Vector3(float(s) * 6.6, 0.0, length * (0.2 + 0.5 * float(k))), s, 170.0)
		"harbor_arc":
			_place(root, "prop_container_stack", Vector3(float(side) * 15.5, 0.0, z), 0, 220.0, false)
			if chunk_index % 3 == 0:
				_far_piece(root, "setpiece_crane", side, random, length)
		"industrial_belt":
			_place(root, "prop_pipe_rack", Vector3(float(side) * 8.4, 0.0, z), 0, 170.0)
			if chunk_index % 2 == 0:
				_far_piece(root, "prop_chimney", -side, random, length)
		"skyline_works":
			_place(root, "prop_scaffold", Vector3(float(side) * 9.1, 0.0, z), side, 170.0)
			if chunk_index % 3 == 1:
				_far_piece(root, "setpiece_crane", side, random, length)
		"central_spire":
			if chunk_index % 4 == 0:
				_far_piece(root, "setpiece_spire", side, random, length)
	if density > 0.7:
		for k in 3:
			_place(root, "prop_bollard", Vector3(float(side) * 5.9, 0.0, 6.0 + float(k) * 14.0), 0, 70.0)

static func _far_piece(root: Node3D, model_id: String, side: int, random: RandomNumberGenerator, length: float) -> void:
	var node := ModelLibrary.instantiate(model_id, false)
	if node == null:
		return
	node.position = Vector3(float(side) * random.randf_range(30.0, 44.0), 0.0, random.randf_range(0.0, length))
	ModelLibrary.set_visibility_range(node, 360.0)
	root.add_child(node)

static func _light_pool(root: Node3D, pos: Vector3, size: Vector2, color: Color) -> void:
	var m := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = size
	m.mesh = plane
	m.position = pos
	m.material_override = MaterialLibrary.additive_sprite(color, "res://assets/vfx/vfx_light_pool.png", false)
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	m.visibility_range_end = 150.0
	root.add_child(m)

static func _halo(root: Node3D, pos: Vector3, size: float, color: Color) -> void:
	var m := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(size, size)
	m.mesh = quad
	m.position = pos
	m.material_override = MaterialLibrary.additive_sprite(color, "res://assets/vfx/vfx_glow.png", true)
	m.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	m.visibility_range_end = 170.0
	root.add_child(m)
