# ANALYTICS + PLAYER BEHAVIOR SCHEMA

## Event naming
`domain_action` with lower_snake_case.

## Common properties
- app_version
- build_channel
- platform
- device_tier
- session_id
- run_id
- district_id
- mode
- content_version
- experiment_id
- days_since_install

## Acquisition
install
first_open
attribution_received
store_page_visit

## Onboarding
onboarding_start
onboarding_step_complete
onboarding_complete
first_run_start
first_run_end
first_reward_claim
first_unlock

## Run events
run_start
run_end
run_pause
run_resume
route_presented
route_selected
chunk_entered
chunk_exited
obstacle_hit
near_miss
perfect_move
collectible_pickup
powerup_pickup
powerup_activated
flow_enter
flow_exit
overdrive_enter
overdrive_exit
death
revive_offer
revive_accept
revive_decline

## Progression
mission_started
mission_progress
mission_complete
mission_claim
character_unlock
character_select
character_mastery_level
cosmetic_unlock
achievement_unlock
district_unlock
chapter_complete

## Economy
currency_earned
currency_spent
shop_open
offer_view
offer_click
bundle_purchase

## Ads
rewarded_offer
rewarded_started
rewarded_completed
rewarded_failed
interstitial_eligible
interstitial_shown
interstitial_closed

## IAP
iap_store_open
iap_product_view
iap_purchase_start
iap_purchase_success
iap_purchase_failure
iap_restore_start
iap_restore_result

## LiveOps
season_enter
season_progress
season_reward_claim
event_enter
event_progress
event_complete
event_reward_claim

## Social
leaderboard_view
leaderboard_rank
leaderboard_score_submit
ghost_created
ghost_view
ghost_challenge_start
ghost_challenge_complete

## Technical
session_crash
scene_load_time
first_frame_time
fps_bucket
frame_hitch
memory_warning
network_error
save_error
purchase_error

## Funnels
### First-session funnel
install -> first_open -> first_run_start -> first_run_end -> first_reward_claim -> first_unlock

### Retention funnel
D0 -> D1 -> D3 -> D7 -> D14 -> D30

### Monetization funnel
shop_open -> offer_view -> offer_click -> purchase_start -> purchase_success

### Rewarded ad funnel
revive_offer -> rewarded_started -> rewarded_completed -> run_resume

## Behavior reports
1. Death heatmap by obstacle ID.
2. Route choice by district and reward band.
3. Session depth by onboarding cohort.
4. Mission completion rates.
5. Flow uptime by runner.
6. Retention by acquisition creative.
7. Ad exposure vs retention.
8. IAP conversion by country and acquisition cohort.
9. LTV by source/campaign once acquisition data exists.
10. Crash/FPS distribution by device.

## Experimentation
Every A/B test gets:
- experiment_id;
- hypothesis;
- variant definitions;
- eligible cohort;
- primary metric;
- guardrail metrics;
- start/end timestamps;
- decision log.

Primary success metric should not be revenue alone. Check retention and session health alongside monetization.
