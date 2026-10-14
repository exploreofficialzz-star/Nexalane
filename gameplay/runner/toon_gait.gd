extends RefCounted
class_name ToonGait
## Cartoon pose library for the 0.6.0 runner (tools/assetgen/toon.py).  Same channel layout and the same function names as
## GaitModel, so RunnerAnimator drives either one; this one is deliberately NOT biomechanical: a big, bouncy, readable
## sprint (high knees, heel kicks, wide arm pumps, forward lean), exaggerated jump / slide / crash poses.
##
## Conventions (tools/assetgen/toon_rig.py): the runner faces +Z, rest rotations are identity.  Channel values are radians:
## leg HIP_FLEX > 0 = thigh forward, KNEE > 0 = heel towards the buttock, ANKLE > 0 = toes down, arm SH_FLEX > 0 = arm forward,
## ELBOW > 0 = forearm up.  tools/preview_toon_poses.py runs THIS file through a small GDScript->Python translator and renders
## every pose on the shipped GLB (docs/previews/toon_pose_sheet.png).
##
## Only a small GDScript subset is used on purpose (typed vars, static funcs, if / elif / for, float maths) so that translator can run it.

const DEG: float = PI / 180.0

# ---- channel layout (identical to GaitModel) -----------------------------------------------------------------------
const PEL_X: int = 0
const PEL_Z: int = 1
const PEL_PITCH: int = 2
const PEL_YAW: int = 3
const PEL_ROLL: int = 4
const SPN_PITCH: int = 5
const SPN_YAW: int = 6
const SPN_ROLL: int = 7
const CHS_PITCH: int = 8
const CHS_YAW: int = 9
const CHS_ROLL: int = 10
const NCK_PITCH: int = 11
const NCK_YAW: int = 12
const NCK_ROLL: int = 13
const HD_PITCH: int = 14
const HD_YAW: int = 15
const HD_ROLL: int = 16
const ARM: int = 17          # + side * 8 + A_*
const A_CLAV_YAW: int = 0
const A_CLAV_ELEV: int = 1
const A_SH_FLEX: int = 2
const A_SH_ABD: int = 3
const A_SH_ROT: int = 4
const A_ELBOW: int = 5
const A_FORE_ROT: int = 6
const A_WRIST: int = 7
const LEG: int = 33          # + side * 6 + L_*
const L_HIP_FLEX: int = 0
const L_HIP_ABD: int = 1
const L_HIP_ROT: int = 2
const L_KNEE: int = 3
const L_ANKLE: int = 4
const L_TOE: int = 5
const N_CH: int = 45

# ---- skeleton dimensions (mirror tools/assetgen/toon_rig.py) -------------------------------------------------------
const THIGH: float = 0.400
const SHANK: float = 0.360
const HIP_HALF_WIDTH: float = 0.115
const HIP_DROP: float = 0.010
const ANKLE_HEIGHT: float = 0.110
const TOE_Z: float = 0.140
const TOE_Y: float = 0.050
const HEEL_Z: float = -0.090
const TOE_TIP_Z: float = 0.120
const REST_HIPS_Y: float = 0.880

const STANCE_FRACTION: float = 0.35         # share of the cycle one foot is on the ground
const HOP: float = 0.060                    # extra pelvis lift in the two flight phases (cartoon exaggeration, metres)
const SLIDE_PELVIS_Y: float = 0.420
const AIR_PELVIS_Y: float = 0.860
const READY_KNEE_BACK_DEG: float = 40.379


static func arm_ch(side: int, k: int) -> int:
	return ARM + side * 8 + k


static func leg_ch(side: int, k: int) -> int:
	return LEG + side * 6 + k


static func new_pose() -> PackedFloat32Array:
	var c := PackedFloat32Array()
	c.resize(N_CH)
	return c


# ---- speed -> gait parameters -------------------------------------------------------------------------------------
## 0 = easy jog, 1 = flat-out sprint (game speeds are 16..31 m/s).
static func intensity(speed: float) -> float:
	if speed <= 0.0:
		return 0.0
	if speed < 8.0:
		return 0.25 * speed / 8.0
	return clampf(0.25 + 0.75 * (speed - 8.0) / 20.0, 0.0, 1.0)


static func overdrive(speed: float) -> float:
	return clampf((speed - 24.0) / 10.0, 0.0, 1.0)


