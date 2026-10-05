extends Node
class_name BackendServiceImpl

signal connectivity_changed(online: bool)
var provider: Object = null
var online := false
var last_error := ""
var _leaderboard_cache: Array[Dictionary] = []
var test_mode := OS.is_debug_build()

func connect_account() -> bool:
	if provider != null and provider.has_method("connect_account"):
		online = bool(provider.call("connect_account"))
	else:
		online = false
	connectivity_changed.emit(online)
	return online

func submit_score(leaderboard_id: String, score: int, metadata: Dictionary = {}) -> bool:
	if score < 0:
		last_error = "invalid_score"
		return false
	if provider != null and provider.has_method("submit_score"):
		return bool(provider.call("submit_score", leaderboard_id, score, metadata))
	return test_mode

func fetch_leaderboard(leaderboard_id: String) -> Array[Dictionary]:
	if provider != null and provider.has_method("fetch_leaderboard"):
		var result: Variant = provider.call("fetch_leaderboard", leaderboard_id)
		var rows: Array[Dictionary] = []
		if typeof(result) == TYPE_ARRAY:
			for row in result:
				if typeof(row) == TYPE_DICTIONARY:
					rows.append(row)
		_leaderboard_cache = rows
	var copy: Array[Dictionary] = []
	for row in _leaderboard_cache:
		copy.append(row.duplicate(true))
	return copy

func validate_run(run_seed: int, score: int, distance: float, content_version: String, client_hash: String) -> bool:
	if run_seed == 0 or score < 0 or distance < 0.0 or content_version.is_empty() or client_hash.is_empty():
		last_error = "invalid_payload"
		return false
	var expected := "%s:%s:%s:%s" % [run_seed, score, int(distance), content_version]
	if client_hash != expected:
		last_error = "hash_mismatch"
		return false
	# Conservative sanity bound for client-reported score. Server adapters should re-simulate in production.
	if score > int(distance * 65.0) + 5000:
		last_error = "score_out_of_bounds"
		return false
	return true

func save_cloud_snapshot() -> bool:
	if provider != null and provider.has_method("save_cloud_snapshot"):
		return bool(provider.call("save_cloud_snapshot", SaveService.export_snapshot()))
	return false

func sync_cloud_snapshot() -> bool:
	var cloud := load_cloud_snapshot()
	if cloud.is_empty():
		return save_cloud_snapshot()
	SaveService.merge_cloud_snapshot(cloud)
	SaveService.save_game()
	return true

func load_cloud_snapshot() -> Dictionary:
	if provider != null and provider.has_method("load_cloud_snapshot"):
		var result: Variant = provider.call("load_cloud_snapshot")
		if typeof(result) == TYPE_DICTIONARY:
			return result
	return {}

func set_provider(next_provider: Object) -> void:
	provider = next_provider
