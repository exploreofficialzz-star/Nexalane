extends RefCounted
class_name TrackPlanner

## Deterministic, fairness-checked obstacle + collectible planner.
##
## Fairness rules (speed = estimated runner speed at that point of the track):
##  * every slot is separated by at least max(8 m, speed * 0.32 s);
##  * a slot that needs a lane change after another slot gets speed * 0.30 s + 3 m per lane to travel;
##  * jump/slide obstacles are separated from each other by speed * 0.8 s (the airtime of a jump);
##  * a "pair" (two lanes blocked) is only generated when the player can cross the whole road in time.
## A single blocked lane can always be avoided with at most one adjacent lane change, so single slots are
## always solvable once the minimum gap holds. Rows (all three lanes) require the matching jump/slide.

const LANE_X := [-3.2, 0.0, 3.2]
const REACTION_TIME := 0.30
const AIR_TIME := 0.80
const START_GRACE := 40.0
const COIN_SPACING := 2.2

var _prev_end_abs := START_GRACE
var _prev_vertical := false
var _prev_row := false

func reset(first_free_z: float = START_GRACE) -> void:
	_prev_end_abs = first_free_z
	_prev_vertical = false
	_prev_row = false

# --------------------------------------------------------------------------- regular chunk
## Returns {"obstacles": Array[Dictionary], "coins": Array[Dictionary], "boosts": Array[Dictionary]}.
## obstacle: {lane, z, family, id, kind, depth}; coin: {x, y, z, value}; boost: {lane, z}
func plan_chunk(random: RandomNumberGenerator, district_id: String, start_abs: float, length: float, difficulty: float, speed: float, collectible_hint: int) -> Dictionary:
	var obstacles: Array[Dictionary] = []
	var boosts: Array[Dictionary] = []
	var shift_gap := speed * REACTION_TIME + 3.0
	var air_gap := speed * AIR_TIME
	var min_gap := maxf(8.0, speed * 0.32)
	var max_slots := clampi(2 + int(floor(difficulty * 3.0)) + random.randi_range(0, 1), 2, 6)
	var placed := 0
	var attempts := 0
	while placed < max_slots and attempts < 14:
		attempts += 1
		var slot := _pick_slot(random, district_id, difficulty)
		var vertical: bool = slot["vertical"]
		var need := min_gap
		if vertical and _prev_vertical:
			need = maxf(need, air_gap)
		elif vertical or _prev_vertical:
			need = maxf(need, shift_gap + 4.0)
		else:
			need = maxf(need, shift_gap)
		if str(slot["type"]) == "pair":
			need = maxf(need, shift_gap * 2.0)
		if _prev_row:
			need = maxf(need, air_gap * 0.8)
		var depth: float = slot["depth"]
		var extra := random.randf_range(0.0, lerpf(14.0, 2.0, difficulty))
		var z_start := maxf(_prev_end_abs + need - start_abs, 4.0) + extra
		if z_start + depth > length - 2.0:
			break                                         # does not fit in this chunk; the next chunk continues from _prev_end_abs
		for item in slot["items"]:
			var entry: Dictionary = item
			entry["z"] = z_start + depth * 0.5
			obstacles.append(entry)
		_prev_end_abs = start_abs + z_start + depth
		_prev_vertical = vertical
		_prev_row = str(slot["type"]).begins_with("row")
		placed += 1
	return {"obstacles": obstacles, "coins": _plan_coins(random, obstacles, length, collectible_hint), "boosts": boosts}

