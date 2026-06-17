# Hardware Bring-Up

Use this checklist when the BU03-Kit boards arrive or when starting a new test session.

## Board Labels

Recommended labels:

```text
A01 anchor
A02 anchor
A03 anchor
A04 anchor
T01 tag
T02 spare tag
```

Write the label on the board enclosure and record the serial port used by each board.

## Basic Checks

1. Inspect each board for visible damage.
2. Connect one board to the computer with USB.
3. Confirm the USB serial device appears.
4. Open a serial terminal.
5. Confirm the expected baud rate from vendor documentation or seller guidance.
6. Send a basic AT command and confirm the board replies.
7. Record the firmware version if an AT command exists for it.

Useful local command:

```bash
python3 collector/bu03_collector.py --port /dev/cu.usbserial-0001 --baudrate 115200 --command AT --echo
```

## Role Configuration

The official AT command document should be used as the source of truth. Earlier review found an AT configuration pattern where role `0` is tag and role `1` is anchor, but confirm with the actual AT document before writing automation.

Record every configuration change:

```text
device_label, module_id, role, channel, baudrate, firmware, notes
A01, TBD, anchor, TBD, TBD, TBD, front-left test anchor
```

## Two-Board Distance Test

Start with only two boards:

```text
A01 <---- measured distance ----> T01
```

Measure at:

- 1 meter
- 2 meters
- 3 meters
- 5 meters
- 10 meters if space allows

For each distance, capture:

- Actual tape-measured distance
- Reported distance
- Difference
- Whether there is line of sight
- Whether people or shelves block the signal

Use the collector to preserve both raw serial output and normalized distance rows:

```bash
python3 collector/bu03_collector.py \
  --port /dev/cu.usbserial-0001 \
  --baudrate 115200 \
  --tag-id T01 \
  --anchor-id A01 \
  --actual-distance 2.0 \
  --line-of-sight yes \
  --notes "2m two-board test" \
  --echo
```

## Distance Calibration

Only run `AT+SETDEV` after collecting several known distances. A good first pass is 1 m to 5 m, with 20-30 seconds of samples at each point. Keep the boards away from metal surfaces and keep the antenna side unobstructed.

Collect each point with the real tape-measured distance:

```bash
python3 collector/bu03_collector.py \
  --port /dev/cu.usbserial-2110 \
  --baudrate 115200 \
  --encoding gbk \
  --tag-id T01 \
  --anchor-id A01 \
  --actual-distance 3.0 \
  --line-of-sight yes \
  --notes "A01-T01 calibration 3m" \
  --command "AT+DISTANCE" \
  --repeat-command-interval 1 \
  --echo
```

Calculate calibration parameters from the collected distance CSV files:

```bash
python3 scripts/bu03_calibrate.py data/captures/bu03-distance-*.csv
```

The script prints an `AT+SETDEV=...` command and `AT+SAVE`. Send those commands to the base station, then repeat a few distance checks before continuing to multi-anchor tests.

## Enclosure Notes

3D printed enclosures are acceptable for pilot use.

Rules:

- Use plastic material such as PLA, PETG, or ABS.
- Do not place metal near the antenna area.
- Keep the antenna side facing the store area.
- Expose USB or power input.
- Use fixed anchor mounts so coordinates do not drift after calibration.
