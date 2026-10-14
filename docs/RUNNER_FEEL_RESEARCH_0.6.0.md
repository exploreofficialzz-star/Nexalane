# Making it feel like the classic 3-lane runners - research notes (0.6.0)

What I looked at and what I took from it. Statements about Subway Surfers describe what is publicly visible / discussed by developers; I did not have
its source, so the numbers in our camera are **design choices tuned for this game**, not copies.

## What the genre does (and where we follow it)
| Observation | Source type | What we did |
|---|---|---|
| The track is straight and modular; the "curve" you see is a **vertex-bend shader** that drops the world away toward the horizon (also hides pop-in) | Unity developer forums / asset docs on "curved world" shaders | Not implemented yet (see release notes); fog + tall facades hide the horizon for now |
| Three fixed lanes, snappy lane change, camera **behind and above**, runner low in the frame, big readable character | Gameplay analyses, video | Camera 7.2 m back / 3.35 m up / 13 deg down: runner fills about a quarter of a portrait screen, horizon about 30 % from the top |
| The picture is calm: the character moves on screen, the horizon does not wobble | Gameplay | Fixed yaw and pitch, damped sideways follow, no shake |
| Cartoon proportions, bright colours, strong silhouette, a few big animations | Character art | Big-headed runner, bright hoodie on a dark-outlined body, exaggerated run / jump / slide / crash |
| The world is busy: things pass by, people, signs, trains | Gameplay | `ChunkLife`: bunting, crowd, pigeons, balloons, steam, drones, neon |
| Feedback on every action ("juice"), but not so much that it hides the lanes | Design write-ups on feedback overload | Squash and stretch, soft crash punch, no screen shake; restraint on flicker (accessibility flag) |

## Godot specifics that mattered
* With physics interpolation on, a camera that follows a physics-moved body should be updated every rendered frame from the target's
  `get_global_transform_interpolated()` with `physics_interpolation_mode = OFF` on the camera; nodes that are moved from `_process` need it OFF as well
  (Godot docs, "Advanced physics interpolation"; forum threads on camera / player jitter confirm the symptom).
* A bend shader that reads the camera position must use `MAIN_CAM_INV_VIEW_MATRIX` in shadow passes (Godot 4.3+), otherwise shadows detach - one reason the bend is a separate, testable step.