## Gait cycles per second (two steps per cycle).
static func cadence(u: float, over: float) -> float:
	return 1.85 + 0.85 * u + 0.20 * over


static func stance_fraction(u: float) -> float:
	return STANCE_FRACTION


# ---- the running pose ---------------------------------------------------------------------------------------------
## ph = phase of the LEFT leg in cycles (0 = left foot touches down); extra_lean (rad) = acceleration lean;
## launch 0..1 = standing-start drive; turn = signed lane change input (-1..1, + = left).
static func run_pose(ph: float, u: float, over: float, extra_lean: float, launch: float, turn: float) -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	var sw: float = TAU
	var tilt: float = (6.0 + 5.0 * u) * DEG + 0.45 * extra_lean + 2.0 * DEG * sin(2.0 * sw * (ph - 0.10))
	c[PEL_PITCH] = tilt
	c[PEL_ROLL] = lerpf(4.0, 7.0, u) * DEG * sin(sw * ph)
	c[PEL_YAW] = lerpf(6.0, 11.0, u) * DEG * sin(sw * ph)
	c[PEL_X] = lerpf(0.016, 0.024, u) * sin(sw * ph)
	var lean: float = (11.0 + 12.0 * u + 4.0 * over) * DEG + extra_lean + launch * 18.0 * DEG
	var rest_lean: float = lean - tilt
	c[SPN_PITCH] = 0.40 * rest_lean
	c[CHS_PITCH] = 0.60 * rest_lean
	var twist: float = (lerpf(7.0, 12.0, u) + lerpf(8.0, 13.0, u)) * DEG
	c[SPN_YAW] = -0.40 * twist * sin(sw * ph)
	c[CHS_YAW] = -0.60 * twist * sin(sw * ph)
	c[SPN_ROLL] = -0.55 * c[PEL_ROLL]
	c[CHS_ROLL] = -0.30 * c[PEL_ROLL]
	c[NCK_PITCH] = -0.40 * 0.80 * lean
	c[HD_PITCH] = -0.60 * 0.80 * lean
	var yaw_sum: float = c[PEL_YAW] + c[SPN_YAW] + c[CHS_YAW]
	var roll_sum: float = c[PEL_ROLL] + c[SPN_ROLL] + c[CHS_ROLL]
	c[NCK_YAW] = -0.45 * yaw_sum + 0.30 * turn * 0.35
	c[HD_YAW] = -0.45 * yaw_sum + 0.70 * turn * 0.35
	c[NCK_ROLL] = -0.40 * roll_sum
	c[HD_ROLL] = -0.40 * roll_sum
	var af: float = (38.0 + 30.0 * u + 6.0 * over + 10.0 * launch) * DEG
	var ab: float = (44.0 + 32.0 * u + 6.0 * over + 8.0 * launch) * DEG
	var em: float = (84.0 + 10.0 * u) * DEG
	for side in range(2):
		var q: float = ph + 0.5 * float(side)
		var sn: float = sin(sw * (q - 0.02))
		c[arm_ch(side, A_SH_FLEX)] = 0.5 * (af - ab) + 0.5 * (af + ab) * sn
		c[arm_ch(side, A_ELBOW)] = em + 22.0 * DEG * sn
		c[arm_ch(side, A_SH_ABD)] = (10.0 + 4.0 * sn) * DEG
		c[arm_ch(side, A_FORE_ROT)] = -8.0 * DEG
		c[arm_ch(side, A_WRIST)] = 8.0 * DEG
		c[arm_ch(side, A_CLAV_YAW)] = 4.0 * DEG * sn
		c[arm_ch(side, A_CLAV_ELEV)] = 2.5 * DEG * absf(sn)
	for side in range(2):
		var p: float = ph + 0.5 * float(side)
		p = p - floorf(p)
		# hip flexion as a WORLD angle (+ = thigh forward): reach forward before touch-down, drive back through the stance,
		# then a high knee drive in the swing.  The pelvis tilt is added because the legs hang from the tilted pelvis.
		var h_td: float = (28.0 + 12.0 * u + 3.0 * over) * DEG
		var h_to: float = -(16.0 + 10.0 * u) * DEG
		var h_pk: float = (58.0 + 24.0 * u + 4.0 * over) * DEG
		var hip: float = h_td
		if p < STANCE_FRACTION:
			hip = lerpf(h_td, h_to, 0.5 - 0.5 * cos(PI * p / STANCE_FRACTION))
		else:
			var sw_t: float = (p - STANCE_FRACTION) / (1.0 - STANCE_FRACTION)
			if sw_t < 0.72:
				hip = lerpf(h_to, h_pk, 0.5 - 0.5 * cos(PI * sw_t / 0.72))
			else:
				hip = lerpf(h_pk, h_td, 0.5 - 0.5 * cos(PI * (sw_t - 0.72) / 0.28))
		hip = hip + tilt
		var knee: float = 14.0 * DEG
		if p < STANCE_FRACTION:
			knee = (14.0 + 16.0 * sin(PI * p / STANCE_FRACTION)) * DEG
		else:
			var s: float = (p - STANCE_FRACTION) / (1.0 - STANCE_FRACTION)
			knee = (14.0 + (86.0 + 24.0 * u + 6.0 * over - 14.0) * sin(PI * s)) * DEG
		var foot: float = -8.0
		if p < 0.14:
			foot = lerpf(-8.0, 0.0, smoothstep(0.0, 0.14, p))
		elif p < STANCE_FRACTION:
			foot = lerpf(0.0, 42.0, smoothstep(0.14, STANCE_FRACTION, p))
		elif p < 0.50:
			foot = lerpf(42.0, 26.0, smoothstep(STANCE_FRACTION, 0.50, p))
		elif p < 0.80:
			foot = lerpf(26.0, -4.0, smoothstep(0.50, 0.80, p))
		else:
			foot = lerpf(-4.0, -8.0, smoothstep(0.80, 1.0, p))
		foot = foot * DEG
		c[leg_ch(side, L_HIP_FLEX)] = hip
		c[leg_ch(side, L_KNEE)] = knee
		c[leg_ch(side, L_ANKLE)] = foot - (tilt - hip + knee)
		c[leg_ch(side, L_HIP_ABD)] = (4.0 + 3.0 * sin(sw * p)) * DEG
		var w: float = smoothstep(0.0, 0.03, p) * (1.0 - smoothstep(STANCE_FRACTION, STANCE_FRACTION + 0.04, p))
		c[leg_ch(side, L_TOE)] = -clampf(foot, 0.0, 40.0 * DEG) * w
	return c


