extends Node
class_name GameModeServiceImpl

signal mode_changed(mode: String)

const MODE_NAMES := ["ENDLESS", "STORY", "DAILY", "WEEKLY", "EVENT", "TRAINING", "GHOST", "CHALLENGE"]
var selected_mode := "ENDLESS"
var selected_story_chapter := 1

func _ready() -> void:
	selected_story_chapter = clampi(int(SaveService.data.get("progression", {}).get("chapter", 1)), 1, 12)

func set_mode(mode: String) -> void:
	var normalized := mode.to_upper()
	if normalized not in MODE_NAMES:
		normalized = "ENDLESS"
	selected_mode = normalized
	mode_changed.emit(selected_mode)

func mode_enum() -> AppStateService.GameMode:
	match selected_mode:
		"STORY": return AppStateService.GameMode.STORY
		"DAILY": return AppStateService.GameMode.DAILY
		"WEEKLY": return AppStateService.GameMode.WEEKLY
		"EVENT": return AppStateService.GameMode.EVENT
		"TRAINING": return AppStateService.GameMode.TRAINING
		"GHOST": return AppStateService.GameMode.GHOST
		"CHALLENGE": return AppStateService.GameMode.CHALLENGE
		_: return AppStateService.GameMode.ENDLESS

func mode_label() -> String:
	match selected_mode:
		"STORY": return "STORY • CHAPTER %02d" % selected_story_chapter
		"DAILY": return "DAILY • %s" % daily_key()
		"WEEKLY": return "WEEKLY • %s" % weekly_key()
		"EVENT": return "EVENT • %s" % EventEngine.active_modifier.to_upper()
		"TRAINING": return "TRAINING • PRACTICE"
		"GHOST": return "GHOST • LAST RUN"
		"CHALLENGE": return "CHALLENGE • %s" % ChallengeService.selected_id.to_upper()
		_: return "ENDLESS • PERSONAL BEST"

func seed_for_selected_mode() -> int:
	match selected_mode:
		"STORY": return _stable_seed("story|%d|%s" % [selected_story_chapter, AppState.CONTENT_VERSION])
		"DAILY": return _stable_seed("daily|%s|%s" % [daily_key(), AppState.CONTENT_VERSION])
		"WEEKLY": return _stable_seed("weekly|%s|%s" % [weekly_key(), AppState.CONTENT_VERSION])
		"EVENT": return _stable_seed("event|%s|%s" % [EventEngine.active_event_id, daily_key()])
		"TRAINING": return _stable_seed("training|%s" % AppState.CONTENT_VERSION)
		"GHOST":
			var ghost: Dictionary = GhostService.load_local_ghost()
			if not ghost.is_empty():
				return maxi(1, int(ghost.get("seed", 0)))
			return _stable_seed("ghost|empty|%s" % AppState.CONTENT_VERSION)
		"CHALLENGE": return _stable_seed("challenge|%s|%s" % [ChallengeService.selected_id, AppState.CONTENT_VERSION])
		_:
			var rng := RandomNumberGenerator.new()
			rng.randomize()
			return maxi(1, int(rng.randi()))

func objective_text() -> String:
	var obj := objective()
	match str(obj["kind"]):
		"distance": return "REACH %.0fm" % float(obj["target"])
		"score": return "SCORE %.0f" % float(obj["target"])
		"collect": return "COLLECT %.0f" % float(obj["target"])
		"flow_stage": return "REACH FLOW STAGE %d" % int(obj["target"])
		_: return "RUN AS FAR AS YOU CAN"

func objective() -> Dictionary:
	match selected_mode:
		"STORY":
			var chapter_index := selected_story_chapter - 1
			match chapter_index % 4:
				0:
					return {"kind": "distance", "target": 450.0 + float(chapter_index * 125), "reward": 450 + selected_story_chapter * 80}
				1:
					return {"kind": "score", "target": 1800.0 + float(chapter_index * 700), "reward": 500 + selected_story_chapter * 90}
				2:
					return {"kind": "collect", "target": 12.0 + float(chapter_index * 3), "reward": 550 + selected_story_chapter * 95}
				_:
					return {"kind": "flow_stage", "target": 3.0 if selected_story_chapter < 9 else 4.0, "reward": 600 + selected_story_chapter * 100}
		"DAILY":
			return {"kind": "distance", "target": 1800.0, "reward": 900}
		"WEEKLY":
			return {"kind": "distance", "target": 4000.0, "reward": 1800}
		"EVENT":
			return {"kind": "distance", "target": 2500.0, "reward": 1500}
		"TRAINING":
			return {"kind": "distance", "target": 900.0, "reward": 100}
		"CHALLENGE":
			var challenge := ChallengeService.current()
			return {"kind": "distance", "target": float(challenge.get("target", 250.0)), "reward": int(challenge.get("reward", 300))}
		"GHOST":
			return {"kind": "distance", "target": 1200.0, "reward": 250}
		_:
			return {"kind": "endless", "target": 0.0, "reward": 0}

## Daily/weekly keys use UTC so that every player in the world shares the same board at the same moment.
func daily_key() -> String:
	var date := Time.get_date_dict_from_system(true)
	return "%04d-%02d-%02d" % [int(date["year"]), int(date["month"]), int(date["day"])]

## Weeks start on Monday (UTC). Unix day 0 was a Thursday, hence the +3 offset.
func weekly_key() -> String:
	var day_index := int(floor(Time.get_unix_time_from_system() / 86400.0))
	return "W%04d" % int(floor(float(day_index + 3) / 7.0))

## FNV-1a (32 bit). Unlike the built-in hash() this is guaranteed identical across engine versions and
## platforms, which daily/weekly/story seeds rely on.
static func stable_hash(text: String) -> int:
	var h := 2166136261
	for b in text.to_utf8_buffer():
		h = ((h ^ int(b)) * 16777619) & 0xFFFFFFFF
	return h

func _stable_seed(value: String) -> int:
	return maxi(1, stable_hash(value))
