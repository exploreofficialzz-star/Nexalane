extends Node
class_name DeviceProfileServiceImpl

signal profile_changed(profile: String)

var profile := "MID"
var fps_cap := 60
var particle_budget := 140
var shadows_enabled := true
var glow_enabled := false
var msaa_level := 0            # 0 off, 1 = 2x, 2 = 4x
var render_scale := 1.0
var prop_density := 1.0        # 0..1 multiplier for optional scenery

func _ready() -> void:
	refresh()

func refresh() -> void:
	var preference := "auto"
	if SaveService != null and SaveService.data.has("settings"):
		preference = str(SaveService.data["settings"].get("graphics", "auto")).to_lower()
	var detected := _detect()
	var chosen := detected if preference not in ["low", "mid", "high"] else preference.to_upper()
	_apply(chosen)

func _detect() -> String:
	var size := DisplayServer.window_get_size()
	var long_edge := maxi(size.x, size.y)
	if OS.has_feature("mobile"):
		return "LOW" if long_edge < 1200 else "MID"
	return "HIGH"

func _apply(next_profile: String) -> void:
	profile = next_profile
	match profile:
		"LOW":
			fps_cap = 45
			particle_budget = 60
			shadows_enabled = false
			glow_enabled = false
			msaa_level = 0
			render_scale = 0.8
			prop_density = 0.55
		"HIGH":
			fps_cap = 120
			particle_budget = 240
			shadows_enabled = true
			glow_enabled = true
			msaa_level = 2
			render_scale = 1.0
			prop_density = 1.0
		_:
			profile = "MID"
			fps_cap = 60
			particle_budget = 140
			shadows_enabled = true
			glow_enabled = false
			msaa_level = 0
			render_scale = 1.0
			prop_density = 0.85
	Engine.max_fps = fps_cap
	profile_changed.emit(profile)

func apply_to_viewport(viewport: Viewport) -> void:
	if viewport == null:
		return
	match msaa_level:
		0: viewport.msaa_3d = Viewport.MSAA_DISABLED
		1: viewport.msaa_3d = Viewport.MSAA_2X
		_: viewport.msaa_3d = Viewport.MSAA_4X
	# The Compatibility (OpenGL) renderer has no 3D resolution scaling, so only ask for it on Vulkan renderers.
	var scale_supported := RenderingServer.get_current_rendering_method() != "gl_compatibility"
	viewport.scaling_3d_scale = render_scale if scale_supported else 1.0

func particle_count(default_count: int) -> int:
	return mini(default_count, particle_budget)
