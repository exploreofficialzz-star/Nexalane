extends Camera3D
class_name ChaseCamera

## Third-person chase camera, tuned like the classic 3-lane runners (Subway Surfers style):
##  * It looks straight down the track with a FIXED yaw and pitch - it never re-aims at the runner, so the runner's lane
##    changes slide it across the screen instead of whipping the picture around.
##  * Only the sideways and vertical follow are smoothed (frame-rate independent exponential damping); the distance
##    behind the runner is rigid, so the runner keeps the same size and place on screen at any speed.
##  * It runs every RENDERED frame and reads the runner's INTERPOLATED transform with physics interpolation switched off
##    for the camera itself.  That is the documented way to avoid camera / body jitter ("shaking") on 90 / 120 Hz phones.
##  * No positional or rotational shake.  A crash gives one soft zoom-and-tilt punch, a landing a small settle.
##  * The menu "hero" framing glides into the gameplay framing when a run starts.

const GAME_DISTANCE := 7.2             # metres behind the runner
const GAME_HEIGHT := 3.35              # metres above the track
const GAME_PITCH_DEG := 13.0           # look-down angle; puts the horizon near the top third of a portrait screen
const MENU_OFFSET := Vector3(2.3, 1.55, 5.2)           # front three-quarter view of the runner
const BASE_FOV := 58.0
const MENU_FOV := 46.0
const BOOST_FOV := 3.5                 # extra FOV while boosting / at top speed
const LATERAL_FOLLOW := 0.72           # share of the runner's sideways offset the camera follows
const LATERAL_RATE := 9.0              # 1 / seconds: how quickly the camera catches up sideways
const VERTICAL_FOLLOW := 0.30          # share of the runner's jump height the camera follows
const VERTICAL_RATE := 5.0
const STRETCH_MAX := 0.7               # extra distance (m) the camera falls back while accelerating

var target: Node3D
var menu_mode := true
var _blend := 0.0                      # 0 = menu framing, 1 = gameplay framing
var _cam_x := 0.0
var _cam_up := 0.0
var _stretch := 0.0
var _boost_fov := 0.0
var _impact := 0.0                     # crash punch 0..1 as drawn (eased in, so it never steps)
var _impact_goal := 0.0                # set by kick(), decays on its own
var _dip := 0.0                        # landing settle (metres) as drawn
var _dip_goal := 0.0                   # set by dip(), decays on its own

func _ready() -> void:
	near = 0.12
	far = 650.0
	fov = BASE_FOV
	current = true
	physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF   # this camera is placed manually, every frame

func set_menu_mode(value: bool) -> void:
	menu_mode = value

## A real hit (crash 1.0, shield hit 0.6): one soft zoom-and-tilt punch, about a second long.  Deliberately not a shake - the picture
## never wobbles - and light taps (near misses, 0.12) are ignored so the view stays calm while you run.
func kick(strength: float) -> void:
	if strength < 0.3:
		return
	_impact_goal = maxf(_impact_goal, clampf(strength, 0.0, 1.0) * AccessibilityService.shake_scale())

## The camera settles a little with the runner's weight on a landing (strength 0..1).
func dip(strength: float) -> void:
	_dip_goal = maxf(_dip_goal, clampf(strength, 0.0, 1.0) * 0.03 * AccessibilityService.shake_scale())

func snap() -> void:
	if target != null:
		target.reset_physics_interpolation()           # the runner was just teleported: no glide from the old place
		var tf: Transform3D = target.get_global_transform_interpolated()
		_cam_x = tf.origin.x * LATERAL_FOLLOW
		_cam_up = 0.0
	_stretch = 0.0
	_boost_fov = 0.0
	_impact = 0.0
	_impact_goal = 0.0
	_dip = 0.0
	_dip_goal = 0.0
	_blend = 0.0 if menu_mode else 1.0
	_update(0.0, true)

func _process(delta: float) -> void:
	_update(minf(delta, 0.05), false)

static func _damp(current: float, goal: float, rate: float, dt: float) -> float:
	return lerpf(current, goal, 1.0 - exp(-rate * dt))

func _update(dt: float, immediate: bool) -> void:
	if target == null:
		return
	var goal := 0.0 if menu_mode else 1.0
	_blend = goal if immediate else move_toward(_blend, goal, dt * 1.25)
	var eased := smoothstep(0.0, 1.0, _blend)
	var pos: Vector3 = target.get_global_transform_interpolated().origin
	var forward_speed := 0.0
	var boosting := false
	if target is RunnerController:
		var rc := target as RunnerController
		forward_speed = rc.velocity.z if not menu_mode else 0.0
		boosting = rc.boost_time > 0.0
	var follow_x := pos.x * LATERAL_FOLLOW
	var follow_up := maxf(pos.y, 0.0) * VERTICAL_FOLLOW
	var stretch_goal := clampf((forward_speed - 20.0) / 12.0, 0.0, 1.0) * STRETCH_MAX * 0.6 + (STRETCH_MAX * 0.4 if boosting else 0.0)
	var boost_goal := clampf((forward_speed - 18.0) / 14.0, 0.0, 1.0) * 0.6 + (0.4 if boosting else 0.0)
	if immediate:
		_cam_x = follow_x
		_cam_up = follow_up
		_stretch = stretch_goal
		_boost_fov = boost_goal
	else:
		_cam_x = _damp(_cam_x, follow_x, LATERAL_RATE, dt)
		_cam_up = _damp(_cam_up, follow_up, VERTICAL_RATE, dt)
		_stretch = _damp(_stretch, stretch_goal, 2.5, dt)
		_boost_fov = _damp(_boost_fov, boost_goal, 2.0, dt)
		_impact_goal = _damp(_impact_goal, 0.0, 3.0, dt)
		_impact = _damp(_impact, _impact_goal, 26.0, dt)           # eased onset: about 40 ms, never a one-frame jump
		_dip_goal = _damp(_dip_goal, 0.0, 7.0, dt)
		_dip = _damp(_dip, _dip_goal, 30.0, dt)
	var game_pos := Vector3(_cam_x, GAME_HEIGHT + _cam_up - _dip, pos.z - GAME_DISTANCE - _stretch)
	var menu_pos := Vector3(pos.x * 0.35 + MENU_OFFSET.x, MENU_OFFSET.y, pos.z + MENU_OFFSET.z)
	var cam := menu_pos.lerp(game_pos, eased)
	var pitch := deg_to_rad(GAME_PITCH_DEG) + _impact * 0.016
	var game_dir := Vector3(0.0, -sin(pitch), cos(pitch))
	var menu_look := Vector3(pos.x, 1.25, pos.z)
	var look_point := menu_look.lerp(cam + game_dir * 12.0, eased)
	var look_dir := (look_point - cam).normalized()
	global_transform = Transform3D(Basis.looking_at(look_dir, Vector3.UP), cam)
	fov = lerpf(MENU_FOV, BASE_FOV, eased) + _boost_fov * BOOST_FOV * eased + _impact * 1.6 * eased
