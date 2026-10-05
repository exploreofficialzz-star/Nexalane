extends Node
class_name ConsentServiceImpl

signal consent_changed

func has_decision() -> bool:
	var consent: Dictionary = SaveService.data.get("consent", {})
	return bool(consent.get("decided", false))

func analytics_allowed() -> bool:
	var consent: Dictionary = SaveService.data.get("consent", {})
	return bool(consent.get("analytics", false))

func ads_allowed() -> bool:
	var consent: Dictionary = SaveService.data.get("consent", {})
	return bool(consent.get("ads", false))

func set_consent(analytics: bool, ads: bool, personalized_ads: bool = false) -> void:
	SaveService.data["consent"] = {
		"decided": true,
		"analytics": analytics,
		"ads": ads,
		"personalized_ads": personalized_ads
	}
	SaveService.save_game()
	AnalyticsService.enabled = analytics
	consent_changed.emit()

func clear_consent() -> void:
	SaveService.data["consent"] = {
		"decided": false,
		"analytics": false,
		"ads": false,
		"personalized_ads": false
	}
	SaveService.save_game()
	AnalyticsService.enabled = false
	consent_changed.emit()
