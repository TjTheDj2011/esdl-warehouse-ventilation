# Bench Log

Recorded results from actual hardware sessions. Nothing here is design intent —
every line is something that was observed on the bench.

---

## Session 1 — 2026-09-23, first hardware bring-up

**Setup:** ESP32-WROOM-32 on `/dev/ttyUSB0` (CP2102), two breadboards, 5 V 2 A
wall adapter for the fan rail, USB for logic, common ground.

### Verified working

| Subsystem | Evidence |
|---|---|
| Board, toolchain, serial | Self test printed; firmware flashed and ran |
| Bare-board fault behaviour | With nothing attached: 0 I2C devices, 0 probes, FAULT at `fail=3`, `exhaust=fwd` — fails safe, does not sit in STANDBY |
| OLED panel 1 | Detected bus 0 @ 0x3C, assigned IN |
| OLED panel 2 | Detected bus 1 @ 0x3C, assigned OUT |
| DS18B20 inside | **ok=563, fail=0** |
| DS18B20 outside | **ok=563, fail=0** |
| Sensor plausibility | 77.1 / 79.4 F at rest; `out` drifted 79.4 → 79.0 → 78.8 F while settling |
| Both fans | Spin correctly wired direct to the 5 V rail |
| 5 V supply | Confirmed delivering (fans ran from it) |

### Control states, driven by `sim` on hardware

| Injected in/out (F) | State reached | Intake | Exhaust |
|---|---|---|---|
| 72 / 65 | `STANDBY` | off | off |
| 85 / 65 | `CROSS_VENT` | fwd | fwd |
| 85 / 84 | `EXHAUST_ONLY` | off | fwd |
| 85 / 95 | `SEALED` | off | off |
| 78.5 / 65 | held active | — | hysteresis did not release above 77 F |
| 74 / 65 | `STANDBY` | off | off |

All transitions matched `docs/03_control_matrix.md`. `fail=0` throughout.

### Defects found — none reachable by the host tests

1. **Panel roles were pinned to fixed (bus, address) pairs.** Two panels could
   not be used until the third had its address pad moved. Now assigned in probe
   order, so any number of panels works.

2. **Display contradicted the state it was driving.** During simulation the
   trace and panels showed the real sensors while the controller acted on the
   injected values, so `CROSS_VENT` appeared next to 76.3 F. Now both follow
   whatever the control law actually used.

3. **Manual-override timeout underflowed and fired instantly.** `now` is
   captured at the top of `loop()`, but `poll_console()` calls `millis()` again
   microseconds later, so `manual_since` could exceed `now`. The unsigned
   subtraction wrapped to ~4.29e9, clearing any threshold. Effect: a fan
   command was cancelled on the same loop pass and the fan never turned —
   presenting exactly like a wiring fault. Fixed by using the same signed
   rollover-safe comparison already used elsewhere in the file.

   **Worth noting in the report:** the 51 host checks verify the control law,
   which was correct throughout. This bug lived in console handling and in
   timing against a real `millis()` — neither of which the host harness
   reaches. It took the bench to find it.

### Buzzer polarity — measured, not assumed

The 3-pin active module sounds when its signal pin is pulled **LOW** and is
silent when driven **HIGH**. Verified by holding GPIO 23 high and listening.
Many modules are the opposite, so this is a property of this part.

Two consequences, both fixed:

- `buzzer_write()` now inverts via `BUZZER_ACTIVE_LOW` in config.h. Without it
  the alarm is exactly backwards: silent during a fault, sounding the rest of
  the time.
- `setup()` was driving the pin LOW at boot, which on this module means the
  alarm sounded from power-up before any logic ran. It now initialises to the
  silent level.

### Buzzer verified after the fix

Confirmed by ear: silent, then steady tone, then silent, then 4 Hz beeping,
then silent. The two alarm sounds are distinguishable, which is the point -
a thermal problem and a sensor problem can be told apart without looking at
a panel.

### Latch carry-over after simulation (found while reviewing status)

`status` showed `CROSS_VENT` with the chamber at 77.6 F and `hot=yes`, having
earlier run `sim 85 65`. The hysteresis was behaving correctly - 77.6 F sits
inside the 77-80 band, so the latch held - but the latch had been set by
injected data, not by the real chamber. A fresh boot at 77.6 F would sit in
STANDBY.

Left alone this means a rehearsal with `sim` can strand the rig in a state the
real temperature never produced, which during a demo would read as a fault.
`sim off` now clears the latches so the controller re-derives from live data.
Host check [18] covers it.

### Outstanding at end of session

**DRV8833 header pins are not soldered.** The board rests on the header rather
than being bonded to it, so there is no electrical connection to the breadboard.
Everything either side of that link is proven: the trace shows the ESP32 holding
`intake=fwd`, and both fans run direct from the same 5 V rail. Soldering is the
only remaining fault.

