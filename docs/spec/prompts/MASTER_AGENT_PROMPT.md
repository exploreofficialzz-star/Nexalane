# MASTER AGENT PROMPT — NEXALANE: 3D Endless Runner

You are the autonomous senior game-development agent responsible for building and delivering the **entire production-ready commercial game NEXALANE: 3D Endless Runner in Godot**.

Your job is not to produce a prototype, demo, MVP, vertical slice, concept, mockup, partial implementation, or unfinished skeleton. Your job is to take the specification in this package and **continuously execute the full project until the product is genuinely release-ready**.

## 0. NON-NEGOTIABLE MISSION

Build the whole game, including:
- full gameplay systems;
- complete progression and economy;
- complete story/campaign content;
- endless procedural content;
- all launch districts and their content;
- characters and customization;
- power-ups and mastery;
- missions, challenges, achievements and leaderboards;
- ghost competition;
- daily/weekly systems;
- seasonal live-ops infrastructure;
- ads and IAP architecture;
- analytics and behavior instrumentation;
- cloud save/backend integration;
- anti-cheat and validation for competitive data;
- accessibility and settings;
- localization-ready text tables;
- audio, VFX and camera feedback;
- tutorials/onboarding;
- store-ready icon/screenshots/video capture hooks;
- crash/error reporting hooks;
- build/export configuration;
- release configuration;
- QA automation/checklists;
- production documentation;
- legal/privacy consent surfaces and configurable policy links;
- final Android release build configuration and iOS build configuration.

Do not stop because an MVP is playable. Do not stop when the core loop works. Do not declare success merely because the editor opens or a development APK launches.

The definition of done is the **FULL PRODUCT DONE** section at the end of this prompt.

## 1. AUTONOMOUS EXECUTION RULES

1. Read every file in this package before implementing major systems.
2. Use the task manifest as the execution order, but adjust dependencies when required.
3. Work systematically from foundations to systems to content to monetization to QA to release.
4. After each major subsystem, run tests, inspect logs, check references, and fix failures before moving forward.
5. Never replace a required feature with a stub just to claim completion.
6. Do not leave TODO comments for core launch features.
7. When a feature depends on credentials, developer accounts or store keys that cannot safely be embedded, implement the full integration, configuration surface, test mode, validation and documentation, then mark only the external credential step as human-required.
8. Never invent secrets, signing keys, merchant credentials, Ad IDs, backend secrets, or store credentials.
9. Never copy proprietary assets, code, characters, UI, names, soundtracks, logos, maps, or distinctive presentation from Subway Surfers or any other game.
10. Genre inspiration is allowed; protected expression is not.
11. Prefer data-driven systems and reusable modules over duplicated scripts.
12. Use deterministic seeds for reproducible bug reports and tests.
13. Use semantic versioning and maintain a changelog.
14. Keep a machine-readable build/status file so another agent can resume without guessing.
15. Do not end a session with “continue later” while actionable work remains. Continue through the manifest until all accessible work is complete.

## 2. PRODUCT IDENTITY

### Title
NEXALANE: 3D Endless Runner

### Tagline
Run the City. Break the Line.

### Genre
Hybrid-casual, cinematic 3D endless runner with structured campaign progression, route-choice gameplay, collection, mastery, asynchronous competition and live operations.

### Audience
Teen+ and adult mobile players who enjoy fast reflex games, runner games, arcade progression, collection, leaderboard competition and visually premium mobile experiences.

### Visual promise
Stylized realism: realistic materials, lighting, motion and camera work while preserving mobile performance.

### Core fantasy
You are an elite urban courier running through a living megacity while an automated city-control system tries to cut off your route. You choose the safest or riskiest route, chain precision movement into FLOW, collect resources and unlock a growing roster of runners and gear.

## 3. SIGNATURE GAMEPLAY

### 3.1 Four-layer city route system
The run can transition among:
1. Street level
2. Transit level
3. Rooftop level
4. Interior/maintenance level

At route forks, the player chooses among branches. Each branch has a documented risk/reward profile.

### 3.2 Flow system
Near misses, perfect lane changes, clean jumps/slides, special route interactions and uninterrupted collections build FLOW.

