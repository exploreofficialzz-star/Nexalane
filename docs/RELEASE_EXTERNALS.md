# Release External Gates — 0.4.0

The full game candidate is implemented and audited locally. The following must be supplied by the publisher/release environment before store submission:

- Godot 4.7.2 editor/export templates and Android/iOS SDKs.
- Android signing keystore and Play Console registration.
- iOS signing, provisioning and App Store Connect registration.
- Production ad provider app/unit IDs.
- Production billing product configuration matching `services/billing/billing_service.gd`.
- Backend project/API credentials and server-side validation endpoint.
- Privacy policy / terms URLs.
- Production crash/analytics provider credentials if desired.
- Physical-device QA and store compliance approval.

No secret, certificate or publisher-owned URL has been fabricated.
