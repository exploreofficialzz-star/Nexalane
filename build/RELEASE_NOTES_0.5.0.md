# NEXALANE 0.5.0 - a runner that moves like a person

* New runner: a skinned, anatomically proportioned human (hooded jacket, pack, gloves, knee pads) on a 25-bone humanoid
  skeleton - one mesh, 5 draw calls instead of 23.
* New gait: real running kinematics (stance and flight phases, planted feet, spring-mass bounce, pelvis and shoulder counter-rotation,
  head stabilisation, arm drive), cadence capped at a human 5 steps/s (was up to 11.6).
* New states: "get set" countdown stance and explosive start, take-off / leap / landing preparation and absorption, reclined slide,
  lane-change lean and turn, crash recoil and winded crouch, speed-swept hair, bouncing pack and hood.
* Footsteps on wet asphalt with puddle splashes, camera dip on landings, ghosts animated like the player.
* Fixed: runner hovering when the run ended mid-air; stiff limb stepping on 90 / 120 Hz screens.
* Tools: `check_gait_port.py` (GDScript == Python reference) joins the release gate; pose sheet renderer.
* Unchanged: physics, tuning, scoring, saves, track, content version.
See `docs/AUDIT_REPORT_0.5.0.md`.