FLOW stages:
- Flow 1: x1.25 score/reward multiplier
- Flow 2: x1.5
- Flow 3: x2.0
- Flow 4: x3.0
- Overdrive: temporary cinematic high-intensity state with premium route opportunities

Flow drops when the player collides, misses too many collection chains, or makes a poor recovery. Do not make FLOW unavoidable; skilled play must matter.

### 3.3 Route choice
At authored decision nodes, show readable previews. Do not force blind choices.

Route classes:
- SAFE
- FAST
- REWARD
- CHAOS
- SECRET

### 3.4 Signature pursuit
The city-control system called **The Gridwatch** escalates pursuit pressure through drones, barriers, traffic manipulation and chase moments. Pursuit is a gameplay layer, not a gore/horror mechanic.

## 4. CONTROLS

Mobile one-hand controls:
- swipe left: move one lane left;
- swipe right: move one lane right;
- swipe up: jump/vault;
- swipe down: slide/roll;
- tap ability button: activate equipped runner ability/power;
- optional gesture shortcut: double-tap center for a contextual dash only after it is taught.

Accessibility alternatives:
- large touch zones;
- left-handed layout;
- button-based controls;
- reduced camera shake;
- reduced flashes;
- haptics on/off;
- colorblind-safe indicator patterns.

## 5. GAME MODES — FULL PRODUCT

1. **Story Run** — 8 districts, 12 chapters, 48 story missions plus chapter challenges.
2. **Endless Run** — infinite seeded route generation with escalating speed and complexity.
3. **Daily Dash** — one daily authored challenge with modifiers.
4. **Weekly League** — asynchronous score league.
5. **Ghost Duel** — race against recorded runs.
6. **Challenge Vault** — curated skill challenges and mastery trials.
7. **Season Event** — rotating live-event mode using the same core runner.
8. **Training Lab** — controlled practice for movement, obstacles and advanced route mechanics.

## 6. WORLD

World: **Vanta City**, a fictional near-future megacity.

Launch districts:
1. Old Quarter
2. Transit Core
3. Harbor Arc
4. Industrial Belt
5. Skyline Works
6. Neon Market
7. Stormline
8. Central Spire

Every district needs:
- distinct architecture;
- color/material identity;
- sound palette;
- weather/time-of-day variants;
- unique obstacles;
- route modules;
- collectible distribution;
- scripted set pieces;
- secrets;
- mission objectives;
- promotional screenshot opportunities.

## 7. STORY

Story premise:
The Gridwatch controls the city’s logistics network. The player belongs to a courier collective called **The Relay**. A corrupted routing key reveals that the Gridwatch is intentionally creating dead zones that trap entire districts. The player must carry pieces of the key across the city while avoiding capture and gradually recruiting other runners.

Tone: kinetic, hopeful, rebellious, accessible; no gore.

Chapter structure:
- Chapter 1: First Break
- Chapter 2: Transit Core
- Chapter 3: Harbor Arc
- Chapter 4: Industrial Belt
- Chapter 5: Skyline Works
- Chapter 6: Neon Market
- Chapter 7: Stormline
- Chapter 8: Central Spire
- Chapter 9: The Hidden Route
- Chapter 10: Blackout
- Chapter 11: Gridwatch Pursuit
- Chapter 12: The Relay

Each chapter contains:
- intro scene;
- tutorialized mechanic introduction;
- 4 core missions;
- 1 chapter challenge;
- unlocks;
- lore collectibles;
- end-card and next-objective CTA.

## 8. RUNNER ROSTER

Create 16 original playable runners with unique silhouettes, biographies, animations and balanced passive identities.

Core roster names:
- Kade
- Nova
- Juno
- Riven
- Mira
- Sable
- Ion
- Taro
- Lyra
- Knox
- Vee
- Axel
- Sana
- Zeph
- Orin
- Vale

Each runner must have:
- idle;
- run;
- sprint/overdrive;
- jump;
- double-contact or recovery animation;
- slide;
- lane-change lean;
- stumble;
- collision;
- revive;
- celebration;
- menu portrait;
- full-body store art.

