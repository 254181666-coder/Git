# Store Test Plan

This plan verifies whether BU03-Kit can support the target store positioning scenario.

## Test Goals

- Confirm basic ranging stability.
- Confirm whether 3 or 4 anchors can calculate a usable 2D tag position.
- Measure accuracy in the actual store environment.
- Understand how shelves, people, counters, glass, and corners affect positioning.
- Produce enough data to decide whether to continue toward pilot deployment.

## Recommended Layout

Use meters as the coordinate unit.

```text
A01 (0,0) ---------------- A02 (W,0)

             T01

A03 (0,H) ---------------- A04 (W,H)
```

If only 3 anchors are available, start with `A01`, `A02`, and `A03`, but expect more unstable results.

## Data To Capture

Create one CSV per test session under `data/samples/`.

Suggested columns:

```csv
timestamp,tag_id,anchor_id,actual_x,actual_y,actual_distance,reported_distance,line_of_sight,notes
```

For coordinate tests:

```csv
timestamp,tag_id,actual_x,actual_y,estimated_x,estimated_y,error_m,confidence,notes
```

## Test Cases

1. Static point test

   Put `T01` at 5-10 known points on the store floor. Record actual and estimated coordinates.

2. Walking path test

   Move `T01` slowly along a known path. Check whether the path shape is recognizable.

3. Obstruction test

   Repeat selected points with a person standing between tag and anchor, near shelves, and near counters.

4. Height test

   Compare anchors mounted at different heights. Store deployments usually work better when anchors are placed high and kept fixed.

5. Power stability test

   Leave anchors running for at least 2 hours and watch for disconnects, drift, or abnormal output.

## Pass Criteria For PoC

The PoC is useful if:

- Boards can be configured repeatedly without vendor intervention.
- Distance data can be collected by our own script or service.
- Positioning error is acceptable for the business scenario.
- Anchor placement can be kept stable in the store.
- The data can be converted into business events such as enter area, leave area, dwell time, or asset location.

