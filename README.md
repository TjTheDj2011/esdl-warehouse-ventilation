# ESDL Project 1 — Automated Warehouse Ventilation System

Closed-loop thermal ventilation controller on an ESP32-WROOM-32. Two DHT22
sensors (chamber + ambient) drive a five-state machine that commands an intake
and an exhaust fan through a DRV8833, with live telemetry on an I2C LCD and a
piezo alarm on thermal overload or sensor failure.

**Team:** TJ, Tabitha, Claude · 7-week ESDL course project · Tennessee State ECE

---

## Where everything is

### Start here
| Document | What it answers |
|---|---|
| [CLAUDE.md](CLAUDE.md) | The brief: goal, objectives, standing engineering constraints |
| [hardware/05_hardware_checklist.md](hardware/05_hardware_checklist.md) | **Tick-off checklist: have it / buying it / verify it** |
| [hardware/03_physical_build.md](hardware/03_physical_build.md) | What to build, and in what order |
| [hardware/04_parts_acceptance.md](hardware/04_parts_acceptance.md) | Supply-room card: which substitutions are fine, which break the design |
| [docs/04_engineering_diagrams.pdf](docs/04_engineering_diagrams.pdf) | Block diagram, control flowchart, decision bands, airflow — 4 pages |
| [docs/05_schematic.pdf](docs/05_schematic.pdf) | Circuit schematic, 2 sheets |
| [docs/06_wiring_diagram.pdf](docs/06_wiring_diagram.pdf) | Pictorial wiring + connection table, 3 sheets |
| [docs/08_tinkercad_layout.pdf](docs/08_tinkercad_layout.pdf) | Tinkercad simulation layout, 2 sheets |

### Design
| Document | What it answers |
|---|---|
| [docs/03_control_matrix.md](docs/03_control_matrix.md) | Every state, fan direction, and why. The firmware is tested against this table. |
| [hardware/01_pinout.md](hardware/01_pinout.md) | Authoritative pin map, and which pins are forbidden on this part |

### Build and run
| Document | What it answers |
|---|---|
| [docs/02_bringup_guide.md](docs/02_bringup_guide.md) | Seven ordered bring-up steps, console commands, symptom → cause table |
| [docs/07_tinkercad_guide.md](docs/07_tinkercad_guide.md) | Tinkercad Circuits simulation — parts, wiring, demo script |
| [docs/01_weekly_requirements_log.md](docs/01_weekly_requirements_log.md) | What the instructor asked for each week — our de-facto rubric |

## Firmware

```
firmware/src/control.{h,cpp}   the state machine      (no Arduino dependency)
firmware/src/display.{h,cpp}   LCD formatting         (no Arduino dependency)
firmware/src/main.cpp          hardware glue + serial bring-up console
firmware/src/config.h          pin map and timing
```

The control law and display formatting carry no Arduino dependency, so both are
provable on a laptop before hardware exists — and neither changed when the target
board did.

```bash
./test/run_host_tests.sh      # 47 checks, no hardware needed
./test/tinkercad/run.sh       # 16 checks: Tinkercad port matches the firmware
cd firmware && pio run        # build for ESP32-WROOM-32
python3 docs/diagrams/make_flowchart.py        # engineering diagrams
python3 docs/diagrams/make_schematic.py        # schematic
python3 docs/diagrams/make_wiring.py           # wiring diagram
python3 docs/diagrams/make_tinkercad_layout.py # Tinkercad layout
```

## Control summary

Governing rule: **move air only when the air pulled in is cooler than the air
pushed out.** Let `D = T_in − T_out`.

| Condition | State | Intake | Exhaust |
|---|---|---|---|
| chamber below 77 F | `STANDBY` | braked | braked |
| hot, `D ≥ +2 F` | `CROSS_VENT` | forward | forward |
| hot, `−3 F < D < +2 F` | `EXHAUST_ONLY` | **reverse** | forward |
| hot, `D ≤ −3 F` | `SEALED` | braked | braked |
| 3 bad sensor reads | `FAULT` | reverse | forward |

No refrigeration exists in this design, so the system cannot cool below ambient.
The claim it supports is that it drives the chamber toward the lowest temperature
obtainable by air exchange and never takes an action that makes it hotter.

## Status — week 4 of 7

- Design locked. Firmware written, compiles clean, 47/47 host tests pass.
- **Nothing verified on hardware.** No parts in hand beyond the board and motors.
- Critical path: order the parts in Part A. Lead time is the schedule risk.