> **Withdrawn 2026-09-24.** This was wrong. The pins were present and correctly
> soldered; a seated module hides them inside the breadboard holes, and the
> diagnosis was made from a photograph rather than a measurement. The actual
> fault was a dead DRV8833 — see Session 2, where the replacement passed every
> output test with the same wiring. Left in place rather than deleted so the
> report does not cite a conclusion whose retraction is invisible.

Also outstanding: third OLED still needs its address pad moved to 0x3D, and the
buzzer is not yet wired.

---

## Session 2 — 2026-09-24

Actuator chain proven end to end. **Both fans run under firmware control.**

### What was actually wrong

The first DRV8833 was dead. Not miswired, not unpowered — dead. Replacing it
and resoldering the header fixed the build with no change to the wiring plan or
the firmware's control path.

Getting to that took most of a day, and three of the false trails were the
bench instrument's own bugs rather than faults in the board:

| Instrument bug | What it falsely reported |
|---|---|
| `wire` probe left its drive pin LOW on exit | Sweeping nSLEEP stranded the driver asleep; every later probe read the outputs as dead |
| Sense pin configured `INPUT` with no pull | Random noise read as `INTERMITTENT 1/6` on a good wire |
| `node` classified an output left in BRAKE | A healthy OUT1 reported as `TIED TO GROUND — a real short` |

All three are fixed and committed. The lesson is recorded in
`hardware/03_rebuild_layout.md`: the classifier now validates itself against
unwired GPIO 33 before it reports a verdict on anything.

Two conclusions stated with more confidence than the evidence supported, both
later withdrawn: that the header pins were missing (read from a photo — they
were present and correctly soldered), and that a FAULT wire was absent (this
module has no pull-up on nFAULT, so wired and unwired read identically while
the chip is healthy).

### Measurements — new driver, nothing attached

Probe on each output in turn, bridges coasted between readings:

| Node | `probe` | `node` | Cross-check |
|---|---|---|---|
| OUT1 | CONNECTED (6/6) | FLOATING | — |
| OUT2 | CONNECTED (6/6) | FLOATING | — |
| OUT3 | CONNECTED (6/6) | FLOATING | `probe a` NOT CONNECTED |
| OUT4 | CONNECTED (6/6) | FLOATING | `probe a` NOT CONNECTED |

`coast=HIGH brake=LOW` on all four. The cross-check matters: the intake bridge
cannot reach the exhaust outputs, so the probe is measuring the specific node
rather than something global. Instrument control (unwired GPIO 33) read
`floating` in every run.

For contrast, the dead board measured OUT1/OUT2 `coast=HIGH brake=HIGH`
(outputs never driven) and OUT3 `pullup=LOW pulldown=LOW`, 3/3 — tied to ground
with nothing attached.

### Measurements — fans

| Test | Result |
|---|---|
| Intake alone, `intake on`, red→OUT1 black→OUT2 | **Spins.** `intake=fwd`, no fault |
| Exhaust alone, red→OUT3 black→OUT4 | **Spins.** Driven by `FAULT` state fail-safe, not a manual command |
| Both fans, 12 s continuous | **Both spin.** 0 reboots, 0 brownout indicators, FAULT never asserted, serial never dropped |

The exhaust result is worth noting: it ran because the controller was in `FAULT`
with no sensors attached, and `FAULT` fail-safes to exhaust-on. That rule fired
for real on hardware rather than in simulation.

Both fans together is the CROSS_VENT load case. The 5 V supply held it with no
sign of sag, which was the open question about running both channels at once.

### Still outstanding

- Temperature sensors, OLED panels and buzzer not yet reconnected after the
  rebuild — the driver was brought up alone, deliberately.
- Third OLED still needs its address pad moved to 0x3D.
- `nFAULT` cannot be verified by self-test on this module; it only reports a
  real fault.

### Closed loop, first full run on hardware — 2026-09-24

Both DS18B20s live. The outside sensor had been wired to the wrong pin: GPIO 16
is silkscreened **RX2** on this board, and the jumper was elsewhere. Moving it
to RX2 brought the sensor up immediately.

Controller cleared `FAULT` on its own once the second sensor read, and stopped
the exhaust without intervention — the fail-safe releasing itself, not just
engaging.

**Sensor identity confirmed by hand heat**, which is the check that protects the
demo from a swapped pair:

| | start | end | delta |
|---|---|---|---|
| inside (GPIO 4) | 75.2 F | 87.0 F | **+11.8** |
| outside (GPIO 16) | 75.2 F | 75.1 F | −0.1 |

Only the sensor labelled INSIDE moved, so the labels match the pins.

**Full hysteresis cycle, uninterrupted:**

| Inside | State | Intake | Exhaust |
|---|---|---|---|
| 75.2 F | STANDBY | off | off |
| **80.8 F** rising | **CROSS_VENT** | **on** | **on** |
| 87.1 F | CROSS_VENT | on | on |
| 77.9 F falling | CROSS_VENT (latch holds) | on | on |
| **76.9 F** falling | **STANDBY** | off | off |

