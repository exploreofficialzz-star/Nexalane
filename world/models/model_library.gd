extends RefCounted
class_name ModelLibrary

## Loads the generated GLB models (assets/models/<id>.glb), caches the imported scenes and patches
## materials after instancing:
##  * "glow"      -> shared unshaded vertex-colour material with HDR energy (so it blooms)
##  * "facade_X"  -> shared textured facade material (albedo + emissive windows + roughness/metal)

const PATH := "res://assets/models/%s.glb"

static var _scenes: Dictionary = {}

static func exists(model_id: String) -> bool:
	return ResourceLoader.exists(PATH % model_id)

static func instantiate(model_id: String, cast_shadows: bool = false) -> Node3D:
	var packed := _packed(model_id)
	if packed == null:
		return null
	var node := packed.instantiate() as Node3D
	if node == null:
		return null
	_post_process(node, cast_shadows)
	return node

static func _packed(model_id: String) -> PackedScene:
	if _scenes.has(model_id):
		return _scenes[model_id] as PackedScene
	var packed: PackedScene = null
	var path := PATH % model_id
	if ResourceLoader.exists(path):
		packed = load(path) as PackedScene
	_scenes[model_id] = packed
	return packed

static func _post_process(root: Node, cast_shadows: bool) -> void:
	for child in root.get_children():
		if child is MeshInstance3D:
			var mi := child as MeshInstance3D
			mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON if cast_shadows else GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			if mi.mesh != null:
				for i in mi.mesh.get_surface_count():
					var mat := mi.mesh.surface_get_material(i)
					if mat == null:
						continue
					var mat_name := mat.resource_name
					if mat_name == "glow":
						mi.set_surface_override_material(i, MaterialLibrary.glow_vertex())
					elif mat_name.begins_with("facade_"):
						mi.set_surface_override_material(i, MaterialLibrary.facade(mat_name.substr(7, 1)))
		_post_process(child, cast_shadows)

## Applies a distance cull to every mesh below `root` (cheap way to keep draw calls down).
static func set_visibility_range(root: Node, range_end: float) -> void:
	for child in root.get_children():
		if child is GeometryInstance3D:
			var gi := child as GeometryInstance3D
			gi.visibility_range_end = range_end
			gi.visibility_range_end_margin = 12.0
		set_visibility_range(child, range_end)