# ---- forward kinematics of the legs (sagittal contact maths) --------------------------------------------------------
static func pelvis_basis(c: PackedFloat32Array) -> Basis:
	return Basis.from_euler(Vector3(c[PEL_PITCH], c[PEL_YAW], c[PEL_ROLL]))


static func thigh_basis(c: PackedFloat32Array, side: int) -> Basis:
	var sgn: float = 1.0 if side == 0 else -1.0
	return Basis.from_euler(Vector3(-c[leg_ch(side, L_HIP_FLEX)], -sgn * c[leg_ch(side, L_HIP_ROT)], sgn * c[leg_ch(side, L_HIP_ABD)]))


## Height (relative to the Hips bone origin) of the lowest point of one foot (heel, ball of foot or toe tip).
static func foot_low(c: PackedFloat32Array, side: int) -> float:
	var sgn: float = 1.0 if side == 0 else -1.0
	var bp: Basis = pelvis_basis(c)
	var hip: Vector3 = bp * Vector3(sgn * HIP_HALF_WIDTH, -HIP_DROP, 0.0)
	var bt: Basis = bp * thigh_basis(c, side)
	var knee: Vector3 = hip + bt * Vector3(0.0, -THIGH, 0.0)
	var bs: Basis = bt * Basis.from_euler(Vector3(c[leg_ch(side, L_KNEE)], 0.0, 0.0))
	var ankle: Vector3 = knee + bs * Vector3(0.0, -SHANK, 0.0)
	var bf: Basis = bs * Basis.from_euler(Vector3(c[leg_ch(side, L_ANKLE)], 0.0, 0.0))
	var heel: Vector3 = ankle + bf * Vector3(0.0, -ANKLE_HEIGHT, HEEL_Z)
	var toe_joint: Vector3 = ankle + bf * Vector3(0.0, TOE_Y - ANKLE_HEIGHT, TOE_Z)
	var ball: Vector3 = toe_joint + bf * Vector3(0.0, -TOE_Y, 0.0)
	var bto: Basis = bf * Basis.from_euler(Vector3(c[leg_ch(side, L_TOE)], 0.0, 0.0))
	var tip: Vector3 = toe_joint + bto * Vector3(0.0, -TOE_Y, TOE_TIP_Z)
	return minf(heel.y, minf(ball.y, tip.y))


