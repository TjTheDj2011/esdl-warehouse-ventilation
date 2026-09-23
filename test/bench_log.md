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

Also outstanding: third OLED still needs its address pad moved to 0x3D, and the
buzzer is not yet wired.
