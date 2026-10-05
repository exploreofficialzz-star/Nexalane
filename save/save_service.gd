extends Node
class_name SaveServiceImpl

## Local save with atomic writes, a rolling backup and crash recovery.
## NOTE: JSON has no integer type, so Godot parses every number as float. Loaded values are therefore
## coerced back to the type of the default value (see _coerce) - without this, every int field
## (credits, level, xp ...) would be reset to its default on each launch.

signal save_written(success: bool)

const SAVE_PATH := "user://nexalane_save.json"
const TMP_PATH := "user://nexalane_save.tmp"
const BACKUP_PATH := "user://nexalane_save.bak"
const SAVE_VERSION := 7

var data: Dictionary = {}
## "new" (no file), "ok", "recovered" (loaded the temp/backup copy) or "corrupt_reset"
var load_status := "new"

func _ready() -> void:
	load_game()

func default_save() -> Dictionary:
	return {
		"version": SAVE_VERSION,
		"profile": {"name": "Runner", "level": 1, "xp": 0, "selected_runner": "Kade", "equipped_power": "phase_shield", "equipped_cosmetic": ""},
		"consent": {"decided": false, "analytics": false, "ads": false, "personalized_ads": false},
		"currencies": {"credits": 0, "nova": 0, "event_tokens": 0},
		"inventory": {"runners": {"Kade": true}, "cosmetics": {}, "boards": {}, "trails": {}, "badges": {}},
		"progression": {"chapter": 1, "mission": 1, "challenge": "vault_01", "districts": {}, "runner_mastery": {}},
		"missions": {},
		"achievements": {},
		"story": {"completed_chapters": 0, "last_completed_chapter": 0},
		"daily": {"key": "", "best_score": 0, "claimed": false},
		"weekly": {"key": "", "best_score": 0, "claimed": false},
		"runs_completed": 0,
		"total_collectibles": 0,
		"settings": {"music": true, "sfx": true, "voice": true, "haptics": true, "graphics": "auto", "fps": 60, "left_handed": false, "camera_shake": true, "reduced_flashes": false, "colorblind_safe": true, "language": "en"},
		"tutorial_complete": false,
		"season": {"id": "season_01", "xp": 0, "claimed": [], "pass": false},
		"owned_products": {},
		"processed_transactions": {},
		"scores": {},
		"best_score": 0,
		"best_distance": 0.0
	}

func load_game() -> void:
	data = default_save()
	load_status = "new"
	for path in _candidate_paths():
		if not FileAccess.file_exists(path):
			continue
		var parsed: Variant = _read_json(path)
		if typeof(parsed) == TYPE_DICTIONARY:
			data = _migrate(parsed)
			load_status = "ok" if path == SAVE_PATH else "recovered"
			if load_status == "recovered":
				push_warning("SaveService: main save unreadable, recovered from %s" % path)
			return
		load_status = "corrupt_reset"

func _candidate_paths() -> Array[String]:
	# A complete temp file that is newer than the main file means we crashed between write and rename.
	var paths: Array[String] = [SAVE_PATH, TMP_PATH, BACKUP_PATH]
	if FileAccess.file_exists(TMP_PATH) and FileAccess.file_exists(SAVE_PATH):
		if FileAccess.get_modified_time(TMP_PATH) > FileAccess.get_modified_time(SAVE_PATH):
			paths = [TMP_PATH, SAVE_PATH, BACKUP_PATH]
	return paths

func _read_json(path: String) -> Variant:
	var f := FileAccess.open(path, FileAccess.READ)
	if f == null:
		return null
	var text := f.get_as_text()
	f.close()
	if text.strip_edges().is_empty():
		return null
	return JSON.parse_string(text)

func save_game() -> void:
	data["version"] = SAVE_VERSION
	var text := JSON.stringify(data, "\t")
	var f := FileAccess.open(TMP_PATH, FileAccess.WRITE)
	if f == null:
		push_warning("SaveService: cannot open %s (error %d)" % [TMP_PATH, FileAccess.get_open_error()])
		save_written.emit(false)
		return
	f.store_string(text)
	var write_error := f.get_error()
	f.close()
	if write_error != OK:
		push_warning("SaveService: write failed (error %d)" % write_error)
		save_written.emit(false)
		return
	var main_abs := ProjectSettings.globalize_path(SAVE_PATH)
	var tmp_abs := ProjectSettings.globalize_path(TMP_PATH)
	if FileAccess.file_exists(SAVE_PATH):
		DirAccess.copy_absolute(main_abs, ProjectSettings.globalize_path(BACKUP_PATH))
	var rename_error := DirAccess.rename_absolute(tmp_abs, main_abs)
	if rename_error != OK:
		push_warning("SaveService: rename failed (error %d)" % rename_error)
	save_written.emit(rename_error == OK)

