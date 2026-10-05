extends Node
class_name AccessibilityServiceImpl

signal settings_changed

func is_enabled(key: String) -> bool:
	return bool(SaveService.data["settings"].get(key, false))

func set_setting(key: String, value: Variant) -> void:
	SaveService.data["settings"][key] = value
	if key == "music":
		AudioService.set_music_enabled(bool(value))
	elif key == "sfx":
		AudioService.set_sfx_enabled(bool(value))
	elif key == "graphics":
		DeviceProfileService.refresh()
	SaveService.save_game()
	settings_changed.emit()

func haptic(kind: String = "light") -> void:
	if not is_enabled("haptics"):
		return
	var duration := 18 if kind == "light" else (35 if kind == "medium" else 55)
	Input.vibrate_handheld(duration)

## 0..1 multiplier for camera shake / screen kicks (off when the player disabled shake or wants reduced flashes).
func shake_scale() -> float:
	if not is_enabled("camera_shake"):
		return 0.0
	return 0.35 if is_enabled("reduced_flashes") else 1.0

## Duration multiplier for full-screen fades/flashes.
func flash_scale() -> float:
	return 0.0 if is_enabled("reduced_flashes") else 1.0
