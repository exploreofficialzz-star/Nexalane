extends RefCounted
class_name RunnerAnimator
## Procedural human animation for the runner (0.5.0): drives the 25-bone skeleton of runner_base.glb with the biomechanical
## gait of GaitModel.  One instance animates the player's runner, another each ghost runner.
##
## Usage:  var anim := RunnerAnimator.new();  if anim.bind(model): ...
##         every frame set the input fields (forward_speed, grounded, ...) and call step(delta).
## Events:  foot_strike(side, intensity) when a foot touches the ground (0 = left, 1 = right).
##
## Layers (blended in this order, later ones win): idle -> run -> ready stance -> air -> slide -> landing absorption -> hit.
## Skeleton conventions: tools/assetgen/human_rig.py.  The animator only writes bone POSES; rest transforms stay untouched.

signal foot_strike(side: int, intensity: float)

const BONE_NAMES: Array = [
	"Hips", "Spine", "Chest", "Neck", "Head",
	"LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
	"RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
	"LeftUpperLeg", "LeftLowerLeg", "LeftFoot", "LeftToes",
	"RightUpperLeg", "RightLowerLeg", "RightFoot", "RightToes",
	"Pack", "Hood", "HairFront", "HairBack"]
const CORE_BONES: int = 21
const B_HIPS: int = 0
const B_SPINE: int = 1
const B_CHEST: int = 2
const B_NECK: int = 3
const B_HEAD: int = 4
const B_L_SHOULDER: int = 5
const B_L_UPPER_ARM: int = 6
const B_L_LOWER_ARM: int = 7
const B_L_HAND: int = 8
const B_R_SHOULDER: int = 9
const B_R_UPPER_ARM: int = 10
const B_R_LOWER_ARM: int = 11
const B_R_HAND: int = 12
const B_L_UPPER_LEG: int = 13
const B_L_LOWER_LEG: int = 14
const B_L_FOOT: int = 15
const B_L_TOES: int = 16
const B_R_UPPER_LEG: int = 17
const B_R_LOWER_LEG: int = 18
const B_R_FOOT: int = 19
const B_R_TOES: int = 20
const B_PACK: int = 21
const B_HOOD: int = 22
const B_HAIR_FRONT: int = 23
const B_HAIR_BACK: int = 24

# ---- inputs, set by the owner every frame before step() -------------------------------------------------------------
var forward_speed: float = 0.0       # m/s along +Z
var lateral_speed: float = 0.0       # m/s, + = towards the runner's left (+X)
var vertical_speed: float = 0.0      # m/s
var grounded: bool = true
var sliding: bool = false
var running: bool = false            # the run is live (not the menu, not the countdown)
var ready_stance: bool = false       # countdown: sprinter's "get set" stance
var gravity: float = 30.0
var air_height: float = 0.0          # metres above the floor (used to time the landing preparation)

# ---- read-only results ----------------------------------------------------------------------------------------------
var bound: bool = false
var skeleton: Skeleton3D = null
var last_land_impact: float = 0.0    # 0..1 strength of the most recent landing (camera / audio can use it)
var pelvis_height: float = 0.93

var _bone: PackedInt32Array = PackedInt32Array()
var _rest_pos: PackedVector3Array = PackedVector3Array()
var _rest_rot: Array[Quaternion] = []
var _t: float = 0.0
var _phase: float = 0.0
var _u: float = 0.0
var _over: float = 0.0
var _cad: float = 1.25
var _accel: float = 0.0
var _prev_speed: float = 0.0
var _extra_lean: float = 0.0
var _turn: float = 0.0
var _launch: float = 0.0
var _w_run: float = 0.0
var _w_ready: float = 0.0
var _w_air: float = 0.0
var _w_slide: float = 0.0
var _w_land: float = 0.0
var _w_hit: float = 0.0
var _land_amount: float = 0.0
var _land_t: float = 9.0
var _fall_peak: float = 0.0
var _air_t: float = 0.0
var _lead: int = 0
var _slide_lead: int = 0
var _prev_grounded: bool = true
var _prev_sliding: bool = false
var _prev_running: bool = false
var _down: bool = false
var _hit_t: float = 9.0
var _suppress_steps: float = 0.0
var _prev_y: float = 0.93
var _prev_vy: float = 0.0
var _sec_a: PackedFloat32Array = PackedFloat32Array()
var _sec_w: PackedFloat32Array = PackedFloat32Array()


