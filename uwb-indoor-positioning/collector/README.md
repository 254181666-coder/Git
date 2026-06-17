# Collector

This directory will contain the serial or USB data collector.

First target:

1. Open the BU03-Kit serial port.
2. Send or observe AT/TWR output.
3. Parse distance lines.
4. Write raw and normalized samples to CSV.

Do not build a full API service until basic serial collection is stable.

## Setup

```bash
python3 -m pip install -r collector/requirements.txt
```

On macOS, list likely USB serial devices:

```bash
ls /dev/tty.* /dev/cu.*
```

Prefer `/dev/cu.*` for opening the device from a program.

## Basic AT Check

```bash
python3 collector/bu03_collector.py \
  --port /dev/cu.usbserial-0001 \
  --baudrate 115200 \
  --command AT \
  --echo
```

If the board uses a different baud rate, rerun with the value from the vendor AT document or seller guidance.

## Distance Capture

Two-board distance test example:

```bash
python3 collector/bu03_collector.py \
  --port /dev/cu.usbserial-0001 \
  --baudrate 115200 \
  --tag-id T01 \
  --anchor-id A01 \
  --actual-distance 2.0 \
  --line-of-sight yes \
  --notes "two-board tape test" \
  --echo
```

By default, captures are written under `data/captures/`:

- `bu03-raw-*.csv`: every decoded serial line
- `bu03-distance-*.csv`: normalized rows when a distance value is recognized

The parser currently recognizes common text forms such as `DIST:1.23m`, `range=245 cm`, and `rng:1876mm`. Unknown lines are still preserved in the raw CSV so the parser can be adjusted after seeing real BU03-Kit output.

For BU03 firmware that returns distance only when asked, repeat `AT+DISTANCE` once per second:

```bash
python3 collector/bu03_collector.py \
  --port /dev/cu.usbserial-2110 \
  --baudrate 115200 \
  --encoding gbk \
  --tag-id T01 \
  --anchor-id A01 \
  --actual-distance 1.0 \
  --line-of-sight yes \
  --notes "A01-T01 1m repeated AT+DISTANCE test" \
  --command "AT+DISTANCE" \
  --repeat-command-interval 1 \
  --echo
```
