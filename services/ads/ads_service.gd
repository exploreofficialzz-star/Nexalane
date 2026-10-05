extends Node
class_name AdsServiceImpl

## Ad mediation façade. A real SDK adapter calls set_provider(obj) with an object exposing
## show_rewarded(placement) / show_interstitial() and reports back through report_rewarded_result(bool).
## Rewarded placements are optional bonuses (revive, double reward). Players who bought "Remove Ads"
## receive those bonuses without watching anything.

signal rewarded_result(success: bool)
var provider: Object = null
var ads_removed := false
var interstitial_run_counter := 0
var test_mode := OS.is_debug_build()

func _ready() -> void:
	ads_removed = bool(SaveService.data.get("owned_products", {}).get("remove_ads_499", false))

## True when a rewarded bonus can be offered at all (ads consented, or the player owns Remove Ads).
func can_offer_rewarded() -> bool:
	return ads_removed or ConsentService.ads_allowed()

func show_rewarded(placement: String) -> void:
	if ads_removed:
		AnalyticsService.track("rewarded_granted_premium", {"placement": placement})
		rewarded_result.emit(true)
		return
	if not ConsentService.ads_allowed():
		rewarded_result.emit(false)
		return
	AnalyticsService.track("rewarded_started", {"placement": placement, "test_mode": test_mode})
	if provider != null and provider.has_method("show_rewarded"):
		provider.call("show_rewarded", placement)
	elif test_mode:
		rewarded_result.emit(true)
		AnalyticsService.track("rewarded_completed", {"placement": placement, "test_mode": true})
	else:
		rewarded_result.emit(false)
		AnalyticsService.track("rewarded_unavailable", {"placement": placement})

## Called by the SDK adapter when the rewarded ad finished (true) or failed / was dismissed early (false).
func report_rewarded_result(success: bool) -> void:
	rewarded_result.emit(success)

func show_interstitial() -> void:
	if ads_removed or not ConsentService.ads_allowed():
		return
	interstitial_run_counter += 1
	if interstitial_run_counter < int(RemoteConfigService.get_number("interstitial_min_runs", 4)):
		return
	interstitial_run_counter = 0
	AnalyticsService.track("interstitial_shown", {"test_mode": test_mode})
	if provider != null and provider.has_method("show_interstitial"):
		provider.call("show_interstitial")
	elif not test_mode:
		AnalyticsService.track("interstitial_unavailable")

func set_provider(next_provider: Object) -> void:
	provider = next_provider
