# PRODUCTION QA + RELEASE

## Build gates
### Gate 1 — compile
No script/resource errors.

### Gate 2 — smoke
App launches, menu loads, run starts, run ends, rewards save.

### Gate 3 — progression
Missions, unlocks, currencies, mastery and save migrations work.

### Gate 4 — services
Analytics, ads, billing, backend and remote config fail gracefully and report errors.

### Gate 5 — performance
Representative device matrix meets FPS/memory/load-time targets.

### Gate 6 — release
Signed AAB builds, store assets and release notes are ready.

## Device matrix
At minimum test:
- low-end Android;
- mainstream Android;
- upper-mid Android;
- recent flagship Android;
- tablet class if supported;
- at least one modern iPhone/iPad class for iOS release validation.

## Gameplay QA
Test all:
- lane changes at speed;
- jump over every obstacle class;
- slide under every low obstacle class;
- branch transitions;
- recovery after obstacle hit;
- shield interactions;
- power-up overlap;
- death during scripted events;
- revive state;
- Flow state;
- pause/resume;
- background/foreground;
- low-memory handling.

## Save QA
Test:
- fresh install;
- reinstall;
- version upgrade;
- interrupted save;
- cloud conflict;
- offline play;
- reconnect;
- purchase restore.

## Monetization QA
- test products;
- failed payment;
- restored payment;
- duplicate purchase prevention;
- rewarded-ad completion;
- ad timeout;
- consent declined;
- no-fill.

## Store QA
Google Play:
- AAB;
- signing;
- package ID;
- version code/name;
- target SDK and policy checks;
- data safety information.

iOS:
- bundle ID;
- signing;
- IAP metadata;
- privacy manifest/required declarations as applicable;
- App Store screenshots and description.

## Release checklist
- [ ] no critical crash
- [ ] no broken purchase path
- [ ] no economy duplication exploit
- [ ] no blocked onboarding
- [ ] analytics validated
- [ ] privacy/consent validated
- [ ] low-end device smoke passed
- [ ] release build signed externally
- [ ] store assets complete
- [ ] customer support URL and email configured
- [ ] privacy policy URL configured
- [ ] terms/refund links configured where needed
