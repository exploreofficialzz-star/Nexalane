extends Node
class_name RemoteConfigServiceImpl

## Tuning values. A local override file (user://remote_config.json) is honoured in DEBUG builds only, so a
## release build can never be re-tuned (speed, ramp ...) by editing files on the device.

const OVERRIDE_PATH := "user://remote_config.json"

var config: Dictionary = {
	"base_speed": 16.0,
	"speed_ramp": 0.045,
	"max_speed": 31.0,
	"chunk_length": 48.0,
	"spawn_ahead": 260.0,
	"despawn_behind": 60.0,
	"interstitial_min_runs": 4,
	"rewarded_multiplier": 2.0,
	"flow_decay_per_sec": 0.035,
	"flow_near_miss_bonus": 0.10,
	"season_id": "season_01"
}

func _ready() -> void:
	if OS.is_debug_build():
		_apply_local_overrides()
	_configure_bounds()

func _apply_local_overrides() -> void:
	if not FileAccess.file_exists(OVERRIDE_PATH):
		return
	var f := FileAccess.open(OVERRIDE_PATH, FileAccess.READ)
	if f == null:
		return
	var parsed: Variant = JSON.parse_string(f.get_as_text())
	f.close()
	if typeof(parsed) != TYPE_DICTIONARY:
		return
	for key in parsed.keys():
		if not config.has(key):
			continue
		var want := typeof(config[key])
		var value: Variant = parsed[key]
		if typeof(value) == want:
			config[key] = value
		elif want == TYPE_INT and typeof(value) == TYPE_FLOAT:      # JSON numbers always arrive as float
			config[key] = int(value)
		elif want == TYPE_FLOAT and typeof(value) == TYPE_INT:
			config[key] = float(value)

func _configure_bounds() -> void:
	config["base_speed"] = clampf(float(config["base_speed"]), 8.0, 24.0)
	config["max_speed"] = clampf(maxf(float(config["max_speed"]), float(config["base_speed"])), 16.0, 42.0)
	config["speed_ramp"] = clampf(float(config["speed_ramp"]), 0.0, 0.10)
	config["chunk_length"] = clampf(float(config["chunk_length"]), 36.0, 64.0)
	config["spawn_ahead"] = clampf(float(config["spawn_ahead"]), 120.0, 600.0)
	config["despawn_behind"] = clampf(float(config["despawn_behind"]), 30.0, 180.0)
	config["interstitial_min_runs"] = clampi(int(config["interstitial_min_runs"]), 2, 12)
	config["rewarded_multiplier"] = clampf(float(config["rewarded_multiplier"]), 1.0, 4.0)
	config["flow_decay_per_sec"] = clampf(float(config["flow_decay_per_sec"]), 0.005, 0.2)
	config["flow_near_miss_bonus"] = clampf(float(config["flow_near_miss_bonus"]), 0.0, 0.4)

func get_number(key: String, fallback: float) -> float:
	return float(config.get(key, fallback))

func get_string(key: String, fallback: String) -> String:
	return str(config.get(key, fallback))