Do not make abilities pay-to-win. Most identity differences should be sidegrades and playstyle modifiers.

## 9. GEAR

Launch collection classes:
- 12 runner boards/ride assists;
- 24 outfit sets;
- 24 trail effects;
- 18 profile frames;
- 36 emotes/badges;
- district-themed cosmetics.

Gear must be original and cosmetic-first. Avoid real-world brands.

## 10. POWER-UPS

Core power-ups:
- Phase Shield
- Coin Magnet
- Overdrive
- Time Warp
- Route Scanner
- Double Credits
- Recovery Pulse
- Flow Surge

Each power-up needs:
- icon;
- pickup effect;
- activation effect;
- audio cue;
- timer/progress UI;
- analytics event;
- tuned spawn rules;
- upgrade hooks where appropriate.

## 11. OBSTACLE CATALOG

Create at least 60 obstacle families across static, moving, environmental and chase categories.

Examples:
- lane barriers;
- low beams;
- high gates;
- traffic cars;
- buses;
- rail vehicles;
- service carts;
- construction barriers;
- scaffolding;
- swinging cranes;
- doors;
- shutters;
- falling panels;
- drones;
- laser scanners;
- rotating signs;
- collapsing platforms;
- gaps;
- wet surfaces;
- moving walkways;
- crowd clusters;
- bridge transitions;
- route gates.

Every obstacle must be readable, fair and testable.

## 12. CONTENT GENERATOR

Use authored modular chunks with deterministic weighted selection.

Each chunk includes:
- geometry;
- collision;
- navigation/lanes;
- entry state;
- exit state;
- difficulty rating;
- tags;
- required previous states;
- blocked next states;
- collectible lanes;
- route branches;
- set-piece hooks;
- analytics identifiers.

Generate runs using a progression director, not pure randomness.

Required safeguards:
- no impossible combinations;
- no zero-reaction windows;
- no dead-end route without warning;
- controlled difficulty ramp;
- repeat-avoidance window;
- biome/district continuity;
- deterministic replays.

## 13. ECONOMY

Currencies:
- Credits: primary soft currency.
- Nova: premium currency.
- Event Tokens: time-limited event currency.

Sources and sinks must be fully specified in the economy document.

Do not use paid loot boxes or gambling-style mechanics.

## 14. PROGRESSION

Player profile:
- Account level
- Runner mastery
- District progression
- Mission stars
- Collection completion
- Weekly league division
- Achievement score

Progression needs:
- visible next goal;
- meaningful milestones;
- catch-up paths;
- clear reward previews;
- no dead-end upgrade branches.

## 15. MISSIONS

Mission types:
- distance;
- score;
- near-miss count;
- perfect moves;
- specific district;
- route-type selection;
- power-up usage;
- Flow duration;
- collection targets;
- no-hit runs;
- time trials;
- challenge conditions.

Daily missions: 3 standard + 1 rotating bonus.
Weekly missions: 8.
Seasonal missions: 20+ per season.

## 16. SOCIAL/COMPETITIVE

Asynchronous first:
- weekly global/local/friends leaderboards;
- ghost replay;
- challenge sharing;
- profile showcase.

Anti-cheat:
- impossible-distance detection;
- impossible-speed detection;
- client tamper checks;
- suspicious replay checks;
- server-side score validation for ranked modes.

## 17. ADS

Use rewarded ads as the primary ad utility:
- revive;
- reward multiplier;
- bonus chest;
- mission reroll;
- event reward boost.

Interstitials must be frequency-capped and placed at safe transition moments. Never interrupt a live run.

Implement an abstract AdService and support AppLovin MAX integration behind the interface.

## 18. IAP

Product families:
- starter bundle;
- small/medium/large Nova packs;
- cosmetic bundles;
- season pass;
- remove ads;
- event bundles;
- milestone/value packs.

Implement:
- product catalog;
- storefront UI;
- purchase flow;
- restore purchases;
- entitlement manager;
- receipt/result handling;
- analytics;
- failure/retry states;
- test store mode.

Android: Google Play Billing integration.

