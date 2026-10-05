extends Node
class_name PowerSystem

## One equipped power per run. After a power ends (expires or is consumed) it recharges for COOLDOWNS[id]
## seconds of run time - without a cooldown a shield could simply be re-triggered forever.

signal power_changed(power_id: String, active: bool, remaining: float)

const POWERS := ["phase_shield", "magnet", "overdrive", "time_warp", "route_scanner", "double_credits", "recovery_pulse", "flow_surge"]
const DURATIONS := {"phase_shield": 5.5, "magnet": 7.0, "overdrive": 4.0, "time_warp": 5.0, "route_scanner": 6.0, "double_credits": 8.0, "recovery_pulse": 9.0, "flow_surge": 1.5}
const COOLDOWNS := {"phase_shield": 22.0, "magnet": 18.0, "overdrive": 28.0, "time_warp": 26.0, "route_scanner": 20.0, "double_credits": 30.0, "recovery_pulse": 34.0, "flow_surge": 24.0}

var equipped := "phase_shield"
var remaining := 0.0
var active := false
var cooldown_remaining := 0.0
var cooldown_total := 0.0

func reset_for_run() -> void:
	active = false
	remaining = 0.0
	cooldown_remaining = 0.0
	cooldown_total = 0.0

func is_ready() -> bool:
	return not active and cooldown_remaining <= 0.0

## 1.0 = ready, 0.0 = just used.
func ready_fraction() -> float:
	if active:
		return 0.0
	if cooldown_total <= 0.0:
		return 1.0
	return clampf(1.0 - cooldown_remaining / cooldown_total, 0.0, 1.0)

func activate(power_id: String = equipped) -> bool:
	if power_id not in POWERS or not is_ready():
		return false
	equipped = power_id
	remaining = float(DURATIONS.get(power_id, 5.0))
	active = true
	power_changed.emit(power_id, true, remaining)
	AudioService.play_sfx("shield_on" if power_id == "phase_shield" else "overdrive")
	AnalyticsService.track("power_activated", {"power": power_id})
	return true

func deactivate(reason: String = "expired") -> void:
	if not active:
		return
	active = false
	remaining = 0.0
	cooldown_total = float(COOLDOWNS.get(equipped, 20.0))
	cooldown_remaining = cooldown_total
	power_changed.emit(equipped, false, 0.0)
	AnalyticsService.track("power_deactivated", {"power": equipped, "reason": reason})

func tick(delta: float) -> void:
	if active:
		remaining = maxf(0.0, remaining - delta)
		if remaining <= 0.0:
			deactivate("expired")
			return
		power_changed.emit(equipped, true, remaining)
	elif cooldown_remaining > 0.0:
		cooldown_remaining = maxf(0.0, cooldown_remaining - delta)
		if cooldown_remaining <= 0.0:
			AudioService.play_sfx("power_ready")