## Hips bone height that keeps both feet on / above the ground.
static func support_height(c: PackedFloat32Array) -> float:
	return maxf(-foot_low(c, 0), -foot_low(c, 1))


## Vertical pelvis path of the run: feet planted during stance, a springy hop in the two flight phases.
static func run_pelvis_y(ph: float, u: float, over: float, extra_lean: float, launch: float, cad: float) -> float:
	var base: float = support_height(run_pose(ph, u, over, extra_lean, launch, 0.0))
	var q: float = ph - floorf(ph)
	q = q - 0.5 * floorf(q / 0.5)
	var hop: float = 0.0
	if q > STANCE_FRACTION:
		hop = HOP * (0.55 + 0.45 * u) * sin(PI * (q - STANCE_FRACTION) / (0.5 - STANCE_FRACTION))
	return base + hop


# ---- other whole body poses ---------------------------------------------------------------------------------------
## Relaxed, bouncy standing pose with breathing, a weight shift and a look around (t in seconds).
static func idle_pose(t: float) -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	var br: float = sin(t * 2.1)
	var sh: float = sin(t * 0.9)
	var bob: float = 0.5 + 0.5 * sin(t * 4.2)
	c[PEL_PITCH] = 4.0 * DEG
	c[PEL_ROLL] = 2.5 * DEG * sh
	c[PEL_YAW] = 2.0 * DEG * sin(t * 0.5)
	c[PEL_X] = 0.018 * sh
	c[SPN_PITCH] = 2.0 * DEG + 0.8 * DEG * br
	c[CHS_PITCH] = 1.5 * DEG + 1.0 * DEG * br
	c[CHS_ROLL] = -2.0 * DEG * sh
	c[NCK_PITCH] = -2.0 * DEG
	c[HD_PITCH] = -2.0 * DEG + 2.0 * DEG * sin(t * 0.8)
	c[HD_YAW] = 14.0 * DEG * sin(t * 0.55) * sin(t * 0.23)
	c[HD_ROLL] = 3.0 * DEG * sin(t * 0.7)
	for side in range(2):
		var q: float = 1.0 if side == 0 else -1.0
		c[arm_ch(side, A_SH_FLEX)] = (6.0 + 2.0 * br + 3.0 * bob) * DEG
		c[arm_ch(side, A_SH_ABD)] = (12.0 + 2.0 * br) * DEG
		c[arm_ch(side, A_ELBOW)] = (26.0 + 4.0 * sin(t * 1.3 + float(side)) + 6.0 * bob) * DEG
		c[arm_ch(side, A_FORE_ROT)] = 10.0 * DEG
		c[arm_ch(side, A_WRIST)] = 4.0 * DEG
		c[arm_ch(side, A_CLAV_ELEV)] = 2.0 * DEG * br
		c[leg_ch(side, L_HIP_FLEX)] = (5.0 + q * 1.5 * sh + 3.0 * bob) * DEG
		c[leg_ch(side, L_KNEE)] = (8.0 + q * 1.5 * sh + 6.0 * bob) * DEG
		c[leg_ch(side, L_HIP_ABD)] = 4.0 * DEG
		c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - c[leg_ch(side, L_HIP_FLEX)] + c[leg_ch(side, L_KNEE)])
	return c