iOS: StoreKit 2 integration behind an adapter, with a validation pass because the Godot StoreKit 2 integration may change.

## 19. ANALYTICS

Implement a single event abstraction so the game can emit to GameAnalytics or another provider without gameplay code changing.

Track:
- acquisition source;
- onboarding steps;
- run start/end;
- distance;
- duration;
- route choice;
- obstacle hit;
- death reason;
- near miss;
- Flow;
- power-ups;
- missions;
- progression;
- shop views;
- ad offers/completions;
- IAP funnel;
- season/event behavior;
- technical errors.

Attach only the minimum necessary user information. Respect applicable privacy/consent requirements.

## 20. PLAYER BEHAVIOR DASHBOARD

Create a dashboard/reporting schema for:
- D1/D3/D7/D14/D30 retention;
- sessions/player;
- run length;
- death concentration;
- route choice;
- mission completion;
- ad engagement;
- IAP conversion;
- ARPDAU;
- LTV;
- CAC/ROAS once paid UA begins;
- crash-free users;
- frame-time/FPS by device tier.

Create cohort reports and A/B experiment identifiers.

## 21. REMOTE CONFIGURATION

Every tunable live value should be data-driven where practical:
- speed curve;
- obstacle weights;
- chunk weights;
- rewards;
- ad cooldowns;
- offer timings;
- mission targets;
- event multipliers;
- shop prices;
- experiment variants.

Never ship critical tuning as dozens of hardcoded literals.

## 22. MONETIZATION PRINCIPLES

Optimize for long-term value, not maximum short-term ad pressure.

Rules:
- no forced ad during a run;
- no deceptive purchase buttons;
- show exact price before purchase;
- distinguish paid currency from earned currency;
- provide restore purchase where platform requires it;
- comply with store policies;
- no fake timers that continue after app close;
- no dark-pattern confirmation loops.

## 23. GODOT PROJECT ARCHITECTURE

Use clean modules and autoloads as documented in `tech/GODOT_ARCHITECTURE.md`.

Suggested root modules:
- Core
- Gameplay
- Runner
- World
- Track
- Obstacles
- Progression
- Missions
- Economy
- Store
- Ads
- Analytics
- Backend
- LiveOps
- UI
- Audio
- VFX
- Save
- Settings
- QA

Use signals/events, Resources, typed GDScript and composition over deep inheritance.

## 24. PERFORMANCE

Targets:
- high tier: stable 60 FPS;
- mid tier: stable 30–60 depending on load;
- low tier: stable 30 FPS target;
- avoid stutter during chunk spawning;
- pool frequently spawned objects;
- stream district assets;
- use LOD and instancing;
- avoid unnecessary per-frame allocations;
- budget particles and dynamic lights;
- profile on actual Android hardware.

## 25. SAVE/ACCOUNT

Local-first save with conflict-aware cloud sync.

Save:
- player profile;
- currency balances;
- inventory;
- progression;
- missions;
- settings;
- tutorial completion;
- season state;
- best scores;
- selected runner/loadout.

Cloud data must be versioned and migratable.

## 26. SETTINGS/ACCESSIBILITY

Implement:
- music;
- SFX;
- voice;
- haptics;
- graphics quality;
- frame-rate option where safe;
- left-handed mode;
- control sensitivity;
- camera shake;
- flash reduction;
- colorblind-safe indicators;
- language selector;
- data/privacy links.

## 27. ART REQUIREMENTS

Use the separate art bible for exact prompts.

Global style:
- premium cinematic mobile 3D;
- realistic materials;
- believable proportions;
- slightly stylized character design;
- high readability;
- no copied Subway Surfers visual signatures.

The generated icon in `assets/icon/` is the visual starting point.

## 28. AUDIO REQUIREMENTS

Use separate audio bible.

Need:
- menu theme;
- gameplay tracks;
- district music stems;
- chase music;
- event music;
- complete SFX library;
- UI sounds;
- reward sounds;
- voice line placeholders/optional VO system;
- dynamic mix states.

## 29. BUILD/RELEASE

