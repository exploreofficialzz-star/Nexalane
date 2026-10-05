extends Node
class_name EconomyServiceImpl

signal balance_changed(currency: String, balance: int, delta: int)
const CURRENCIES := ["credits", "nova", "event_tokens"]

func _ready() -> void:
	for c in CURRENCIES:
		if SaveService.data["currencies"].get(c) == null:
			SaveService.data["currencies"][c] = 0

func balance(currency: String) -> int:
	return int(SaveService.data["currencies"].get(currency, 0))

func grant(currency: String, amount: int, reason: String = "") -> bool:
	if currency not in CURRENCIES or amount < 0:
		return false
	SaveService.data["currencies"][currency] = balance(currency) + amount
	balance_changed.emit(currency, balance(currency), amount)
	AnalyticsService.track("currency_earned", {"currency": currency, "amount": amount, "reason": reason})
	return true

func spend(currency: String, amount: int, reason: String = "") -> bool:
	if currency not in CURRENCIES or amount < 0 or balance(currency) < amount:
		return false
	SaveService.data["currencies"][currency] = balance(currency) - amount
	balance_changed.emit(currency, balance(currency), -amount)
	AnalyticsService.track("currency_spent", {"currency": currency, "amount": amount, "reason": reason})
	SaveService.save_game()
	return true