## Countdown "get set" stance: staggered feet, weight forward, arms ready (like a sprinter, a little theatrical).
static func ready_pose(t: float) -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	var br: float = sin(t * 3.2)
	c[PEL_PITCH] = 18.0 * DEG
	c[PEL_YAW] = 4.0 * DEG
	c[SPN_PITCH] = 9.0 * DEG + 0.8 * DEG * br
	c[CHS_PITCH] = 12.0 * DEG + 1.0 * DEG * br
	c[CHS_YAW] = -8.0 * DEG
	c[NCK_PITCH] = -14.0 * DEG
	c[HD_PITCH] = -12.0 * DEG
	c[HD_YAW] = 4.0 * DEG
	c[leg_ch(0, L_HIP_FLEX)] = 50.0 * DEG
	c[leg_ch(0, L_KNEE)] = 70.0 * DEG
	c[leg_ch(1, L_HIP_FLEX)] = 8.0 * DEG
	c[leg_ch(1, L_KNEE)] = READY_KNEE_BACK_DEG * DEG
	for side in range(2):
		c[leg_ch(side, L_HIP_ABD)] = 4.0 * DEG
		c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - c[leg_ch(side, L_HIP_FLEX)] + c[leg_ch(side, L_KNEE)])
	c[arm_ch(1, A_SH_FLEX)] = 48.0 * DEG
	c[arm_ch(1, A_ELBOW)] = 100.0 * DEG
	c[arm_ch(0, A_SH_FLEX)] = -44.0 * DEG
	c[arm_ch(0, A_ELBOW)] = 90.0 * DEG
	for side in range(2):
		c[arm_ch(side, A_SH_ABD)] = 12.0 * DEG
		c[arm_ch(side, A_FORE_ROT)] = -6.0 * DEG
	return c


## Feet-first slide on the backpack: trunk almost flat, legs reaching forward, arms trailing.  Stays within the 0.95 m slide hit box
## (tools/preview_toon_poses.py measures the silhouette: about 0.92 m from the floor to the highest point).
static func slide_pose(lead: int) -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	c[PEL_PITCH] = -82.0 * DEG
	c[SPN_PITCH] = -8.0 * DEG
	c[CHS_PITCH] = -6.0 * DEG
	c[NCK_PITCH] = 24.0 * DEG
	c[HD_PITCH] = 10.0 * DEG
	for side in range(2):
		var is_lead: bool = side == lead
		var thigh: float = 88.0 * DEG
		var knee: float = 4.0 * DEG
		if not is_lead:
			thigh = 80.0 * DEG
			knee = 16.0 * DEG
		var hip: float = thigh + c[PEL_PITCH]
		c[leg_ch(side, L_HIP_FLEX)] = hip
		c[leg_ch(side, L_KNEE)] = knee
		c[leg_ch(side, L_ANKLE)] = -24.0 * DEG - (c[PEL_PITCH] - hip + knee)
		c[leg_ch(side, L_HIP_ABD)] = 6.0 * DEG
		c[arm_ch(side, A_SH_FLEX)] = -60.0 * DEG
		c[arm_ch(side, A_SH_ABD)] = 30.0 * DEG
		c[arm_ch(side, A_ELBOW)] = 26.0 * DEG
		c[arm_ch(side, A_WRIST)] = -12.0 * DEG
	return c


## Big leap.  a = 0..1 progress through the flight, lead = side of the leading leg.  Arms swing up and out.
static func air_pose(a: float, lead: int) -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	var take: float = 1.0 - smoothstep(0.0, 0.22, a)
	var land: float = smoothstep(0.58, 0.92, a)
	var mid: float = maxf(1.0 - take - land, 0.0)
	c[PEL_PITCH] = (12.0 * take + 12.0 * mid + 8.0 * land) * DEG
	c[SPN_PITCH] = (6.0 * take + 8.0 * mid + 2.0 * land) * DEG
	c[CHS_PITCH] = (6.0 * take + 10.0 * mid + 2.0 * land) * DEG
	c[NCK_PITCH] = -10.0 * DEG
	c[HD_PITCH] = -8.0 * DEG
	for side in range(2):
		var is_lead: bool = side == lead
		var hip: float = 0.0
		var knee: float = 0.0
		var foot: float = 0.0
		var shoulder: float = 0.0
		if is_lead:
			hip = 56.0 * take + 82.0 * mid + 44.0 * land
			knee = 80.0 * take + 50.0 * mid + 30.0 * land
			foot = 30.0 * take - 6.0 * mid + 20.0 * land
			shoulder = 30.0 * take - 20.0 * mid + 40.0 * land
		else:
			hip = -22.0 * take + 22.0 * mid + 28.0 * land
			knee = 40.0 * take + 118.0 * mid + 60.0 * land
			foot = 36.0 * take + 22.0 * mid + 22.0 * land
			shoulder = 70.0 * take + 70.0 * mid + 36.0 * land
		c[leg_ch(side, L_HIP_FLEX)] = hip * DEG
		c[leg_ch(side, L_KNEE)] = knee * DEG
		c[leg_ch(side, L_ANKLE)] = foot * DEG - (c[PEL_PITCH] - hip * DEG + knee * DEG)
		c[leg_ch(side, L_HIP_ABD)] = (6.0 + 8.0 * mid) * DEG
		c[arm_ch(side, A_SH_FLEX)] = shoulder * DEG
		c[arm_ch(side, A_SH_ABD)] = (18.0 + 40.0 * mid) * DEG
		c[arm_ch(side, A_ELBOW)] = (70.0 * take + 50.0 * mid + 60.0 * land) * DEG
	return c


