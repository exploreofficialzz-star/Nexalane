# LIVE OPS BIBLE

## Season architecture
Each season has:
- visual theme;
- limited cosmetics;
- 1 hero runner or skin;
- 1 special event mechanic/modifier;
- 20+ seasonal missions;
- weekly challenge ladder;
- event shop;
- season pass;
- leaderboard refresh.

## Annual content framework
Quarter-style themes, adapted to actual release date:
1. City After Dark
2. Stormline
3. Skyline Breakout
4. Winter/holiday equivalent if commercially appropriate

## Recurring weekly loop
Monday: league reset.
Tuesday: daily challenge modifier.
Wednesday: featured route.
Thursday: double reward window.
Friday: ghost duel weekend kickoff.
Saturday/Sunday: high-value event window.

Do not require all events to be manual every week. Build reusable templates.

## Event templates
- Race to Distance
- Flow Frenzy
- Golden Route
- No-Miss Trial
- Ghost Hunt
- District Takeover
- High-Speed Hour
- Collector Sprint

## Event data model
Fields:
- event_id
- version
- start_at
- end_at
- eligible_modes
- modifier_set
- reward_table
- leaderboard_enabled
- purchase_offer_ids
- mission_ids
- artwork_id

## Live-op safety
If remote content fails to load, fall back to locally bundled default events. Never trap players in an empty event screen.

## Content cadence goal
Prefer a repeatable operating system over manually rebuilding systems every update.
