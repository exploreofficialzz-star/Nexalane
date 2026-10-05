extends Node
class_name LeaderboardServiceImpl

var leaderboard_id := "weekly_global"

func submit_current_run() -> bool:
	var score := int(AppState.run_score)
	var distance := float(AppState.run_distance)
	var validation_hash := "%s:%s:%s:%s" % [AppState.active_seed, score, int(distance), AppState.CONTENT_VERSION]
	if not BackendService.validate_run(AppState.active_seed, score, distance, AppState.CONTENT_VERSION, validation_hash):
		return false
	return BackendService.submit_score(leaderboard_id, score, {"distance": distance, "runner": AppState.selected_runner})

func top_scores() -> Array[Dictionary]:
	return BackendService.fetch_leaderboard(leaderboard_id)
