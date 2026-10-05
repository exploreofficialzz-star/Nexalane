extends Node
class_name ShopServiceImpl

signal cosmetic_equipped(cosmetic_id: String)

func purchase_cosmetic(cosmetic_id: String) -> bool:
	for item in ContentRegistry.cosmetics():
		if item["id"] != cosmetic_id:
			continue
		if is_owned(cosmetic_id):
			AudioService.play_sfx("purchase_error")
			return false
		if not EconomyService.spend(str(item["currency"]), int(item["cost"]), "cosmetic_shop"):
			AudioService.play_sfx("purchase_error")
			return false
		SaveService.data["inventory"]["cosmetics"][cosmetic_id] = true
		SaveService.save_game()
		AudioService.play_sfx("purchase_success")
		AnalyticsService.track("shop_purchase", {"item_id": cosmetic_id})
		return true
	return false

func is_owned(cosmetic_id: String) -> bool:
	return bool(SaveService.data["inventory"]["cosmetics"].get(cosmetic_id, false))

func equipped() -> String:
	return str(SaveService.data["profile"].get("equipped_cosmetic", ""))

## Pass "" to unequip. Returns false if the outfit is not owned.
func equip_cosmetic(cosmetic_id: String) -> bool:
	if cosmetic_id != "" and not is_owned(cosmetic_id):
		return false
	SaveService.data["profile"]["equipped_cosmetic"] = cosmetic_id
	SaveService.save_game()
	cosmetic_equipped.emit(cosmetic_id)
	return true

func purchase_event_item(item_id: String) -> bool:
	for item in ContentRegistry.event_shop():
		if item["id"] != item_id:
			continue
		if not EconomyService.spend("event_tokens", int(item["cost"]), "event_shop"):
			AudioService.play_sfx("purchase_error")
			return false
		EconomyService.grant("credits", int(item["reward_credits"]), "event_shop")
		if int(item["reward_nova"]) > 0:
			EconomyService.grant("nova", int(item["reward_nova"]), "event_shop")
		AudioService.play_sfx("purchase_success")
		SaveService.save_game()
		AnalyticsService.track("event_shop_purchase", {"item_id": item_id})
		return true
	return false

func catalog() -> Array[Dictionary]:
	return ContentRegistry.cosmetics()
