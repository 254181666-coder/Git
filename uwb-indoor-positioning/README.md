# UWB Indoor Positioning Project

This project is the starter workspace for a BU03-Kit based indoor positioning proof of concept.

## Project Entry

This directory is now the single entry point for all UWB related work on this Mac:

```text
/Users/ann/Documents/Codex/uwb-indoor-positioning
```

Earlier UWB drafts from Desktop projects have been consolidated into `legacy/` for reference only. New work should happen in the main project structure below, not in the old Desktop folders.

Legacy sources:

- `legacy/desktop-bu01-prototype/`: early BU01/MySQL/Web prototype from Desktop.
- `legacy/fourphase-monitoring-prototype/`: early Four-Faith/FourPhase MQTT monitoring prototype from Desktop.
- `docs/business-room-service-architecture.md`: service workflow architecture note copied from the business data project.

The current hardware target is Ai-Thinker BU03-Kit. The first goal is to verify whether the boards can support store-level indoor positioning, then connect the positioning result to the business system through an independent service.

## Current Decision

- Use BU03-Kit for the first proof of concept.
- Treat BU03-Kit as a development board, not the final product board.
- Use 3D printed enclosures for pilot anchors and tags.
- Keep the positioning service independent from the existing business system.
- Integrate with the business system through API, WebSocket, or events after positioning is stable.

## First Milestone

Build a small closed loop:

```text
BU03-Kit distance data
  -> local collector
  -> positioning calculation
  -> latest tag coordinates
  -> simple web map
```

## Suggested Project Structure

```text
docs/                 Project notes, source links, test plans
firmware/             Firmware notes and vendor files index
collector/            Serial/USB data collector
positioning/          Trilateration and filtering logic
server/               API and realtime positioning service
web/                  Store map and live tag view
data/                 Anchor coordinates and sample captures
scripts/              Calibration and maintenance tools
```

## Immediate Next Steps

1. Count the BU03-Kit boards and label them, for example `A01`, `A02`, `A03`, `A04`, `T01`.
2. Confirm each board can connect over USB serial.
3. Confirm AT commands work.
4. Configure at least one anchor and one tag.
5. Run two-board TWR distance testing.
6. Capture distance data into CSV.
7. Place 3 or 4 anchors in a known rectangle and calculate `x, y`.

## Key Documents

- [Official source index](docs/source-materials.md)
- [Hardware bring-up](docs/hardware-bringup.md)
- [Store test plan](docs/store-test-plan.md)
- [Integration architecture](docs/integration-architecture.md)
- [Business room service architecture](docs/business-room-service-architecture.md)
- [Open questions](docs/open-questions.md)