func _migrate(source: Dictionary) -> Dictionary:
	var defaults := default_save()
	var result := defaults.duplicate(true)
	for key in source.keys():
		result[key] = source[key]
	var version := int(source.get("version", 1))
	_normalize(result, defaults)
	if version < 2:
		result["currencies"]["event_tokens"] = int(result["currencies"].get("event_tokens", 0))
	if version < 4:
		result["owned_products"] = {}
	if version < 5:
		result["consent"] = defaults["consent"].duplicate(true)
	if version < 6:
		result["story"] = defaults["story"].duplicate(true)
		result["daily"] = defaults["daily"].duplicate(true)
		result["weekly"] = defaults["weekly"].duplicate(true)
	if version < 7 and str(result["settings"].get("graphics", "auto")) == "mid":
		result["settings"]["graphics"] = "auto"
	var claimed: Array = []
	for tier in result["season"].get("claimed", []):
		claimed.append(int(tier))
	result["season"]["claimed"] = claimed
	result["version"] = SAVE_VERSION
	return result

## Fill missing keys and coerce scalar types so the rest of the game can trust the shape of `data`.
func _normalize(result: Dictionary, defaults: Dictionary) -> void:
	for key in defaults.keys():
		var default_value: Variant = defaults[key]
		if not result.has(key):
			result[key] = _clone(default_value)
		elif typeof(default_value) == TYPE_DICTIONARY:
			if typeof(result[key]) != TYPE_DICTIONARY:
				result[key] = _clone(default_value)
			else:
				_normalize(result[key], default_value)
		else:
			result[key] = _coerce(result[key], default_value)

static func _clone(value: Variant) -> Variant:
	if typeof(value) == TYPE_DICTIONARY or typeof(value) == TYPE_ARRAY:
		return value.duplicate(true)
	return value

static func _coerce(value: Variant, default_value: Variant) -> Variant:
	var want := typeof(default_value)
	var have := typeof(value)
	if have == want:
		return value
	if want == TYPE_INT and have == TYPE_FLOAT:
		return int(value)
	if want == TYPE_FLOAT and have == TYPE_INT:
		return float(value)
	return _clone(default_value)

func export_snapshot() -> Dictionary:
	return data.duplicate(true)

func merge_cloud_snapshot(cloud_raw: Dictionary) -> void:
	if cloud_raw.is_empty():
		return
	var cloud := _migrate(cloud_raw)
	data["best_score"] = maxi(int(data.get("best_score", 0)), int(cloud.get("best_score", 0)))
	data["best_distance"] = maxf(float(data.get("best_distance", 0.0)), float(cloud.get("best_distance", 0.0)))
	data["runs_completed"] = maxi(int(data.get("runs_completed", 0)), int(cloud.get("runs_completed", 0)))
	data["total_collectibles"] = maxi(int(data.get("total_collectibles", 0)), int(cloud.get("total_collectibles", 0)))
	data["profile"]["xp"] = maxi(int(data["profile"].get("xp", 0)), int(cloud["profile"].get("xp", 0)))
	data["profile"]["level"] = maxi(int(data["profile"].get("level", 1)), int(cloud["profile"].get("level", 1)))
	data["story"]["completed_chapters"] = maxi(int(data["story"].get("completed_chapters", 0)), int(cloud["story"].get("completed_chapters", 0)))
	data["progression"]["chapter"] = maxi(int(data["progression"].get("chapter", 1)), int(cloud["progression"].get("chapter", 1)))
	for bucket in ["runners", "cosmetics", "boards", "trails", "badges"]:
		for item_id in cloud["inventory"][bucket].keys():
			if bool(cloud["inventory"][bucket].get(item_id, false)):
				data["inventory"][bucket][item_id] = true
	for product_id in cloud["owned_products"].keys():
		if bool(cloud["owned_products"].get(product_id, false)):
			data["owned_products"][product_id] = true
	for currency in ["credits", "nova", "event_tokens"]:
		data["currencies"][currency] = maxi(int(data["currencies"].get(currency, 0)), int(cloud["currencies"].get(currency, 0)))
	if str(data["season"].get("id", "")) == str(cloud["season"].get("id", "")):
		data["season"]["xp"] = maxi(int(data["season"].get("xp", 0)), int(cloud["season"].get("xp", 0)))

func get_value(path: Array, fallback: Variant = null) -> Variant:
	var cursor: Variant = data
	for key in path:
		if typeof(cursor) != TYPE_DICTIONARY or not cursor.has(key):
			return fallback
		cursor = cursor[key]
	return cursor

func set_value(path: Array, value: Variant) -> void:
	if path.is_empty():
		return
	var cursor: Dictionary = data
	for i in range(path.size() - 1):
		var key: Variant = path[i]
		if not cursor.has(key) or typeof(cursor[key]) != TYPE_DICTIONARY:
			cursor[key] = {}
		cursor = cursor[key]
	cursor[path[-1]] = value