func _pick_slot(random: RandomNumberGenerator, district_id: String, difficulty: float) -> Dictionary:
	var w_single := 1.0
	var w_row_jump := 0.0 if difficulty < 0.12 else 0.30
	var w_row_slide := 0.0 if difficulty < 0.20 else 0.20
	var w_pair := 0.0 if difficulty < 0.30 else 0.30 * difficulty
	var roll := random.randf() * (w_single + w_row_jump + w_row_slide + w_pair)
	if roll < w_row_jump:
		return _row_slot(random, district_id, ObstacleCatalog.Kind.JUMP)
	roll -= w_row_jump
	if roll < w_row_slide:
		return _row_slot(random, district_id, ObstacleCatalog.Kind.SLIDE)
	roll -= w_row_slide
	if roll < w_pair:
		return _pair_slot(random, district_id)
	return _single_slot(random, district_id, difficulty)

func _entry(random: RandomNumberGenerator, family: String, lane: int) -> Dictionary:
	return {"lane": lane, "z": 0.0, "family": family, "id": ObstacleCatalog.obstacle_id(family, random.randi_range(0, 3)),
		"kind": ObstacleCatalog.kind_of(family), "depth": ObstacleCatalog.depth_of(family)}

func _pick_family(random: RandomNumberGenerator, district_id: String, kind: int) -> String:
	var families := ObstacleCatalog.families_for(district_id, kind)
	return families[random.randi_range(0, families.size() - 1)]

func _single_slot(random: RandomNumberGenerator, district_id: String, difficulty: float) -> Dictionary:
	var roll := random.randf()
	var kind := ObstacleCatalog.Kind.DODGE
	if roll < 0.45 - 0.10 * difficulty:
		kind = ObstacleCatalog.Kind.DODGE
	elif roll < 0.78:
		kind = ObstacleCatalog.Kind.JUMP
	else:
		kind = ObstacleCatalog.Kind.SLIDE
	var family := _pick_family(random, district_id, kind)
	var entry := _entry(random, family, random.randi_range(0, 2))
	return {"type": "single", "items": [entry], "depth": float(entry["depth"]), "vertical": kind != ObstacleCatalog.Kind.DODGE}

func _row_slot(random: RandomNumberGenerator, district_id: String, kind: int) -> Dictionary:
	var family := _pick_family(random, district_id, kind)
	var items: Array[Dictionary] = []
	var depth := 0.0
	for lane in 3:
		var entry := _entry(random, family, lane)
		depth = maxf(depth, float(entry["depth"]))
		items.append(entry)
	return {"type": "row_jump" if kind == ObstacleCatalog.Kind.JUMP else "row_slide", "items": items, "depth": depth, "vertical": true}

func _pair_slot(random: RandomNumberGenerator, district_id: String) -> Dictionary:
	var family := _pick_family(random, district_id, ObstacleCatalog.Kind.DODGE)
	var free_lane := random.randi_range(0, 2)
	var items: Array[Dictionary] = []
	var depth := 0.0
	for lane in 3:
		if lane == free_lane:
			continue
		var entry := _entry(random, family, lane)
		depth = maxf(depth, float(entry["depth"]))
		items.append(entry)
	return {"type": "pair", "items": items, "depth": depth, "vertical": false}

# --------------------------------------------------------------------------- collectibles
func _lane_blocked(obstacles: Array[Dictionary], lane: int, z: float) -> bool:
	for o in obstacles:
		if int(o["lane"]) == lane and absf(z - float(o["z"])) < float(o["depth"]) * 0.5 + 1.4:
			return true
	return false

