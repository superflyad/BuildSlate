# Phone-function evidence proof

The [phone gate](../../buildslate/hardware_readiness.py) cannot accept a reviewed file as proof of a working phone merely because its SHA-256 matches. Its `phone_validation` record must point to a controlled JSON bundle under `validation/phone/test-results/`. The [technical proof](../../buildslate/phone_proof.py) requires the following exact test set, in order, with a separate hash-bound raw CSV for each case:

| Case | Minimum raw evidence checked |
| --- | --- |
| `network_registration` | Final SIM-ready and network-registered state |
| `outgoing_call` | Latched dial request followed by peer answer, then at least 30 seconds of uninterrupted connected telemetry; both audio sample counters advance at every connected sample; no drop |
| `incoming_call` | Latched ring indication followed by local answer, then the same connected duration, two-way audio, and drop checks |
| `packet_data` | Both transmitted and received cellular byte counters advance |
| `radio_kill` | Final radio-disabled state has no network registration |
| `emergency_lab_simulator` | Final emergency route result passes in an authorized lab simulator |

Each distinct CSV needs `elapsed_s` starting at zero and increasing strictly, plus `campaign_id`, `unit_id`, `build_id`, and `configuration_sha256` on every row matching the bundle. The bundle carries those identities, selected cellular MPN and modem firmware version, carrier identity, approved emergency-lab reference, and regulatory review reference. It binds to exact SHA-256 values of the approved selected BOM, cellular design, and telephony software records. The phone gate additionally requires that the same unit/build/configuration passed the functional EVT0 campaign and that the cellular MPN matches the selected BOM. Cellular and telephony design artifacts belong under `engineering/hardware/released/`; raw phone results belong under `validation/phone/test-results/`.

For outgoing calls, the CSV must include binary, latched `dial_request_seen` and `peer_answer_seen` fields. Incoming calls use `ring_seen` and `local_answer_seen`. The first row starts with both fields and `connected` at zero. The two setup events must occur in order before connection. Every row from the first connected sample through the last must remain connected, span at least 30 seconds, and have no sample gap over two seconds. `uplink_audio_samples` and `downlink_audio_samples` must each increase at every connected interval. These are counter and state checks on a submitted log; the operator must still review actual audio capture, signaling, timing, and network instrumentation.

Example bundle shape, with values replaced by actual controlled evidence:

```json
{
  "schema_version": 1,
  "device": "slate-pocket-v1r",
  "campaign_id": "CAMPAIGN-ID",
  "unit_id": "SERIAL-ID",
  "build_id": "BUILD-ID",
  "configuration_sha256": "64 lowercase hex characters",
  "cellular_mpn": "EXACT-ORDERABLE-MPN",
  "modem_firmware_version": "VERSION",
  "carrier": "APPROVED-TEST-NETWORK",
  "selected_bom_sha256": "64 lowercase hex characters",
  "cellular_design_sha256": "64 lowercase hex characters",
  "telephony_software_sha256": "64 lowercase hex characters",
  "emergency_method": "authorized_lab_simulator",
  "emergency_lab_approval": "CONTROLLED-APPROVAL-ID",
  "regulatory_review_reference": "CONTROLLED-REVIEW-ID",
  "tests": [
    {
      "id": "network_registration",
      "raw_path": "validation/phone/test-results/network_registration.csv",
      "raw_sha256": "64 lowercase hex characters",
      "disposition": "pass"
    }
  ]
}
```

The example shows one test entry for brevity; the gate requires all six. The [validation fixture](../../validation/validate_phone_proof.py) proves that tampered raw bytes, missing received audio, interrupted or sparsely sampled connections, missing dial/answer events, a log from another unit, mismatched upstream design hashes, and design records placed in the test directory are rejected. It is synthetic and does not demonstrate a physical Slate unit.

This is an evidence-consistency screen and a **ready for engineering review** gate. Hashes and CSV counters cannot authenticate a physical unit, prove RF performance or emergency service, or grant regulatory approval. Independent review of the test setup, raw instruments, carrier configuration, lab scope, and final product filings remains required. No current phone test bundle exists, so the public [Hardware view](https://superflyad.github.io/BuildSlate/?tab=hardware) stays blocked.
