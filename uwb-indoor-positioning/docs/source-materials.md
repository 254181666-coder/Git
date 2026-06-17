# Source Materials

This document collects the external materials used to understand BU03-Kit and the planned indoor positioning project.

## Official Ai-Thinker UWB Page

- URL: https://docs.ai-thinker.com/uwb_1/
- Build time shown on page: 2026-06-08 10:42:13

Important points from the page:

- BU01 is based on Decawave DW1000 and supports TWR positioning.
- BU03 is based on Decawave DW3000 and supports TDOA/PDOA positioning systems.
- BU04 is also based on DW3000 and integrates STM32F103 MCU with dual antenna support.
- BU03-Kit has links for specifications, datasheet, schematic, firmware, AT commands, TWR upper-computer tool, PDOA upper-computer tool, FAQ, test guide, calibration template, online secondary development guide, and SDK.

## BU03-Kit Official Resources

From the official page:

- BU03-Kit Chinese specification
- BU03-Kit English datasheet
- BU03-Kit schematic
- BU03 AT normal firmware, firmware number 2717, version V1.0.0
- BU03/BU04 AT command document
- TWR upper-computer tool
- PDOA upper-computer tool
- BU03/BU04 FAQ
- BU03/BU04 test guide
- Accuracy correction coefficient template
- Secondary development SDK

## Working Assumptions

- The purchased boards are BU03-Kit development boards, not bare BU03 modules.
- BU03-Kit uses the DW3000 generation, which is preferred over BU01/DW1000 for this project.
- BU03-Kit should be usable over USB serial because the kit schematic includes a USB-to-serial circuit.
- The first useful data target is distance data. Coordinate output may need to be calculated by our own software.
- For store positioning, at least 3 anchors are required for 2D positioning, and 4 anchors are recommended.

## Local Files To Add Later

When the seller provides downloadable files, copy or reference them here:

```text
firmware/vendor/
docs/vendor/
tools/vendor/
```

Do not commit large binary tools unless this project later becomes a shared repository with an agreed storage strategy.