## Impact absorption: deep hip / knee / ankle flexion, trunk folded forward, arms thrown forward.
static func land_pose() -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	c[PEL_PITCH] = 30.0 * DEG
	c[SPN_PITCH] = 12.0 * DEG
	c[CHS_PITCH] = 12.0 * DEG
	c[NCK_PITCH] = -20.0 * DEG
	c[HD_PITCH] = -16.0 * DEG
	for side in range(2):
		var hip: float = 64.0 * DEG
		var knee: float = 88.0 * DEG
		c[leg_ch(side, L_HIP_FLEX)] = hip
		c[leg_ch(side, L_KNEE)] = knee
		c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - hip + knee)
		c[leg_ch(side, L_HIP_ABD)] = 9.0 * DEG
		c[arm_ch(side, A_SH_FLEX)] = 44.0 * DEG
		c[arm_ch(side, A_SH_ABD)] = 26.0 * DEG
		c[arm_ch(side, A_ELBOW)] = 62.0 * DEG
	return c


## The instant of impact: upper body snaps back, arms fly out, legs brace.
static func hit_recoil_pose() -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	c[PEL_PITCH] = 4.0 * DEG
	c[SPN_PITCH] = -10.0 * DEG
	c[CHS_PITCH] = -14.0 * DEG
	c[NCK_PITCH] = 14.0 * DEG
	c[HD_PITCH] = 14.0 * DEG
	for side in range(2):
		var hip: float = 28.0 * DEG
		var knee: float = 40.0 * DEG
		c[leg_ch(side, L_HIP_FLEX)] = hip
		c[leg_ch(side, L_KNEE)] = knee
		c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - hip + knee)
		c[leg_ch(side, L_HIP_ABD)] = 12.0 * DEG
		c[arm_ch(side, A_SH_FLEX)] = 96.0 * DEG
		c[arm_ch(side, A_SH_ABD)] = 62.0 * DEG
		c[arm_ch(side, A_ELBOW)] = 30.0 * DEG
		c[arm_ch(side, A_WRIST)] = -24.0 * DEG
	return c


## Dazed crouch after the stumble: knees bent, trunk folded, head down, hands towards the knees.
static func hit_down_pose() -> PackedFloat32Array:
	var c: PackedFloat32Array = new_pose()
	c[PEL_PITCH] = 36.0 * DEG
	c[SPN_PITCH] = 24.0 * DEG
	c[CHS_PITCH] = 22.0 * DEG
	c[NCK_PITCH] = -4.0 * DEG
	c[HD_PITCH] = 22.0 * DEG
	for side in range(2):
		var hip: float = 82.0 * DEG
		var knee: float = 100.0 * DEG
		c[leg_ch(side, L_HIP_FLEX)] = hip
		c[leg_ch(side, L_KNEE)] = knee
		c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - hip + knee)
		c[leg_ch(side, L_HIP_ABD)] = 14.0 * DEG
		c[arm_ch(side, A_SH_FLEX)] = 44.0 * DEG
		c[arm_ch(side, A_SH_ABD)] = 16.0 * DEG
		c[arm_ch(side, A_ELBOW)] = 34.0 * DEG
	return c


## Linear blend of two channel sets; returns the blended set (use the return value: `pose = ToonGait.blend_into(pose, other, w)`).
static func blend_into(into: PackedFloat32Array, other: PackedFloat32Array, w: float) -> PackedFloat32Array:
	if w <= 0.0001:
		return into
	for i in range(N_CH):
		into[i] = lerpf(into[i], other[i], w)
	return into
