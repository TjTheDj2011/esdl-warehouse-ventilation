# ESDL Project 1 — Automated Warehouse Ventilation System

**Course:** ESDL (Electrical System Design Lab) — Tennessee State University, ECE
**Team:** TJ (Terrence Parham), Tabitha, Claude (designated ESDL specialist)
**Timeline:** 7-week project. Week 4 as of 2026-09-16 → ~3 weeks remain.

> Hardware / embedded C++ class project. This repository is scoped to ESDL Project 1
> and nothing else. Standards here are hardware-lab standards: nothing is called
> "working" without a bench measurement behind it.

## Project Goal
Design and prototype a closed-loop, automated warehouse ventilation system using an
ESP32 that independently monitors internal and external temperature and dynamically
drives a dual-fan exhaust/intake setup with no human intervention.

## Bill of Materials (design intent)
| Part | Role |
|---|---|
| ESP32-WROOM-32 | Controller (3.3V logic). Chosen over the on-hand ESP32-S3 N16R8 for spares + tutorial coverage; S3 is the backup. |
| 2x DS18B20 (1-wire, 3.3V) | Internal (chamber) + ambient (outside) temperature. On hand, from the professor. |
| 3x SSD1306 OLED 128x64 (I2C, 3.3V) | Live telemetry: one panel each for IN temp, OUT temp, STATE. On hand. |
| Active piezo buzzer | Critical thermal-overload alarm |
| Dual-channel motor driver | Drives both fans |
| 2x 80mm brushless computer fan (5V) | Intake (low, one wall) + exhaust (high, opposite wall). One direction only. |
| Transparent enclosure | Diagonal cross-ventilation wind tunnel |

## Core Objectives
1. **Hardware integration** — all peripherals on one ESP32.
2. **Finite state logic** — C++ FSM, thermal ONLY. Humidity is read and deliberately
   discarded to keep the control loop streamlined and reliable.
3. **Data visualization** — real-time Inside Temp / Outside Temp / System State on
   three dedicated OLED panels, each showing one value as large as the panel
   allows, to prove state changes live during the physical presentation.
4. **Physical prototyping** — transparent box, diagonal wind tunnel: intake bottom-left,
   exhaust top-right. Demonstrate airflow manipulation under a dry heat source.

## State Machine (demonstration triggers)
| State | Entry condition | Intake | Exhaust | Buzzer | LCD |
|---|---|---|---|---|---|
| `STANDBY`      | T_in < 80F                       | OFF | OFF | off | `IDLE`    |
| `CROSS_VENT`   | T_in > 80F AND outside >=2F cooler | ON  | ON  | off | `CROSS`/`VENT` |
| `EXHAUST_ONLY` | T_in > 80F AND outside within 3F | OFF | ON  | ON  | `EXHAUST` |
| `SEALED` (added)| T_in > 80F AND outside >=3F HOTTER | OFF | OFF | ON | `SEALED` |
| `FAULT` (added)| N consecutive bad sensor reads   | OFF | ON  | pattern | `SENSOR FAULT` (scrolls) |

Rationale for EXHAUST_ONLY: inside and outside are within a few degrees, so exchange is
close to thermally neutral and the win is removing internally generated heat. The exhaust
sits high on the opposite wall where buoyant hot air collects, so it skims the hottest
layer; makeup air enters low through the IDLE INTAKE FAN, which serves as the passive
vent. That ingress is harmless by construction -- if outside were meaningfully hotter we
would be in SEALED, not this state. Buzzer signals critical thermal overload.

**Fans decided 2026-09-18: two brushless computer fans, one direction only.** Intake low
on one wall, exhaust high on the opposite wall, diagonal path preserved. No fan ever
reverses. This replaces the earlier reversing-intake scheme and the 130-size brushed
motors: brushless fans move far more air, are quiet and balanced, mount with four screws,
and remove brush noise from the I2C bus entirely -- the failure mode listed below as the
#1 risk in this build. Adding SEALED is what made the reversal unnecessary: the backdraft
the reversal existed to block can only carry hot air when outside is hotter, and that
condition now stops both fans instead.
Full table with rationale: docs/03_control_matrix.md (the firmware is tested against it).

**Governing principle (added):** move air only when the air we pull in is cooler than
the air we push out; otherwise stop moving air. Ventilating while outside is hotter
does not cool the warehouse -- it heats it. `SEALED` exists because two fans cannot
fix that condition, and pretending otherwise would make the system worse.
`SEALED` cannot deadlock: an internal heat source raises T_in until it passes T_out,
which releases the seal and resumes ventilation automatically.

**Physical limit, stated honestly:** there is no refrigeration here, so the system
cannot cool below ambient. The defensible claim is that it drives the chamber toward
the lowest temperature obtainable by air exchange and never takes an action that
makes the chamber hotter.

Display note: three OLED panels replaced the 16x2 LCD on 2026-09-18. Each value
gets a whole 128x64 panel, so text renders larger than the LCD managed. State
labels are spelled out rather than abbreviated: a label containing a space is
split and stacked on two lines (CROSS / VENT, SENSOR / FAULT), so no word has
to be decoded from a contraction. Each half must fit one line at text size 3,
the smallest readable across a room - host check [12] enforces it. FAULT also
scrolls, because motion draws the eye when something is wrong.

## Standing engineering constraints (decided — do not silently regress)
- **Hysteresis is mandatory.** ON at 80.0F / OFF at 77.0F + minimum state dwell (~10s).
  A bare `>` threshold chatters the fans on sensor noise.