# ---------------------------------------------------------------- binding
## Finds the Skeleton3D below `model` and the bones the animator needs.  Returns false (and stays inert) if the rig is not usable.
func bind(model: Node) -> bool:
	bound = false
	skeleton = _find_skeleton(model)
	if skeleton == null:
		return false
	_bone.resize(BONE_NAMES.size())
	_rest_pos.resize(BONE_NAMES.size())
	_rest_rot.clear()
	var ok: bool = true
	for i in range(BONE_NAMES.size()):
		var idx: int = _find_bone(skeleton, str(BONE_NAMES[i]))
		_bone[i] = idx
		if idx < 0:
			_rest_pos[i] = Vector3.ZERO
			_rest_rot.append(Quaternion.IDENTITY)
			if i < CORE_BONES:
				ok = false
		else:
			var rest: Transform3D = skeleton.get_bone_rest(idx)
			_rest_pos[i] = rest.origin
			_rest_rot.append(rest.basis.get_rotation_quaternion())
	if not ok:
		skeleton = null
		return false
	_sec_a.resize(4)
	_sec_w.resize(4)
	_widen_culling(model)
	bound = true
	return true


static func _find_skeleton(node: Node) -> Skeleton3D:
	if node is Skeleton3D:
		return node as Skeleton3D
	for child in node.get_children():
		var found: Skeleton3D = _find_skeleton(child)
		if found != null:
			return found
	return null


static func _normalized(s: String) -> String:
	var out: String = ""
	for i in range(s.length()):
		var code: int = s.unicode_at(i)
		if (code >= 48 and code <= 57) or (code >= 97 and code <= 122):
			out += String.chr(code)
		elif code >= 65 and code <= 90:
			out += String.chr(code + 32)
	return out


static func _find_bone(skel: Skeleton3D, bone_name: String) -> int:
	var idx: int = skel.find_bone(bone_name)
	if idx >= 0:
		return idx
	var want: String = _normalized(bone_name)
	for i in range(skel.get_bone_count()):
		var have: String = _normalized(skel.get_bone_name(i))
		if have == want or have.ends_with(want):
			return i
	return -1


## A skinned mesh is culled with its bind-pose bounds; widen them so a leaping / sliding pose is never culled.
static func _widen_culling(node: Node) -> void:
	for child in node.get_children():
		if child is MeshInstance3D:
			(child as MeshInstance3D).extra_cull_margin = 1.5
		_widen_culling(child)


# ---------------------------------------------------------------- events from the owner
## The run starts (or restarts after a revive): standing-start drive, get up if the runner was down.
func begin_run() -> void:
	_down = false
	_hit_t = 9.0
	_suppress_steps = 0.2


## The runner crashed: recoil, stumble and crouch.  Held until begin_run() / stand_up().
func trigger_hit() -> void:
	_down = true
	_hit_t = 0.0


## Stands the runner back up (menu, restart).
func stand_up() -> void:
	_down = false
	_hit_t = 9.0


func is_down() -> bool:
	return _down


## Swing leg = the leg that is currently moving forward = the natural lead leg for a jump / slide.
func _swing_leg() -> int:
	return 0 if fposmod(_phase, 1.0) >= 0.5 else 1


