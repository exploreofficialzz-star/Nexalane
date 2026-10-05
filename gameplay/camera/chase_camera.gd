extends Camera3D
class_name ChaseCamera

## Third-person chase camera. It lives in the world (not under the runner) so lane changes only partially
## drag the view sideways, speed widens the FOV, and the runner's lean never rolls the picture.
## A cinematic "hero" framing is used while the menu is open and glides behind the runner when a run starts.

const GAME_OFFSET := Vector3(0.0, 3.45, -9.4)
const MENU_OFFSET := Vector3(2.3, 1.55, 5.2)           # front three-quarter view of the runner
const LOOK_AHEAD := 6.5
const BASE_FOV := 62.0
const MAX_FOV := 74.0
const LATERAL_FOLLOW := 0.62

var target: Node3D
var menu_mode := true
var shake := 0.0
var _blend := 0.0                     # 0 = menu framing, 1 = gameplay framing
var _speed_factor := 0.0
var _shake_time := 0.0

func _ready() -> void:
	near = 0.12
	far = 650.0
	fov = BASE_FOV
	current = true

func set_menu_mode(value: bool) -> void:
	menu_mode = value

func kick(strength: float) -> void:
	shake = maxf(shake, strength * AccessibilityService.shake_scale())

func snap() -> void:
	_blend = 0.0 if menu_mode else 1.0
	_apply(0.0, true)

func _physics_process(delta: float) -> void:
	_apply(delta, false)

func _apply(delta: float, immediate: bool) -> void:
	if target == null:
		return
	var goal := 0.0 if menu_mode else 1.0
	_blend = goal if immediate else move_toward(_blend, goal, delta * 1.25)
	var eased := smoothstep(0.0, 1.0, _blend)
	var pos := target.global_position
	var run_speed := 0.0
	if target is RunnerController:
		run_speed = (target as RunnerController).speed
	_speed_factor = lerpf(_speed_factor, clampf((run_speed - 14.0) / 18.0, 0.0, 1.0) if not menu_mode else 0.0, minf(1.0, delta * 2.0) if not immediate else 1.0)
	var cam_x := lerpf(pos.x * 0.35 + MENU_OFFSET.x, pos.x * LATERAL_FOLLOW, eased)
	var cam := Vector3(cam_x, lerpf(MENU_OFFSET.y, GAME_OFFSET.y, eased) + pos.y * 0.5, pos.z + lerpf(MENU_OFFSET.z, GAME_OFFSET.z, eased))
	var look_at_point := Vector3(lerpf(pos.x, pos.x * 0.8, eased), lerpf(1.25, 1.2, eased), pos.z + lerpf(0.0, LOOK_AHEAD, eased))
	global_position = cam
	look_at(look_at_point, Vector3.UP)
	fov = lerpf(lerpf(48.0, BASE_FOV, eased), MAX_FOV, _speed_factor * eased)

func _process(delta: float) -> void:
	if shake > 0.001:
		_shake_time += delta * 45.0
		h_offset = sin(_shake_time * 1.3) * shake * 0.12
		v_offset = cos(_shake_time * 1.7) * shake * 0.09
		shake = maxf(0.0, shake - delta * 2.4)
	else:
		h_offset = 0.0
		v_offset = 0.0
