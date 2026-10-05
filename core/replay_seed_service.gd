extends Node
class_name ReplaySeedServiceImpl

func current_seed() -> int:
	return int(AppState.active_seed)

func build_token(run_seed: int = 0) -> String:
	var selected_seed := run_seed if run_seed != 0 else current_seed()
	return "NEXALANE|%s|%s|%s" % [selected_seed, AppState.CONTENT_VERSION, AppState.TUNING_VERSION]

func parse_token(token: String) -> Dictionary:
	var parts := token.split("|")
	if parts.size() != 4 or parts[0] != "NEXALANE":
		return {}
	return {"seed": int(parts[1]), "content_version": parts[2], "tuning_version": int(parts[3])}

func deterministic_signature(run_seed: int) -> String:
	return "%s:%s:%s" % [run_seed, AppState.CONTENT_VERSION, AppState.TUNING_VERSION]