- **Differential deadband.** DS18B20 is +/-0.5C each, so T_in - T_out carries
  ~+/-1.8F of uncertainty. Outside must be >=2F cooler before we open the intake.
  (Same figure as the DHT22 it replaced, so no threshold retuning was needed.)
- **A missing reading is the dangerous failure.** DS18B20 reports a disconnected
  probe as -127C; main.cpp maps that and any out-of-range value to NaN, and every
  comparison against NaN is false -> would silently land in STANDBY with the box
  cooking. Explicit FAULT state, loud, fail-safe to exhaust-on. Never a silent
  default.
- **An idle fan is an open vent -- now by design.** With brushless fans the idle intake
  is the deliberate makeup-air path for EXHAUST_ONLY. It is safe because EXHAUST_ONLY
  only runs when outside is within 3F; hotter than that and SEALED stops both fans.
  A one-way flapper over the intake is optional and only reduces passive exchange
  during SEALED.
- **Ambient sensor placement.** Keep it well clear of the top-right exhaust plume or it
  reads our own hot exhaust -> latches EXHAUST_ONLY forever (positive feedback loop).
  Shield the internal sensor from direct heat-gun IR so it reads air temp, not radiance.
- **No level shifter needed.** Every peripheral is 3.3V native: SSD1306 OLEDs,
  DHT22s, DRV8833. Choosing OLED panels over a 5V HD44780 LCD removed the
  single most dangerous wiring mistake the design previously allowed. Do not
  reintroduce a 5V display without also reintroducing the shifter.
- **Motor power is separate.** Never off the 3.3V rail or USB-through-board; brushed
  inrush browns out the MCU mid-demo. Common ground. 0.1uF ceramic across each motor's
  terminals. Brush noise killing I2C was the #1 failure risk with brushed motors;
  brushless fans remove it, which is a large part of why they were chosen.
- **Driver choice.** DRV8833 or TB6612FNG (native 3.3V logic). Fans are only ever
  switched on or off, so an H-bridge is not strictly required -- two logic-level
  N-MOSFETs would do -- but the DRV8833 is kept because it needs no wiring change and
  its reverse capability is still useful for bring-up testing. Note DRV8833 tops out at
  10.8V: use 5V fans with it, or TB6612FNG if you switch to 12V fans.
- **Buzzer drive.** Bare active buzzer element (~30mA) goes through an NPN, not straight
  off a GPIO (20mA recommended max). A buzzer *module* with onboard transistor is fine.
- **Pin selection (ESP32-WROOM-32).** GPIO 6-11 are SPI flash -- using them crashes
  the chip. GPIO 34-39 are INPUT ONLY and cannot drive anything. Strapping pins are
  0, 2, 5, 12, 15; GPIO 12 must be LOW at boot. 1/3 are UART0.
  Safe: 4, 13, 14, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27, 32, 33.
  The forbidden set differs entirely on the S3 backup board (33-37 lost to octal
  PSRAM, no input-only pins, safe 4-18 + 21). Never carry one pin map to the other.
  Authoritative map: hardware/01_pinout.md.
- **Non-blocking only.** millis() cooperative scheduler, zero delay() in loop().
  A DS18B20 conversion takes up to 750ms: start both, collect ~900ms later, then
  run the control law. Never wait on a sensor. The three OLED panels refresh one
  per slot so a single pass never stalls pushing three framebuffers.
- **Units.** All control logic in Celsius (DS18B20 native); convert only for display.
  80F = 26.67C.

## Work standards for this project
- Military-grade thoroughness, root causes not symptoms. No shortcuts.
- Real sensor data only. Loud failure if a reading is missing -- never a silent default.
- Never claim something works without proof of actual execution on hardware.
- Every claim in the report must be backed by a measurement we actually took.

## Layout
- `firmware/` -- ESP32 C++ (Arduino framework / PlatformIO)
- `hardware/` -- schematic, pinout, BOM, enclosure drawings
- `docs/`     -- project brief, design docs, test plan, report drafts
- `test/`     -- bench test procedures and recorded results

## Answered (was: open questions)
1. **Parts on hand:** several ESP32-WROOM-32 (USB-C) -- selected; one ESP32-S3 N16R8
   + IPEX antenna -- backup; breadboard, jumpers, resistors, 2x 130-size motors.
   Everything else still to order -- see hardware/02_bom_shopping_list.md.
2. **Weeks 1-2:** conceptual only. Design locked 2026-09-09. No prior code.
3. **No written rubric or handout.** Requirements are stated verbally each week.
   Capture them in docs/01_weekly_requirements_log.md -- that log is the de facto spec.
4. **Labor:** TJ and Tabitha build everything together. Claude is advisor, coder, and
   all digital deliverables.

## Answered by the syllabus (2026-09-24)
Full analysis: docs/09_course_requirements.md.
- **Reports 60%, presentations 20%, demonstrations 20%.** The report is the
  course. The working rig is 20% of it.
- **Reports are individual.** Team builds together; each member submits their
  own, in their own words, from shared data.
- **Formal group presentation from week 6**; weekly progress updates always.
- Nine required report sections, ECE Department format. Late: -10 pts/day.
- The syllabus demands **analytical theories and design calculations** and a
  **cost analysis**. Neither exists yet - the largest gap in the project.
- This is **project 1 of 2**; the second must be a different area, Tabitha
  leading.
- Instructor stated **verbally** that AI may be used in all aspects (2026-09-24).
  Reports still carry a short AI-use acknowledgment.

## Still open
- Confirm the instructor's week numbering. On ours the presentation is
  2026-09-30 and the report 2026-10-07.
- Obtain the ECE Department design reporting format document.
- Decide project 2.
