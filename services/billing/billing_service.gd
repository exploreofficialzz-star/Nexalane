extends Node
class_name BillingServiceImpl

## Store billing façade. A real adapter (Google Play Billing / StoreKit) calls set_provider(obj) with an
## object exposing purchase(product_id) and restore_purchases(), and reports results through
## complete_purchase(product_id, transaction_id) / fail_purchase(product_id, reason).
## Entitlements are applied exactly once per transaction id and non-consumables never re-grant bundle
## contents when restored.

signal purchase_succeeded(product_id: String)
signal purchase_failed(product_id: String, reason: String)

const PRODUCTS := {
	"nexalane_starter_299": {"type": "non_consumable_bundle", "credits": 2500, "nova": 150, "cosmetics": ["outfit_01"]},
	"nova_small_099": {"type": "consumable", "nova": 120},
	"nova_medium_499": {"type": "consumable", "nova": 700},
	"nova_large_999": {"type": "consumable", "nova": 1600},
	"nova_xlarge_1999": {"type": "consumable", "nova": 3600},
	"remove_ads_499": {"type": "non_consumable"},
	"season_pass_999": {"type": "entitlement"},
	"event_bundle_299": {"type": "bundle", "event_tokens": 120, "credits": 1200},
	"premium_cosmetic_499": {"type": "cosmetic", "cosmetics": ["outfit_22"]},
	"elite_bundle_999": {"type": "bundle", "nova": 1200, "credits": 6000, "cosmetics": ["outfit_24"]}
}
const ONE_TIME_TYPES := ["non_consumable", "non_consumable_bundle", "entitlement", "cosmetic"]

var provider: Object = null
var test_mode := OS.is_debug_build()
var _pending: Dictionary = {}

func is_one_time(product_id: String) -> bool:
	return str(PRODUCTS.get(product_id, {}).get("type", "")) in ONE_TIME_TYPES

func is_owned(product_id: String) -> bool:
	return bool(SaveService.data["owned_products"].get(product_id, false))

func purchase(product_id: String) -> void:
	if not PRODUCTS.has(product_id):
		fail_purchase(product_id, "unknown_product")
		return
	if _pending.has(product_id):
		return
	if is_one_time(product_id) and is_owned(product_id):
		fail_purchase(product_id, "already_owned")
		return
	AnalyticsService.track("purchase_start", {"product_id": product_id})
	if provider != null and provider.has_method("purchase"):
		_pending[product_id] = true
		provider.call("purchase", product_id)
	elif test_mode:
		complete_purchase(product_id, "test-%d" % Time.get_ticks_usec())
	else:
		fail_purchase(product_id, "billing_provider_unavailable")

## Adapter callback: the store confirmed the purchase.
func complete_purchase(product_id: String, transaction_id: String = "") -> void:
	_pending.erase(product_id)
	if not PRODUCTS.has(product_id):
		fail_purchase(product_id, "unknown_product")
		return
	var processed: Dictionary = SaveService.data["processed_transactions"]
	if transaction_id != "" and processed.has(transaction_id):
		return                                           # duplicate delivery from the store
	if transaction_id != "":
		processed[transaction_id] = true
	var first_time := not (is_one_time(product_id) and is_owned(product_id))
	_apply_entitlement(product_id, first_time)
	purchase_succeeded.emit(product_id)
	AudioService.play_sfx("purchase_success")
	AnalyticsService.track("purchase_success", {"product_id": product_id, "test_mode": test_mode, "restored": not first_time})

## Adapter callback: cancelled / declined / failed.
func fail_purchase(product_id: String, reason: String) -> void:
	_pending.erase(product_id)
	purchase_failed.emit(product_id, reason)
	AudioService.play_sfx("purchase_error")
	AnalyticsService.track("purchase_failed", {"product_id": product_id, "reason": reason})

func restore_purchases() -> void:
	if provider != null and provider.has_method("restore_purchases"):
		provider.call("restore_purchases")
	AnalyticsService.track("restore_purchases", {"test_mode": test_mode})

func set_provider(next_provider: Object) -> void:
	provider = next_provider

func _apply_entitlement(product_id: String, grant_contents: bool) -> void:
	var def: Dictionary = PRODUCTS[product_id]
	if is_one_time(product_id):
		SaveService.data["owned_products"][product_id] = true
	if product_id == "remove_ads_499":
		AdsService.ads_removed = true
	elif product_id == "season_pass_999":
		SaveService.data["season"]["pass"] = true
	if grant_contents:
		for currency in ["credits", "nova", "event_tokens"]:
			var amount := int(def.get(currency, 0))
			if amount > 0:
				EconomyService.grant(currency, amount, "purchase:" + product_id)
		for cosmetic_id in def.get("cosmetics", []):
			SaveService.data["inventory"]["cosmetics"][str(cosmetic_id)] = true
	SaveService.save_game()
