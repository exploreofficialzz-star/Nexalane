extends RefCounted
class_name MaterialLibrary

## Shared, lazily created materials. Everything is cached so thousands of props reuse a handful of materials.

static var _cache: Dictionary = {}

static func _tex(path: String) -> Texture2D:
	return load(path) as Texture2D

static func ground(wet: bool, length_m: float, tint: Color) -> StandardMaterial3D:
	var key := "ground|%s|%d|%s" % [str(wet), int(round(length_m)), tint.to_html(false)]
	if _cache.has(key):
		return _cache[key] as StandardMaterial3D
	var base := "res://assets/textures/env_asphalt_%s" % ("wet" if wet else "dry")
	var m := StandardMaterial3D.new()
	m.albedo_texture = _tex(base + ".png")
	m.albedo_color = Color.WHITE.lerp(tint, 0.10)
	m.roughness = 1.0
	m.roughness_texture = _tex(base + "_r.png")
	m.normal_enabled = true
	m.normal_texture = _tex(base + "_n.png")
	m.normal_scale = 1.0
	m.uv1_scale = Vector3(1.0, length_m / 9.0, 1.0)          # the road tile is 18 m x 9 m
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	if wet:
		m.emission_enabled = true
		m.emission_texture = _tex(base + "_e.png")
		m.emission_energy_multiplier = 0.9
	_cache[key] = m
	return m

static func facade(kind: String) -> StandardMaterial3D:
	var key := "facade|" + kind
	if _cache.has(key):
		return _cache[key] as StandardMaterial3D
	var base := "res://assets/textures/env_facade_%s" % kind
	var m := StandardMaterial3D.new()
	m.albedo_texture = _tex(base + ".png")
	m.emission_enabled = true
	m.emission_texture = _tex(base + "_e.png")
	m.emission_energy_multiplier = 1.8
	m.roughness = 1.0
	m.roughness_texture = _tex(base + "_mr.png")
	m.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_GREEN
	m.metallic = 1.0
	m.metallic_texture = _tex(base + "_mr.png")
	m.metallic_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_BLUE
	m.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
	_cache[key] = m
	return m

## Unshaded vertex-colour material used for every "glow" surface of the generated models.
static func glow_vertex(energy: float = 2.4) -> StandardMaterial3D:
	var key := "glow_vertex|%.2f" % energy
	if _cache.has(key):
		return _cache[key] as StandardMaterial3D
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.vertex_color_use_as_albedo = true
	m.albedo_color = Color(energy, energy, energy, 1.0)
	_cache[key] = m
	return m

## Additive, unshaded, depth-write-free sprite (light pools, halos, trails). Pass shared=false when the
## caller will modify the material afterwards.
static func additive_sprite(color: Color, texture_path: String, billboard: bool, shared: bool = true) -> StandardMaterial3D:
	var key := "additive|%s|%s|%s" % [color.to_html(true), texture_path, str(billboard)]
	if shared and _cache.has(key):
		return _cache[key] as StandardMaterial3D
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.blend_mode = BaseMaterial3D.BLEND_MODE_ADD
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	m.albedo_texture = _tex(texture_path)
	m.albedo_color = color
	if billboard:
		m.billboard_mode = BaseMaterial3D.BILLBOARD_ENABLED
	if shared:
		_cache[key] = m
	return m

## Holographic route sign (alpha blended, unshaded, slightly over-bright so it blooms).
static func route_decal(route_class: String) -> StandardMaterial3D:
	var key := "decal|" + route_class
	if _cache.has(key):
		return _cache[key] as StandardMaterial3D
	var path := "res://assets/decals/route_%s.png" % route_class.to_lower()
	if route_class == "SPIRE":
		path = "res://assets/decals/district_spire.png"
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.albedo_texture = _tex(path)
	m.albedo_color = Color(1.5, 1.5, 1.5, 1.0)
	_cache[key] = m
	return m

## Far city silhouette plane. Fog is disabled so the skyline stays readable; the tint follows the district.
static func skyline(layer: String, tint: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.disable_fog = true
	m.albedo_texture = _tex("res://assets/textures/env_skyline_%s.png" % layer)
	m.albedo_color = tint
	return m
