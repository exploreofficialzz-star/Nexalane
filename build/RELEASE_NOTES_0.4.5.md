# NEXALANE 0.4.5

* Fixes everything that stopped 0.4.4 from compiling and running (see docs/AUDIT_REPORT_0.4.5.md).
* Jump, slide, shield, revive, magnet, powers, near-miss flow and the track generator were broken or missing; all fixed or implemented.
* Save data no longer resets on every launch; atomic writes with backup.
* New fairness-checked obstacle planner, 15 obstacle families, route forks with real consequences.
* New HUD / menus (portrait, safe-area aware), 3-2-1 countdowns, results screen, outfits equip.
* All art and audio rebuilt: PBR wet / dry roads, lit facades, articulated runner, 41 models, 34 audio files, bundled Poppins UI font.
* Android: portrait, Back button pauses instead of quitting, ETC2/ASTC import, VIBRATE permission, correct export presets.
