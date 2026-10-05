extends Node
class_name SeasonEngineImpl

const MAX_TIER := 30
const XP_PER_TIER := 1000

func tier() -> int:
	return clampi(1 + int(floor(float(LiveOpsService.season_xp) / float(XP_PER_TIER))), 1, MAX_TIER)

func progress_to_next() -> float:
	if tier() >= MAX_TIER:
		return 1.0
	return float(LiveOpsService.season_xp % XP_PER_TIER) / float(XP_PER_TIER)

func reward_at_tier(value: int) -> Dictionary:
	return {"tier": value, "credits": 250 + value * 50, "nova": 20 if value % 5 == 0 else 0}

func is_claimed(tier_value: int) -> bool:
	return tier_value in SaveService.data["season"]["claimed"]

## Every reached tier that has not been claimed yet (players can no longer lose rewards by skipping a tier).
func claimable_tiers() -> Array[int]:
	var result: Array[int] = []
	for t in range(1, tier() + 1):
		if not is_claimed(t):
			result.append(t)
	return result

## Season-pass holders receive +50% credits on every tier.
func claim_all() -> int:
	var tiers := claimable_tiers()
	var boost := 1.5 if bool(SaveService.data["season"].get("pass", false)) else 1.0
	for t in tiers:
		var reward := reward_at_tier(t)
		EconomyService.grant("credits", int(round(float(reward["credits"]) * boost)), "season_tier")
		if int(reward["nova"]) > 0:
			EconomyService.grant("nova", int(reward["nova"]), "season_tier")
		SaveService.data["season"]["claimed"].append(t)
	if not tiers.is_empty():
		SaveService.save_game()
		AudioService.play_sfx("reward")
		AnalyticsService.track("season_claim", {"tiers": tiers.size()})
	return tiers.size()
