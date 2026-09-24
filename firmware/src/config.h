// Board and timing configuration.
// Pin map mirrors hardware/01_pinout.md -- ESP32-WROOM-32.
// If you change a pin here, change it there too.
#pragma once

#include <cstdint>

#include "display.h"

// ---- Pin map: ESP32-WROOM-32 ------------------------------------------------
// Safe pins on this part: 4, 13, 14, 16, 17, 18, 19, 21, 22, 23, 25, 26, 27,
// 32, 33.  GPIO 34-39 are INPUT ONLY and cannot drive anything.
// GPIO 6-11 are the SPI flash. GPIO 0/2/5/12/15 are strapping pins.
// DS18B20 1-wire sensors. They could share a single pin (each has a unique
// 64-bit ROM id), but separate pins are kept deliberately: "the one on GPIO 4
// is inside" is far easier to wire, debug and explain than enumerating ROM
// addresses, and spare GPIO is not scarce.
// Each data line needs a 4.7k pull-up to 3.3V. Breakout modules include it.
constexpr int PIN_TEMP_INSIDE  = 4;   // chamber sensor
constexpr int PIN_TEMP_OUTSIDE = 16;  // ambient sensor, clear of the exhaust plume
// Two independent hardware I2C buses. Three identical SSD1306 panels cannot
// share one bus: they are hardwired to 0x3C and only one address-select pad
// is available per module. Bus 0 carries two (0x3C and 0x3D, one jumpered),
// bus 1 carries the third. No level shifter anywhere - SSD1306 is 3.3 V native.
constexpr int PIN_I2C0_SDA     = 21;  // bus 0: IN and OUT panels
constexpr int PIN_I2C0_SCL     = 22;
constexpr int PIN_I2C1_SDA     = 17;  // bus 1: STATE panel
constexpr int PIN_I2C1_SCL     = 18;
constexpr int PIN_INTAKE_IN1   = 25;  // DRV8833 AIN1
constexpr int PIN_INTAKE_IN2   = 26;  // DRV8833 AIN2
constexpr int PIN_EXHAUST_IN1  = 27;  // DRV8833 BIN1
constexpr int PIN_EXHAUST_IN2  = 14;  // DRV8833 BIN2
constexpr int PIN_DRV_NSLEEP   = 13;  // DRV8833 nSLEEP, HIGH = bridge enabled

// Diagnostics. The DRV8833 reports its own faults on an open-drain pin that
// pulls LOW on overcurrent, overtemperature or undervoltage - reading it beats
// guessing. PIN_SENSE measures an output through a 1:1 divider so the firmware
// can see what the fan actually receives, rather than trusting a meter reading
// taken with no load.
constexpr int PIN_DRV_FAULT    = 19;  // to DRV8833 FAULT, internal pull-up
constexpr int PIN_SENSE        = 32;  // ADC1, via 1:1 divider from an OUT pin
constexpr float SENSE_DIVIDER  = 2.0f;
// Is the 1:1 divider physically built? Bare-jumper probing is the normal case
// on the bench, and then an output driven to VM would put 5 V directly on a
// 3.3 V ADC pin. False makes the firmware refuse to drive an output high while
// the probe is attached, and stops it scaling readings by a divider that is
// not there (which reported 3.3 V as 6.6 V).
constexpr bool SENSE_HAS_DIVIDER = false;
constexpr int PIN_BUZZER       = 23;  // buzzer module with onboard transistor

// Measured on the bench 2026-09-23: this 3-pin module sounds when the signal
// pin is pulled LOW and is silent when driven HIGH. Plenty of modules are
// wired the other way, so this is a property of the part, not of the design.
// Get it wrong and the alarm is inverted - silent during a fault and screaming
// the rest of the time.
constexpr bool BUZZER_ACTIVE_LOW = true;

// ---- Timing -----------------------------------------------------------------
// A DS18B20 conversion takes up to 750 ms at 12-bit resolution. We start both
// conversions, come back for the results once they are ready, and only then
// run the control law - so nothing ever blocks waiting on a sensor.
constexpr uint32_t SENSOR_PERIOD_MS  = 2500;
constexpr uint32_t CONVERT_WAIT_MS   = 900;   // > 750 ms worst-case conversion
constexpr uint32_t CTRL_OFFSET_MS    = 1000;  // control tick, just after the reads

constexpr uint32_t OLED_PERIOD_MS  = 500;   // 2 Hz refresh, staggered
constexpr uint32_t TRACE_PERIOD_MS = 5000;  // periodic serial heartbeat
constexpr uint32_t BUZZ_PATTERN_MS = 125;   // 4 Hz beep while in FAULT

// Safety net: a motor left running from the bring-up console returns to closed
// loop after this long, so nothing runs unattended on the bench.
constexpr uint32_t MANUAL_TIMEOUT_MS = 300000;  // 5 minutes

// ---- OLED panels -------------------------------------------------------
// Address-select pads on the back of the module choose 0x3C or 0x3D (often
// silkscreened 0x78 / 0x7A, the same addresses written 8-bit). Jumper ONE
// module on bus 0 to 0x3D; leave the other two at the factory 0x3C.
constexpr uint8_t OLED_ADDR_IN    = 0x3C;   // bus 0
constexpr uint8_t OLED_ADDR_OUT   = 0x3D;   // bus 0, jumpered
constexpr uint8_t OLED_ADDR_STATE = 0x3C;   // bus 1

constexpr uint32_t SERIAL_BAUD = 115200;
constexpr size_t CONSOLE_BUF = 64;