# ---------------------------------------------------------------- per frame
func step(delta: float) -> void:
	if not bound:
		return
	var dt: float = clampf(delta, 0.0, 0.05)
	if dt <= 0.0:
		return
	_t += dt
	_update_derived(dt)
	_update_events(dt)
	_update_weights(dt)
	var pose: PackedFloat32Array = GaitModel.idle_pose(_t)
	var y: float = GaitModel.REST_HIPS_Y - 0.03
	if _w_run < 0.999:
		y = GaitModel.support_height(pose)               # fully running: the run path below replaces it anyway
	var strike_phase_prev: float = _phase
	if _w_run > 0.001:
		if grounded and not sliding and _w_air < 0.6:
			_phase += dt * _cad
		var run: PackedFloat32Array = GaitModel.run_pose(_phase, _u, _over, _extra_lean, _launch, _turn)
		var y_run: float = GaitModel.run_pelvis_y(_phase, _u, _over, _extra_lean, _launch, _cad)
		pose = GaitModel.blend_into(pose, run, _w_run)
		y = lerpf(y, y_run, _w_run)
		_emit_strikes(strike_phase_prev, _phase)
		_phase = fposmod(_phase, 1.0)
	if _w_ready > 0.001:
		var rdy: PackedFloat32Array = GaitModel.ready_pose(_t)
		pose = GaitModel.blend_into(pose, rdy, _w_ready)
		y = lerpf(y, GaitModel.support_height(rdy), _w_ready)
	if _w_air > 0.001:
		var air: PackedFloat32Array = GaitModel.air_pose(_air_progress(), _lead)
		pose = GaitModel.blend_into(pose, air, _w_air)
		y = lerpf(y, GaitModel.AIR_PELVIS_Y, _w_air)
	if _w_slide > 0.001:
		var sl: PackedFloat32Array = GaitModel.slide_pose(_slide_lead)
		pose = GaitModel.blend_into(pose, sl, _w_slide)
		y = lerpf(y, GaitModel.SLIDE_PELVIS_Y, _w_slide)
	if _w_land > 0.001:
		var lp: PackedFloat32Array = GaitModel.land_pose()
		pose = GaitModel.blend_into(pose, lp, _w_land)
		y = lerpf(y, GaitModel.support_height(lp), _w_land)
	if _w_hit > 0.001:
		var hp: PackedFloat32Array = _hit_pose()
		pose = GaitModel.blend_into(pose, hp, _w_hit)
		y = lerpf(y, GaitModel.support_height(hp), _w_hit)
	# lane change: shoulders and head lead the turn, the outside arm flares
	var turn_w: float = _w_run * (1.0 - _w_air * 0.5) * (1.0 - _w_slide)
	pose[GaitModel.CHS_YAW] += _turn * 0.16 * turn_w
	var outer: int = 1 if _turn > 0.0 else 0
	pose[GaitModel.arm_ch(outer, GaitModel.A_SH_ABD)] += absf(_turn) * 0.30 * turn_w
	# feet never sink into the floor while the runner is on it
	if grounded and _w_air < 0.5 and _w_slide < 0.5:
		y = maxf(y, GaitModel.support_height(pose))
	pelvis_height = y
	_apply(pose, y)
	_update_secondary(dt, y)


func _update_derived(dt: float) -> void:
	var speed: float = maxf(forward_speed, 0.0) if running else 0.0
	_u = lerpf(_u, GaitModel.intensity(speed), minf(1.0, dt * 6.0))
	_over = lerpf(_over, GaitModel.overdrive(speed), minf(1.0, dt * 4.0))
	_cad = GaitModel.cadence(_u, _over)
	if running and not _prev_running:
		_launch = 1.0                                     # explosive standing start (also after a revive)
		_prev_speed = forward_speed                       # the jump from 0 to run speed is not an acceleration to lean into
	_prev_running = running
	var a: float = clampf((forward_speed - _prev_speed) / dt, -25.0, 25.0) if running else 0.0
	_prev_speed = forward_speed
	_accel = lerpf(_accel, a, minf(1.0, dt * 5.0))      # a speed boost kicks the runner forward for a moment
	_extra_lean = lerpf(_extra_lean, clampf(atan2(_accel, 9.81) * 0.7, -0.12, 0.40), minf(1.0, dt * 8.0))
	var lateral: float = lateral_speed if running else 0.0
	_turn = lerpf(_turn, clampf(lateral / 12.0, -1.0, 1.0), minf(1.0, dt * 12.0))
	_launch = move_toward(_launch, 0.0, dt * 1.4) if running else 0.0
	_suppress_steps = maxf(0.0, _suppress_steps - dt)
	_land_t += dt
	_hit_t += dt


func _update_events(dt: float) -> void:
	if not grounded:
		_fall_peak = maxf(_fall_peak, -vertical_speed)
	if _prev_grounded and not grounded:
		_lead = _swing_leg()
		_air_t = 0.0
		_fall_peak = maxf(0.0, -vertical_speed)
	elif not _prev_grounded and grounded:
		if _air_t >= 0.10:                              # a real flight (the start-line settle and ramp bumps are shorter)
			_land_amount = clampf(_fall_peak / 14.0, 0.25, 1.0)
			last_land_impact = _land_amount
			_land_t = 0.0
			_phase = 0.0 if _lead == 0 else 0.5        # the leading foot is the first to touch down
			_suppress_steps = 0.14
		_fall_peak = 0.0
	_prev_grounded = grounded
	if not grounded:
		_air_t += dt
	if sliding and not _prev_sliding:
		_slide_lead = _swing_leg()
	_prev_sliding = sliding


