extends Node
class_name AudioServiceImpl

## Music (cross-faded, looping, with intensity layers kept in sync) and polyphonic SFX on dedicated buses.
## Buses "Music" and "SFX" are created at runtime, so the settings toggles can simply mute them.

const VOICES := 3
const MUSIC_DB := -4.0
const SILENT_DB := -60.0

const CLIPS := {
	"ui_tap": "res://audio/generated/ui_tap.wav",
	"ui_confirm": "res://audio/sfx/ui_confirm.wav",
	"ui_cancel": "res://audio/sfx/ui_cancel.wav",
	"lane_change": "res://audio/generated/lane_change.wav",
	"jump": "res://audio/sfx/jump.wav",
	"slide": "res://audio/sfx/slide.wav",
	"land": "res://audio/sfx/land.wav",
	"pickup": "res://audio/generated/pickup.wav",
	"reward": "res://audio/sfx/reward.wav",
	"purchase_success": "res://audio/sfx/purchase_success.wav",
	"purchase_error": "res://audio/sfx/purchase_error.wav",
	"collision": "res://audio/sfx/collision.wav",
	"shield_on": "res://audio/sfx/shield_on.wav",
	"shield_hit": "res://audio/sfx/shield_hit.wav",
	"overdrive": "res://audio/generated/overdrive.wav",
	"near_miss": "res://audio/sfx/near_miss.wav",
	"power_ready": "res://audio/sfx/power_ready.wav",
	"countdown": "res://audio/sfx/countdown.wav",
	"go": "res://audio/sfx/go.wav",
	"revive": "res://audio/sfx/revive.wav"
}
## Per-clip gain trim (dB). Clips are normalised at generation time; this balances them against each other.
const CLIP_GAIN_DB := {
	"ui_tap": -7.0, "ui_confirm": -5.0, "ui_cancel": -6.0, "lane_change": -9.0, "jump": -7.0, "slide": -9.0,
	"land": -8.0, "pickup": -8.0, "near_miss": -8.0, "power_ready": -8.0, "countdown": -7.0, "go": -5.0,
	"collision": -2.0, "shield_hit": -4.0, "shield_on": -5.0, "overdrive": -5.0, "reward": -5.0, "revive": -5.0
}
const VARIATION := ["ui_tap", "lane_change", "jump", "slide", "land", "pickup", "near_miss"]

const MUSIC := {
	"menu": "res://audio/music_ogg/menu.ogg",
	"old_quarter": "res://audio/music_ogg/district_old_quarter.ogg",
	"transit_core": "res://audio/music_ogg/district_transit_core.ogg",
	"harbor_arc": "res://audio/music_ogg/district_harbor_arc.ogg",
	"industrial_belt": "res://audio/music_ogg/district_industrial_belt.ogg",
	"skyline_works": "res://audio/music_ogg/district_skyline_works.ogg",
	"neon_market": "res://audio/music_ogg/district_neon_market.ogg",
	"stormline": "res://audio/music_ogg/district_stormline.ogg",
	"central_spire": "res://audio/music_ogg/district_central_spire.ogg",
	"event": "res://audio/music_ogg/event.ogg",
	"reward": "res://audio/music_ogg/reward.ogg"
}
## Rhythmic stems recorded on the same 120 BPM grid as every music loop: they are started at the playhead of the
## current track so they always stay in time.
const MUSIC_LAYERS := {
	"chase": "res://audio/music_ogg/chase.ogg",
	"overdrive": "res://audio/music_ogg/overdrive.ogg"
}
const LAYER_DB := {"chase": -8.0, "overdrive": -7.0}

var music_enabled := true
var sfx_enabled := true
var gameplay_intensity := 0.0
var current_music := ""

var _voices: Dictionary = {}
var _voice_cursor: Dictionary = {}
var _music_a: AudioStreamPlayer
var _music_b: AudioStreamPlayer
var _active_music: AudioStreamPlayer
var _layer_players: Dictionary = {}
var _layer_state: Dictionary = {}
var _tweens: Dictionary = {}
var _rng := RandomNumberGenerator.new()

func _ready() -> void:
	_rng.randomize()
	_ensure_bus("Music")
	_ensure_bus("SFX")
	music_enabled = bool(SaveService.data["settings"].get("music", true))
	sfx_enabled = bool(SaveService.data["settings"].get("sfx", true))
	_apply_mutes()
	for id in CLIPS.keys():
		var stream := load(str(CLIPS[id])) as AudioStream
		if stream == null:
			continue
		var pool: Array = []
		for i in VOICES:
			var player := AudioStreamPlayer.new()
			player.name = "SFX_%s_%d" % [id, i]
			player.stream = stream
			player.bus = "SFX"
			add_child(player)
			pool.append(player)
		_voices[id] = pool
	_music_a = _make_player("Music_A", "Music")
	_music_b = _make_player("Music_B", "Music")
	for layer in MUSIC_LAYERS.keys():
		_layer_players[layer] = _make_player("Layer_%s" % layer, "Music")
		_layer_state[layer] = false
	AppState.paused_changed.connect(_on_paused_changed)
	call_deferred("play_music", "menu")