Engaged at 80.8 F and released at 76.9 F, holding through the 77-80 F band
without chattering. Confirms the mandated 80.0 on / 77.0 off hysteresis against
real sensor noise rather than in simulation.

CROSS_VENT rather than EXHAUST_ONLY was the correct selection throughout:
outside sat ~12 F cooler at peak, well past the 2 F differential deadband.

This is the first end-to-end run: real sensors -> FSM -> both fans, driven by a
real heat source, with no manual commands.

### Still outstanding after this run

OLED panels and buzzer not yet reconnected. `status` misreports the `outputs`
line during manual override - it prints the control law's desired outputs rather
than the pins actually being driven. Cosmetic; the telemetry line is correct.

### Full system restored, and the buzzer redesigned — 2026-09-24

All subsystems back after the rebuild, brought up one at a time:

| Subsystem | Evidence |
|---|---|
| DS18B20 inside (GPIO 4) | ok, `fail=0` |
| DS18B20 outside (GPIO 16 / **RX2**) | ok, `fail=0` after moving to the right pin |
| OLED IN | bus 0 @ 0x3C, rendering |
| OLED OUT | bus 1 @ 0x3D, rendering |
| OLED STATE | bus 1 @ 0x3C, rendering — all three panels live |
| Buzzer | both sounds confirmed by ear |
| Both fans | run under firmware control |

Three panels on two buses, with the modified 0x3D panel sharing bus 1 with an
unmodified 0x3C one. Adding the panels did not disturb the 1-wire sensors.

**Buzzer semantics changed on TJ's call.** Previously EXHAUST_ONLY and SEALED
held a continuous tone and FAULT beeped intermittently. Standing next to that
for a whole demonstration is punishing, and it also spends the loudest signal
the system has on conditions where nothing is actually broken.

Now:

- **Three short chirps on every state change.** Announces an *event* - the
  controller just decided something and the fans are about to move - which is
  what an audience needs in order to look up at the right moment.
- **Continuous tone only in FAULT.** The one state where the controller cannot
  trust its own sensors. Reserving the steady sound for it means "broken" is
  never confused with "working hard".

EXHAUST_ONLY and SEALED are announced by their entry chirp and by the visible
fan behaviour. They are conditions the controller is handling correctly with
good data, so they no longer sound an alarm.

Implemented in `main.cpp`, not in the control law: a chirp marks a transition,
not a state, so it is not a property of the state being entered. The chirp takes
priority over the steady mode while it runs, and uses a signed time difference
so a `millis()` rollover mid-chirp cannot strand the buzzer on.

Host suite updated and passing: **54 checks, 0 failures.**

### Full state sweep on hardware, after the change

| Injected in/out (F) | State | Intake | Exhaust | |
|---|---|---|---|---|
| 85 / 65 | CROSS_VENT | fwd | fwd | OK |
| 85 / 84 | EXHAUST_ONLY | off | fwd | OK |
| 85 / 95 | SEALED | off | off | OK |
| 85 / 65 | CROSS_VENT | fwd | fwd | OK — **seal released on its own** |
| 78 / 65 | CROSS_VENT | fwd | fwd | OK — **hysteresis holds inside the band** |
| 74 / 65 | STANDBY | off | off | OK |

Two of those answer questions the design is likely to be challenged on. The
seal releasing by itself when cool air returns shows `SEALED` cannot deadlock:
the condition that causes it is the condition that clears it. Holding
CROSS_VENT at 78 F shows the hysteresis is real rather than a bare threshold -
a `>` comparison would have dropped out at 79.9 F and chattered.

Returned to live sensors cleanly afterwards with no latch carry-over.

### FAULT verified on hardware by pulling a sensor — 2026-09-24

Inside probe's data wire pulled live, then reconnected. Nothing else touched.

```
[ 5009] STANDBY   in= 74.6F  out= 76.2F  exhaust=off  fail=0
[16000] FAULT     in= --.-F  out= 76.4F  exhaust=fwd  fail=3   <-- STATE CHANGE
[26000] STANDBY   in= 75.0F  out= 76.4F  exhaust=off  fail=0   <-- STATE CHANGE
```

Every clause of the "a missing reading is the dangerous failure" constraint
held:

| Required behaviour | Observed |
|---|---|
| Missing reading never renders as a plausible number | shown as `--.-`, not `0.0` |
| Takes several bad reads, so one glitch cannot trip it | exactly 3 consecutive |
| Fails SAFE to exhaust-on, never seals | `exhaust=fwd` |
| Continuous tone, distinct from the state-change chirp | confirmed by ear |
| Panel names the failure | `SENSOR` / `FAULT`, stacked, scrolling |
| Recovers unattended | returned to STANDBY, `fail=0`, no reboot |

The `0.0` case is the one that matters most: a fake-cold reading would have
parked the controller in STANDBY with the chamber heating and nothing running.
That is the silent failure the design exists to prevent, and it does not occur.

Scrolling was judged readable on the stacked two-line label, so it stays.

**All five states are now verified on hardware**, four by injection and FAULT by
physically breaking a sensor.