func _plan_coins(random: RandomNumberGenerator, obstacles: Array[Dictionary], length: float, hint: int) -> Array[Dictionary]:
	var coins: Array[Dictionary] = []
	var runs := 1 + random.randi_range(0, 1) + (1 if hint > 9 else 0)
	for r in runs:
		var shape := random.randi_range(0, 2)                  # 0 line, 1 diagonal, 2 arc over a jump obstacle
		var count := random.randi_range(4, 8)
		var lane := random.randi_range(0, 2)
		var z0 := random.randf_range(6.0, maxf(7.0, length - 6.0 - float(count) * COIN_SPACING))
		if shape == 2:
			var jump_item: Dictionary = {}
			for o in obstacles:
				if int(o["kind"]) == ObstacleCatalog.Kind.JUMP:
					jump_item = o
					break
			if jump_item.is_empty():
				shape = 0
			else:
				var cz: float = jump_item["z"]
				var cx: float = LANE_X[int(jump_item["lane"])]
				for i in 5:
					var t := float(i) / 4.0
					coins.append({"x": cx, "y": 1.5 + 0.6 * sin(PI * t), "z": cz + (float(i) - 2.0) * 1.9, "value": 10})
				continue
		var lane_to := clampi(lane + random.randi_range(-1, 1), 0, 2)
		for i in count:
			var t := float(i) / float(maxi(1, count - 1))
			var z := z0 + float(i) * COIN_SPACING
			var x: float = lerpf(LANE_X[lane], LANE_X[lane_to], t) if shape == 1 else LANE_X[lane]
			var nearest := clampi(int(round((x + 3.2) / 3.2)), 0, 2)
			if _lane_blocked(obstacles, nearest, z):
				continue
			coins.append({"x": x, "y": 0.9, "z": z, "value": 10})
	return coins

# --------------------------------------------------------------------------- route fork chunk
## options[lane] = route class of that lane. The arch stands at z = 6; lane content follows.
func plan_fork(random: RandomNumberGenerator, options: Array[String], start_abs: float, length: float, speed: float) -> Dictionary:
	var obstacles: Array[Dictionary] = []
	var coins: Array[Dictionary] = []
	var boosts: Array[Dictionary] = []
	var air_gap := speed * AIR_TIME
	for lane in 3:
		var x: float = LANE_X[lane]
		match options[lane]:
			"SAFE":
				for i in 7:
					coins.append({"x": x, "y": 0.9, "z": 16.0 + float(i) * COIN_SPACING, "value": 10})
			"REWARD":
				var barrier := _entry(random, "barrier", lane)
				barrier["z"] = 28.0
				obstacles.append(barrier)
				for i in 5:
					var t := float(i) / 4.0
					coins.append({"x": x, "y": 1.5 + 0.6 * sin(PI * t), "z": 28.0 + (float(i) - 2.0) * 1.9, "value": 10})
				for i in 5:
					coins.append({"x": x, "y": 0.9, "z": 14.0 + float(i) * COIN_SPACING, "value": 10})
				for i in 3:
					coins.append({"x": x, "y": 0.9, "z": 35.0 + float(i) * COIN_SPACING, "value": 10})
			"FAST":
				boosts.append({"lane": lane, "z": 16.0})
				for i in 6:
					coins.append({"x": x, "y": 0.9, "z": 25.0 + float(i) * COIN_SPACING, "value": 10})
			"SECRET":
				var beam := _entry(random, "low_beam", lane)
				beam["z"] = 28.0
				obstacles.append(beam)
				for i in 5:
					coins.append({"x": x, "y": 0.5, "z": 26.0 + float(i) * 1.2, "value": 25})
				for i in 4:
					coins.append({"x": x, "y": 0.9, "z": 14.0 + float(i) * COIN_SPACING, "value": 10})
			_:    # CHAOS: jump, slide, jump - as many as fit with fair spacing
				var z := 16.0
				var kinds := ["gap", "gate", "barrier"]
				for k in kinds:
					var entry := _entry(random, str(k), lane)
					if z + float(entry["depth"]) > length - 3.0:
						break
					entry["z"] = z + float(entry["depth"]) * 0.5
					obstacles.append(entry)
					for j in 3:
						coins.append({"x": x, "y": 1.5 if int(entry["kind"]) == ObstacleCatalog.Kind.JUMP else 0.5, "z": float(entry["z"]) + (float(j) - 1.0) * 1.6, "value": 15})
					z += float(entry["depth"]) + air_gap
	_prev_end_abs = start_abs + length
	_prev_vertical = true
	_prev_row = false
	return {"obstacles": obstacles, "coins": coins, "boosts": boosts}
