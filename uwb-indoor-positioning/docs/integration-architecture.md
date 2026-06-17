# Integration Architecture

The positioning project should stay independent from the main business system until it proves stable.

## Proposed Flow

```text
BU03-Kit anchors/tags
  -> serial or USB collector
  -> distance parser
  -> positioning engine
  -> realtime positioning service
  -> business system integration
```

## Service Responsibilities

The UWB service owns:

- Physical devices
- Anchor coordinates
- Tag coordinates
- Distance samples
- Calibration data
- Realtime position stream
- Area enter/leave events

The business system owns:

- Store records
- Staff records
- Asset records
- Orders
- Tasks
- Alarms
- Business rules

## Suggested API

```http
GET /health
GET /devices
GET /anchors
GET /tags
GET /positions/latest
GET /positions/history?tagId=T01&from=...&to=...
POST /anchors/calibrate
POST /events/test
```

## Position Payload

```json
{
  "storeId": "store-001",
  "tagId": "T01",
  "x": 3.42,
  "y": 1.86,
  "z": null,
  "confidence": 0.82,
  "source": "uwb-bu03",
  "timestamp": "2026-06-08T10:30:00+08:00"
}
```

## Event Payload

```json
{
  "event": "tag_enter_area",
  "storeId": "store-001",
  "tagId": "T01",
  "areaId": "checkout-zone",
  "position": {
    "x": 3.42,
    "y": 1.86
  },
  "timestamp": "2026-06-08T10:35:20+08:00"
}
```

## Implementation Notes

- Start with serial collection and CSV logging before building a full service.
- Add WebSocket only after the parser and positioning algorithm are stable.
- Keep raw samples. They are essential for debugging calibration and algorithm issues.
- Store anchor coordinates in a simple JSON file at first.
- Move to SQLite or PostgreSQL only when the data model is clear.