func _make_player(player_name: String, bus_name: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.name = player_name
	p.bus = bus_name
	p.volume_db = SILENT_DB
	add_child(p)
	return p

func _ensure_bus(bus_name: String) -> void:
	if AudioServer.get_bus_index(bus_name) != -1:
		return
	AudioServer.add_bus()
	var index := AudioServer.bus_count - 1
	AudioServer.set_bus_name(index, bus_name)
	AudioServer.set_bus_send(index, "Master")

func _apply_mutes() -> void:
	var music_bus := AudioServer.get_bus_index("Music")
	var sfx_bus := AudioServer.get_bus_index("SFX")
	if music_bus != -1:
		AudioServer.set_bus_mute(music_bus, not music_enabled)
	if sfx_bus != -1:
		AudioServer.set_bus_mute(sfx_bus, not sfx_enabled)

func set_music_enabled(value: bool) -> void:
	music_enabled = value
	_apply_mutes()

func set_sfx_enabled(value: bool) -> void:
	sfx_enabled = value
	_apply_mutes()

# ---------------------------------------------------------------- sfx
func play_sfx(id: String, pitch: float = 1.0) -> void:
	if not sfx_enabled or not _voices.has(id):
		return
	var pool: Array = _voices[id]
	var cursor := int(_voice_cursor.get(id, 0)) % pool.size()
	_voice_cursor[id] = (cursor + 1) % pool.size()
	var player: AudioStreamPlayer = pool[cursor]
	var jitter := _rng.randf_range(0.97, 1.04) if id in VARIATION else 1.0
	player.pitch_scale = clampf(pitch * jitter, 0.5, 2.0)
	player.volume_db = float(CLIP_GAIN_DB.get(id, -4.0))
	player.play()

# ---------------------------------------------------------------- music
func play_music(id: String, fade_seconds: float = 1.2) -> void:
	if not MUSIC.has(id):
		return
	if id == current_music and _active_music != null and _active_music.playing:
		return
	var stream := load(str(MUSIC[id])) as AudioStream
	if stream == null:
		return
	if stream is AudioStreamOggVorbis:
		(stream as AudioStreamOggVorbis).loop = true
	current_music = id
	var outgoing := _active_music
	var incoming := _music_b if _active_music == _music_a else _music_a
	_kill_tween(incoming)
	incoming.stream = stream
	incoming.volume_db = SILENT_DB
	incoming.play()
	_active_music = incoming
	var fade_in := create_tween()
	_tweens[incoming] = fade_in
	fade_in.tween_property(incoming, "volume_db", MUSIC_DB, fade_seconds)
	if outgoing != null and outgoing.playing:
		_kill_tween(outgoing)
		var fade_out := create_tween()
		_tweens[outgoing] = fade_out
		fade_out.tween_property(outgoing, "volume_db", SILENT_DB, fade_seconds)
		fade_out.tween_callback(outgoing.stop)
	for layer in _layer_players.keys():                  # a new track starts at 0: keep active layers in time with it
		var layer_player: AudioStreamPlayer = _layer_players[layer]
		if layer_player.playing:
			layer_player.seek(0.0)

func stop_music(fade_seconds: float = 0.6) -> void:
	if _active_music == null:
		return
	var player := _active_music
	_kill_tween(player)
	var t := create_tween()
	_tweens[player] = t
	t.tween_property(player, "volume_db", SILENT_DB, fade_seconds)
	t.tween_callback(player.stop)
	current_music = ""

func set_intensity(value: float) -> void:
	gameplay_intensity = clampf(value, 0.0, 1.0)
	_set_layer("chase", gameplay_intensity >= 0.55)
	_set_layer("overdrive", gameplay_intensity >= 0.85)

func _set_layer(layer: String, on: bool) -> void:
	if not _layer_players.has(layer) or on == bool(_layer_state.get(layer, false)):
		return
	_layer_state[layer] = on
	var player: AudioStreamPlayer = _layer_players[layer]
	_kill_tween(player)
	var t := create_tween()
	_tweens[player] = t
	if on:
		if not player.playing:
			var stream := load(str(MUSIC_LAYERS[layer])) as AudioStream
			if stream == null:
				return
			if stream is AudioStreamOggVorbis:
				(stream as AudioStreamOggVorbis).loop = true
			player.stream = stream
			player.volume_db = SILENT_DB
			var start := 0.0
			if _active_music != null and _active_music.playing:
				start = _active_music.get_playback_position()
			player.play(start)
		t.tween_property(player, "volume_db", float(LAYER_DB[layer]), 0.8)
	else:
		t.tween_property(player, "volume_db", SILENT_DB, 0.9)
		t.tween_callback(player.stop)

func _kill_tween(player: AudioStreamPlayer) -> void:
	if _tweens.has(player):
		var old: Tween = _tweens[player]
		if old != null and old.is_valid():
			old.kill()
		_tweens.erase(player)

func _on_paused_changed(value: bool) -> void:
	var bus := AudioServer.get_bus_index("Music")
	if bus != -1:
		AudioServer.set_bus_volume_db(bus, -9.0 if value else 0.0)
