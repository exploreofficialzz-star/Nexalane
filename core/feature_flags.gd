extends RefCounted
class_name FeatureFlags

## 0.6.0 "Subway-style focus": the first screens and the track show only what a runner game needs.  Everything below is
## SWITCHED OFF, not deleted - flip a flag (or add a name to a list) and the feature is back; no other code changes needed.

## Mode chips on the main menu (the other modes - STORY, WEEKLY, EVENT, GHOST, CHALLENGE - stay in the code).
const MENU_MODES: Array = ["ENDLESS", "DAILY", "TRAINING"]

## Buttons of the menu bar.  Hidden for now: "season" (season pass), "achievements" (TROPHIES), "leaderboards" (RANKS).
const MENU_NAV: Array = ["garage", "missions", "shop", "settings"]

## Route forks: every sixth chunk used to make you pick one of three routes at a gate.  Off = one continuous track,
## nothing to read or decide while running at 25 m/s.
const ROUTE_FORKS: bool = false