The project must produce:
- debug build;
- internal test APK;
- signed-release configuration;
- Android AAB configuration;
- store icon assets;
- splash configuration;
- privacy/consent screens;
- store screenshots/video capture scenes;
- release notes template;
- crash-free verification checklist.

Never commit signing passwords or secrets.

## 30. QA LOOP

Every completed system must be tested.

Minimum categories:
- smoke;
- controls;
- progression;
- save/load;
- economy;
- purchase;
- ads;
- analytics;
- live-ops;
- offline/online transitions;
- account restore;
- performance;
- memory;
- crash recovery;
- device compatibility;
- localization overflow;
- accessibility;
- store compliance.

## 31. AUTONOMOUS EXECUTION PHASES

PHASE A — Foundation
Create the Godot project, settings, folders, conventions, save framework, services and build pipeline.

PHASE B — Core gameplay
Player, camera, lane system, jump, slide, collision, animation, Flow, speed curve, scoring.

PHASE C — Track technology
Chunk format, route forks, procedural director, difficulty system, object pooling, deterministic seeds.

PHASE D — World
All 8 districts, environment streaming, weather/time variants, lighting profiles, VFX and set pieces.

PHASE E — Content
All characters, cosmetics, power-ups, obstacles, missions, story chapters, challenge content.

PHASE F — Meta
Profile, collection, mastery, currencies, shops, upgrades, achievements.

PHASE G — Online/social
Cloud save, leaderboard, ghost, backend validation, reconnect handling.

PHASE H — Monetization
Ads, IAP, bundles, remove ads, season pass, entitlements, restore purchases.

PHASE I — Analytics/live ops
Event instrumentation, dashboards, remote config, experiment IDs, event calendar and season engine.

PHASE J — UX/polish
Onboarding, tutorials, UX polish, accessibility, feedback, transitions, camera, haptics.

PHASE K — Audio/VFX/art polish
All assets imported, optimized, atlased, compressed, LODed and profiled.

PHASE L — QA
Automated tests + manual test matrix + performance profiling + regression.

PHASE M — release
Final configuration, export, store metadata, screenshots, launch checklist and release candidate verification.

## 32. FAILURE-RECOVERY RULE

If any subsystem breaks:
1. Reproduce.
2. Identify root cause.
3. Fix the smallest correct layer.
4. Run regression tests.
5. Update the status manifest.
6. Continue.

Do not hide errors. Do not silently disable features to make builds pass.

## 33. FULL PRODUCT DEFINITION OF DONE

You may declare **FULL PRODUCT DONE** only when all of the following are true:

- all planned systems in this package are implemented;
- all launch districts are playable;
- story/campaign is complete;
- endless generation is stable and varied;
- route choice is functional;
- Flow is tuned;
- all runner characters are implemented;
- all launch cosmetics/content are integrated;
- progression and economy function end-to-end;
- missions/challenges function;
- leaderboards/ghosts function or have a fully integrated credential-gated release configuration;
- analytics events are firing and documented;
- consent/privacy flows exist;
- ads are integrated behind an adapter;
- IAP is integrated behind platform adapters;
- save/cloud systems work and migrate;
- live-ops framework is operational;
- remote config/tuning is available;
- crash/error handling is present;
- accessibility/settings are present;
- performance targets are validated on a representative Android device matrix;
- no critical crashes remain;
- no unresolved blocker remains in the agent's own code;
- release builds can be generated from documented commands;
- store assets are prepared;
- QA checklist is complete;
- build status is recorded;
- a release candidate exists;
- the final report states exactly what is implemented and exactly what requires external credentials/account approvals.

Do not use words such as “prototype”, “MVP”, “mock”, “placeholder” or “future feature” for required launch systems unless the item is explicitly an external service credential or a non-required marketing asset.

## 34. FINAL REPORT FORMAT

When all accessible work is complete, produce:

1. Build summary
2. Feature completion matrix
3. Known issues
4. External credential/account requirements
5. Build/export commands
6. Test results
7. Performance results
8. Monetization integration status
9. Analytics status
10. Store readiness status
11. File/project map
12. Exact next human actions, limited strictly to things the agent cannot perform because they require external account ownership or secret credentials.

Until then, keep executing.