func _update_weights(dt: float) -> void:
	_w_run = move_toward(_w_run, 1.0 if running else 0.0, dt * (8.0 if running else 6.0))
	_w_ready = move_toward(_w_ready, 1.0 if (ready_stance and not running) else 0.0, dt * (3.0 if ready_stance else 9.0))
	_w_air = move_toward(_w_air, 1.0 if (not grounded and _air_t > 0.04) else 0.0, dt * (14.0 if not grounded else 12.0))
	_w_slide = move_toward(_w_slide, 1.0 if sliding else 0.0, dt * (10.0 if sliding else 8.0))
	var lt: float = _land_t
	_w_land = _land_amount * smoothstep(0.0, 0.05, lt) * (1.0 - smoothstep(0.08, 0.36, lt))
	_w_hit = move_toward(_w_hit, 1.0 if _down else 0.0, dt * (16.0 if _down else 3.5))


## 0..1 progress through the current flight, estimated from the vertical velocity so landing preparation starts on time.
func _air_progress() -> float:
	var h: float = maxf(0.0, air_height)
	var vy: float = vertical_speed
	var t_land: float = (vy + sqrt(maxf(0.0, vy * vy + 2.0 * gravity * h))) / maxf(gravity, 1.0)
	return clampf(_air_t / maxf(_air_t + maxf(t_land, 0.0), 0.05), 0.0, 1.0)


func _hit_pose() -> PackedFloat32Array:
	var rec: PackedFloat32Array = GaitModel.hit_recoil_pose()
	var down: PackedFloat32Array = GaitModel.hit_down_pose()
	var s: float = smoothstep(0.08, 0.52, _hit_t)
	rec = GaitModel.blend_into(rec, down, s)
	var heave: float = sin(_t * 5.2) * s                 # winded breathing once crouched
	rec[GaitModel.CHS_PITCH] += 0.035 * heave
	rec[GaitModel.HD_PITCH] += 0.02 * heave
	return rec


func _emit_strikes(prev_phase: float, new_phase: float) -> void:
	if _suppress_steps > 0.0 or not grounded or sliding or _w_run < 0.6 or _w_air > 0.4:
		return
	var inten: float = clampf(0.4 + 0.6 * _u, 0.0, 1.0)
	if floorf(new_phase) > floorf(prev_phase):
		foot_strike.emit(0, inten)
	if floorf(new_phase - 0.5) > floorf(prev_phase - 0.5):
		foot_strike.emit(1, inten)


# ---------------------------------------------------------------- writing the skeleton
func _set_rot(b: int, q: Quaternion) -> void:
	var idx: int = _bone[b]
	if idx >= 0:
		var rest_q: Quaternion = _rest_rot[b]
		skeleton.set_bone_pose_rotation(idx, rest_q * q)


