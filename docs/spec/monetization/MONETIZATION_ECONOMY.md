# MONETIZATION + ECONOMY

## Revenue target
Business target: **$50,000 gross revenue by December 31, 2026**.

This document defines the system that gives the project a chance of reaching the target. It does not guarantee revenue.

## Currencies
### Credits
Earned currency. Main sinks:
- cosmetic unlocks;
- mastery upgrades;
- selected utility upgrades;
- event progression.

### Nova
Premium currency. Used for:
- premium cosmetics;
- convenience items;
- season pass-related optional purchases;
- selected revive/utility options where fair.

### Event Tokens
Temporary seasonal currency. Never become a permanent economy sink.

## Ads
### Rewarded
Default placements:
1. optional revive after death;
2. reward multiplier on run summary;
3. optional bonus mission reward;
4. optional chest/claim boost;
5. event boost.

### Interstitial
Only after a run and other natural transitions. Frequency cap by session and remote config.

### Ads removed purchase
Permanent no-interstitial offer; rewarded ads remain voluntary if the product design supports it and platform policy permits.

## IAP catalog
Suggested initial IDs:
- nexalane_starter_299
- nova_small_099
- nova_medium_499
- nova_large_999
- nova_xlarge_1999
- remove_ads_499
- season_pass_999
- event_bundle_299
- premium_cosmetic_499
- elite_bundle_999

Prices must be configured by platform/territory, not assumed globally.

## Starter bundle
Recommended contents:
- 1 premium cosmetic;
- 1,000 Nova-equivalent value;
- 5 revive tickets or equivalent utility;
- small Credit grant.

Avoid overwhelming a new player with dozens of items.

## Economy rules
- Keep earned currency meaningful.
- Do not create paywalls around core play.
- Do not require purchase to continue normal sessions.
- Avoid random paid outcomes.
- Make premium offers legible and optional.
- Price test using cohorts.

## Example retention-safe offer schedule
Day 0: starter offer after first meaningful unlock.
Day 1: returner value offer.
Day 3: character/cosmetic offer.
Day 7: season/event offer.
Later: personalized offers based on behavior clusters.

Do not show purchase prompts before the player understands the game.

## Upgrade economy
Use a bounded soft progression so players can make visible progress without extreme inflation.

Suggested runner mastery costs:
Level 1 -> 2: 500 Credits
2 -> 3: 800
3 -> 4: 1,200
4 -> 5: 1,700
5 -> 6: 2,300
Continue through level 20 using a controlled curve.

The exact values are tunable via remote config.

## Monetization guardrails
Primary guardrails:
- D1 retention;
- D7 retention;
- session length;
- rewarded completion rate;
- refund/failure rate;
- purchase conversion;
- ARPDAU.

Do not accept a monetization experiment purely because it increases immediate revenue if it materially damages retention or session quality.