func _apply(c: PackedFloat32Array, y: float) -> void:
	var hips_idx: int = _bone[B_HIPS]
	skeleton.set_bone_pose_position(hips_idx, _rest_pos[B_HIPS] + Vector3(c[GaitModel.PEL_X], y - GaitModel.REST_HIPS_Y, c[GaitModel.PEL_Z]))
	_set_rot(B_HIPS, Quaternion.from_euler(Vector3(c[GaitModel.PEL_PITCH], c[GaitModel.PEL_YAW], c[GaitModel.PEL_ROLL])))
	_set_rot(B_SPINE, Quaternion.from_euler(Vector3(c[GaitModel.SPN_PITCH], c[GaitModel.SPN_YAW], c[GaitModel.SPN_ROLL])))
	_set_rot(B_CHEST, Quaternion.from_euler(Vector3(c[GaitModel.CHS_PITCH], c[GaitModel.CHS_YAW], c[GaitModel.CHS_ROLL])))
	_set_rot(B_NECK, Quaternion.from_euler(Vector3(c[GaitModel.NCK_PITCH], c[GaitModel.NCK_YAW], c[GaitModel.NCK_ROLL])))
	_set_rot(B_HEAD, Quaternion.from_euler(Vector3(c[GaitModel.HD_PITCH], c[GaitModel.HD_YAW], c[GaitModel.HD_ROLL])))
	for side in range(2):
		var sgn: float = 1.0 if side == 0 else -1.0
		var sh: int = B_L_SHOULDER if side == 0 else B_R_SHOULDER
		var ua: int = B_L_UPPER_ARM if side == 0 else B_R_UPPER_ARM
		var la: int = B_L_LOWER_ARM if side == 0 else B_R_LOWER_ARM
		var hd: int = B_L_HAND if side == 0 else B_R_HAND
		var ul: int = B_L_UPPER_LEG if side == 0 else B_R_UPPER_LEG
		var ll: int = B_L_LOWER_LEG if side == 0 else B_R_LOWER_LEG
		var ft: int = B_L_FOOT if side == 0 else B_R_FOOT
		var ts: int = B_L_TOES if side == 0 else B_R_TOES
		_set_rot(sh, Quaternion.from_euler(Vector3(0.0, -sgn * c[GaitModel.arm_ch(side, GaitModel.A_CLAV_YAW)], sgn * c[GaitModel.arm_ch(side, GaitModel.A_CLAV_ELEV)])))
		_set_rot(ua, Quaternion.from_euler(Vector3(-c[GaitModel.arm_ch(side, GaitModel.A_SH_FLEX)], -sgn * c[GaitModel.arm_ch(side, GaitModel.A_SH_ROT)], sgn * c[GaitModel.arm_ch(side, GaitModel.A_SH_ABD)])))
		_set_rot(la, Quaternion.from_euler(Vector3(-c[GaitModel.arm_ch(side, GaitModel.A_ELBOW)], -sgn * c[GaitModel.arm_ch(side, GaitModel.A_FORE_ROT)], 0.0)))
		_set_rot(hd, Quaternion.from_euler(Vector3(-c[GaitModel.arm_ch(side, GaitModel.A_WRIST)], 0.0, 0.0)))
		_set_rot(ul, Quaternion.from_euler(Vector3(-c[GaitModel.leg_ch(side, GaitModel.L_HIP_FLEX)], -sgn * c[GaitModel.leg_ch(side, GaitModel.L_HIP_ROT)], sgn * c[GaitModel.leg_ch(side, GaitModel.L_HIP_ABD)])))
		_set_rot(ll, Quaternion.from_euler(Vector3(c[GaitModel.leg_ch(side, GaitModel.L_KNEE)], 0.0, 0.0)))
		_set_rot(ft, Quaternion.from_euler(Vector3(c[GaitModel.leg_ch(side, GaitModel.L_ANKLE)], 0.0, 0.0)))
		_set_rot(ts, Quaternion.from_euler(Vector3(c[GaitModel.leg_ch(side, GaitModel.L_TOE)], 0.0, 0.0)))


## Cloth and hair follow the body with a little lag: damped springs driven by the pelvis' vertical acceleration, plus the
## wind that sweeps hair backwards at speed.  Pack, hood and two hair bones (index 0..3 = B_PACK..B_HAIR_BACK).
func _update_secondary(dt: float, y: float) -> void:
	var vy: float = (y - _prev_y) / dt
	var ay: float = clampf((vy - _prev_vy) / dt, -60.0, 60.0)
	_prev_y = y
	_prev_vy = vy
	var windy: bool = running or not grounded
	var wind: float = clampf(forward_speed / 30.0, 0.0, 1.0) if windy else 0.0
	var sweep_front: float = -(0.10 + 0.50 * wind) if windy else 0.0      # airflow combs the hair backwards at speed
	var sweep_back: float = -(0.06 + 0.35 * wind) if windy else 0.0
	var targets: Array = [0.0, 0.0, sweep_front, sweep_back]
	var omega: Array = [14.0, 11.0, 16.0, 13.0]
	var zeta: Array = [0.35, 0.30, 0.25, 0.30]
	var gain: Array = [0.0080, 0.0120, 0.0220, 0.0160]
	for i in range(4):
		var b: int = B_PACK + i
		if _bone[b] < 0:
			continue
		var w0: float = float(omega[i])
		var a: float = _sec_a[i]
		var v: float = _sec_w[i]
		v += dt * (-(w0 * w0) * (a - float(targets[i])) - 2.0 * float(zeta[i]) * w0 * v - float(gain[i]) * ay * w0)
		a = clampf(a + dt * v, -0.7, 0.7)
		_sec_a[i] = a
		_sec_w[i] = v
		var rest_q: Quaternion = _rest_rot[b]
		skeleton.set_bone_pose_rotation(_bone[b], rest_q * Quaternion(Vector3.RIGHT, a))


# ---------------------------------------------------------------- debugging / tests
func debug_state() -> Dictionary:
	return {"phase": _phase, "u": _u, "cadence": _cad, "w_run": _w_run, "w_air": _w_air, "w_slide": _w_slide, "w_land": _w_land,
		"w_hit": _w_hit, "w_ready": _w_ready, "lead": _lead, "down": _down, "pelvis_height": pelvis_height}
