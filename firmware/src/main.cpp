// ESDL Project 1 -- automated warehouse ventilation controller.
// Target: ESP32-WROOM-32. See hardware/01_pinout.md for wiring.
//
// This file is hardware glue and bring-up tooling only. The control law lives
// in control.cpp, which has no Arduino dependency and is proven on a host by
// test/test_control_host.cpp. Keep decision-making out of here.
//
// BRING-UP: open the serial monitor at 115200 and type `help`. Each peripheral
// can be exercised on its own, so a single miswired part does not hide the
// others.

#include <Arduino.h>
#include <DallasTemperature.h>
#include <OneWire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <Wire.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#include "config.h"
#include "control.h"
#include "display.h"

namespace {

// ---- Hardware objects -------------------------------------------------------
OneWire bus_inside(PIN_TEMP_INSIDE);
OneWire bus_outside(PIN_TEMP_OUTSIDE);
DallasTemperature ds_inside(&bus_inside);
DallasTemperature ds_outside(&bus_outside);
VentController controller(default_vent_config());

// Four possible panel slots: two addresses on each of the two buses. Roles are
// assigned to whatever actually answers, in a fixed probe order, so the rig
// works with two panels wired today and three once the third has had its
// address pad moved - with no config edit in between.
Adafruit_SSD1306 slot_dev0(OLED_W, OLED_H, &Wire, -1);
Adafruit_SSD1306 slot_dev1(OLED_W, OLED_H, &Wire, -1);
Adafruit_SSD1306 slot_dev2(OLED_W, OLED_H, &Wire1, -1);
Adafruit_SSD1306 slot_dev3(OLED_W, OLED_H, &Wire1, -1);

struct PanelSlot {
  Adafruit_SSD1306* dev;
  TwoWire* bus;
  uint8_t addr;
  uint8_t busno;
};
PanelSlot panel_slots[4] = {
    {&slot_dev0, &Wire, 0x3C, 0},
    {&slot_dev1, &Wire, 0x3D, 0},
    {&slot_dev2, &Wire1, 0x3C, 1},
    {&slot_dev3, &Wire1, 0x3D, 1},
};

// Roles, filled in probe order. A null pointer means that role has no panel,
// which is reported but never fatal.
Adafruit_SSD1306* oled_in = nullptr;
Adafruit_SSD1306* oled_out = nullptr;
Adafruit_SSD1306* oled_state = nullptr;
int8_t slot_of_in = -1, slot_of_out = -1, slot_of_state = -1;
uint8_t panels_found = 0;

// ---- Live state -------------------------------------------------------------
float t_inside_c = NAN;
float t_outside_c = NAN;

struct SensorStats {
  uint32_t ok = 0;
  uint32_t fail = 0;
  uint32_t consecutive_fail = 0;
};
SensorStats stat_inside, stat_outside;

enum class RunMode : uint8_t { AUTO, MANUAL };
RunMode run_mode = RunMode::AUTO;
uint32_t manual_since = 0;

FanDrive manual_intake = FanDrive::OFF;
FanDrive manual_exhaust = FanDrive::OFF;
BuzzerMode manual_buzzer = BuzzerMode::OFF;

// Bench injection. Lets the FSM be demonstrated without a heat gun, and lets
// the demo be rehearsed. Loudly flagged everywhere, and always off at boot.
bool sim_active = false;
float sim_in_c = NAN;
float sim_out_c = NAN;

// ---- Scheduler slots --------------------------------------------------------
uint32_t due_convert = 0;
uint32_t due_read = CONVERT_WAIT_MS;
uint32_t due_control = CTRL_OFFSET_MS;
uint32_t due_oled = 0;
uint8_t oled_turn = 0;   // stagger panel writes: one per refresh slot
uint32_t due_trace = 0;

VentState last_state = VentState::STANDBY;
char console[CONSOLE_BUF];
size_t console_len = 0;

// millis() wraps at ~49 days. Comparing the signed difference stays correct
// across the wrap; comparing the raw values does not.
inline bool due(uint32_t now, uint32_t when) {
  return static_cast<int32_t>(now - when) >= 0;
}

// Advance a slot by one period, resynchronising if we fell so far behind that
// catching up would fire a burst of back-to-back reads.
inline void reschedule(uint32_t now, uint32_t& slot, uint32_t period) {
  slot += period;
  if (due(now, slot)) slot = now + period;
}

inline float c_to_f(float c) { return c * 9.0f / 5.0f + 32.0f; }
inline float f_to_c(float f) { return (f - 32.0f) * 5.0f / 9.0f; }

// ---- Actuators --------------------------------------------------------------
void motor_drive(int in1, int in2, FanDrive d) {
  switch (d) {
    case FanDrive::FORWARD:
      digitalWrite(in1, HIGH);
      digitalWrite(in2, LOW);
      break;
    case FanDrive::REVERSE:
      digitalWrite(in1, LOW);
      digitalWrite(in2, HIGH);
      break;
    case FanDrive::OFF:
    default:
      // Both inputs high is BRAKE on a DRV8833: it shorts the winding, which
      // resists the propeller being windmilled by exhaust suction. Draws no
      // current at rest.
      digitalWrite(in1, HIGH);
      digitalWrite(in2, HIGH);
      break;
  }
}

// Three short chirps on every state change. This announces an *event* - the
// controller just decided something and the fans are about to move - which is
// what an audience needs during a demonstration. It is deliberately short and
// deliberately not the same sound as a fault: a continuous tone means the
// controller cannot trust its sensors and needs a human, and that distinction
// is lost if the buzzer is also the routine "I did a thing" noise.
constexpr uint32_t CHIRP_ON_MS  = 70;
constexpr uint32_t CHIRP_GAP_MS = 90;
constexpr uint8_t  CHIRP_COUNT  = 3;
constexpr uint32_t CHIRP_SLOT_MS  = CHIRP_ON_MS + CHIRP_GAP_MS;
constexpr uint32_t CHIRP_TOTAL_MS = CHIRP_COUNT * CHIRP_SLOT_MS;

uint32_t chirp_started = 0;
bool     chirp_running = false;

void start_chirp(uint32_t now) {
  chirp_started = now;
  chirp_running = true;
}

void buzzer_raw(bool on) {
  const bool level = BUZZER_ACTIVE_LOW ? !on : on;
  digitalWrite(PIN_BUZZER, level ? HIGH : LOW);
}

void buzzer_write(uint32_t now, BuzzerMode mode) {
  // The chirp takes priority while it runs, so a transition is audible even
  // when the state it lands in is silent. Signed difference, not unsigned
  // subtraction, so a millis() rollover mid-chirp cannot strand it on.
  if (chirp_running) {
    const int32_t elapsed = static_cast<int32_t>(now - chirp_started);
    if (elapsed >= 0 && elapsed < static_cast<int32_t>(CHIRP_TOTAL_MS)) {
      const uint32_t slot = static_cast<uint32_t>(elapsed) % CHIRP_SLOT_MS;
      buzzer_raw(slot < CHIRP_ON_MS);
      return;
    }
    chirp_running = false;
  }

  bool on = false;
  switch (mode) {
    case BuzzerMode::OFF: on = false; break;
    case BuzzerMode::STEADY: on = true; break;
    case BuzzerMode::PATTERN: on = ((now / BUZZ_PATTERN_MS) & 1u) != 0; break;
  }
  buzzer_raw(on);
}

// What the control law is actually acting on. While simulation is active the
// trace and the panels must show the injected values, not the real sensors -
// otherwise the display contradicts the state it is driving, which invites
// exactly the wrong question during a demo. The S marker and the
// [SIMULATED INPUT] tag are what tell you the numbers are not real.
float shown_in_c() { return sim_active ? sim_in_c : t_inside_c; }
float shown_out_c() { return sim_active ? sim_out_c : t_outside_c; }

// ---- I2C / OLED -------------------------------------------------------------
bool i2c_probe(TwoWire& bus, uint8_t addr) {
  bus.beginTransmission(addr);
  return bus.endTransmission() == 0;
}

int i2c_scan(TwoWire& bus, uint8_t* found, int max_found) {
  int n = 0;
  for (uint8_t a = 1; a < 127; ++a) {
    if (i2c_probe(bus, a) && n < max_found) found[n++] = a;
  }
  return n;
}

// Probe every slot and hand the found panels to roles in order: IN, OUT,
// STATE. Two panels therefore give the two temperatures, which is what you
// want while the third is still waiting on a soldering iron.
void oled_attach() {
  oled_in = oled_out = oled_state = nullptr;
  slot_of_in = slot_of_out = slot_of_state = -1;
  panels_found = 0;

  for (int i = 0; i < 4; ++i) {
    PanelSlot& s = panel_slots[i];
    if (!i2c_probe(*s.bus, s.addr)) continue;
    if (!s.dev->begin(SSD1306_SWITCHCAPVCC, s.addr, false, false)) continue;
    s.dev->setTextColor(SSD1306_WHITE);
    s.dev->cp437(true);
    if (!oled_in)        { oled_in = s.dev;    slot_of_in = i; }
    else if (!oled_out)  { oled_out = s.dev;   slot_of_out = i; }
    else if (!oled_state){ oled_state = s.dev; slot_of_state = i; }
    ++panels_found;
  }
}

void report_panel(const char* role, int8_t slot) {
  if (slot < 0) {
    Serial.printf("OLED %-6s: NOT FOUND\n", role);
    return;
  }
  Serial.printf("OLED %-6s: ok  (bus %u, 0x%02X)\n", role,
                panel_slots[slot].busno, panel_slots[slot].addr);
}

// Largest built-in text size whose rendered width still fits the panel.
// Using the built-in font with setTextSize keeps the glyphs blocky, which
// reads better across a room than a fine-stroked proportional face.
uint8_t fit_size(const char* text, uint8_t max_size) {
  const size_t len = strlen(text);
  for (uint8_t sz = max_size; sz > 1; --sz) {
    if (len * 6u * sz <= static_cast<size_t>(OLED_W)) return sz;
  }
  return 1;
}

void draw_centred(Adafruit_SSD1306& d, const char* text, uint8_t size, int y) {
  d.setTextSize(size);
  const int w = static_cast<int>(strlen(text)) * 6 * size;
  d.setCursor((OLED_W - w) / 2, y);
  d.print(text);
}

// One value panel: small label on top, the number as large as it will go.
void draw_value_panel(Adafruit_SSD1306* dp, const char* label, float celsius,
                      char marker) {
  if (!dp) return;
  Adafruit_SSD1306& d = *dp;
  char v[DISPLAY_FIELD_MAX];
  display_value(v, sizeof(v), celsius);

  d.clearDisplay();
  draw_centred(d, label, 2, 2);
  const uint8_t sz = fit_size(v, 5);
  draw_centred(d, v, sz, 30);
  d.setTextSize(1);
  d.setCursor(OLED_W - 8, OLED_H - 8);
  d.print("F");
  if (marker) {
    d.setCursor(2, OLED_H - 8);
    d.print(marker);
  }
  d.display();
}

// The state panel. Long labels wrap at the space rather than shrinking to
// unreadable; FAULT additionally scrolls, because motion draws the eye.
void draw_state_panel(Adafruit_SSD1306* dp, VentState st, char marker) {
  if (!dp) return;
  Adafruit_SSD1306& d = *dp;
  d.stopscroll();               // must stop before writing, or RAM corrupts
  d.clearDisplay();

  const char* text = display_state_text(st);
  const uint8_t sz = fit_size(text, 4);
  if (sz >= 3) {
    draw_centred(d, text, sz, (OLED_H - 8 * sz) / 2);
  } else {
    char head[16], tail[16];
    const char* sp = strchr(text, ' ');
    const size_t cut = sp ? static_cast<size_t>(sp - text) : strlen(text);
    snprintf(head, sizeof(head), "%.*s", static_cast<int>(cut), text);
    snprintf(tail, sizeof(tail), "%s", sp ? sp + 1 : "");
    const uint8_t s2 = min(fit_size(head, 4), fit_size(tail, 4));
    draw_centred(d, head, s2, 12);
    draw_centred(d, tail, s2, 12 + 8 * s2 + 4);
  }
  if (marker) {
    d.setTextSize(1);
    d.setCursor(2, OLED_H - 8);
    d.print(marker);
  }
  d.display();
  if (display_state_scrolls(st)) d.startscrollleft(0x00, 0x0F);
}

// Panels are refreshed one at a time. Each display() pushes a 1 KB frame over
// I2C and blocks for roughly 20 ms; staggering keeps any single loop pass
// short instead of stalling 60 ms three times a second.
void oled_refresh() {
  const char marker = display_marker(sim_active, run_mode == RunMode::MANUAL);
  switch (oled_turn) {
    case 0:
      draw_value_panel(oled_in, "IN", shown_in_c(), marker);
      break;
    case 1:
      draw_value_panel(oled_out, "OUT", shown_out_c(), marker);
      break;
    default:
      draw_state_panel(oled_state, controller.state(), marker);
      break;
  }
  oled_turn = (oled_turn + 1) % 3;
}

// ---- Serial trace -----------------------------------------------------------
void trace(uint32_t now, bool changed) {
  char ti[8], to[8];
  display_value(ti, sizeof(ti), shown_in_c());
  display_value(to, sizeof(to), shown_out_c());
  // Report what is ACTUALLY driving the pins. In manual mode the control
  // law's opinion is not what the hardware is doing, and a trace that
  // shows the wrong one cannot be used to verify a fan command.
  const VentOutputs o = (run_mode == RunMode::MANUAL)
                            ? VentOutputs{manual_intake, manual_exhaust,
                                          manual_buzzer}
                            : controller.outputs();
  Serial.printf("[%8lu] %-12s in=%5sF out=%5sF intake=%s exhaust=%s fail=%u%s%s%s\n",
                static_cast<unsigned long>(now),
                VentController::state_name(controller.state()), ti, to,
                VentController::fan_name(o.intake),
                VentController::fan_name(o.exhaust),
                static_cast<unsigned>(controller.fail_streak()),
                sim_active ? "  [SIMULATED INPUT]" : "",
                run_mode == RunMode::MANUAL ? "  [MANUAL OVERRIDE]" : "",
                changed ? "   <-- STATE CHANGE" : "");
}

// ---- Hardware diagnostics ---------------------------------------------------
// Answers "what is the driver actually doing", instead of inferring it from
// behaviour. FAULT is the chip's own opinion; the ADC reads the output pin
// through a divider, under real load, which a multimeter cannot do while the
// fan is connected.
bool drv_faulted() { return digitalRead(PIN_DRV_FAULT) == LOW; }

float sense_volts() {
  // 11 dB attenuation gives roughly 0-3.1 V at the pin; the divider halves
  // whatever the output is doing, so 5 V reads about 2.5 V.
  uint32_t acc = 0;
  for (int i = 0; i < 16; ++i) acc += analogRead(PIN_SENSE);
  const float pin_v = (acc / 16.0f) * 3.3f / 4095.0f;
  return pin_v * (SENSE_HAS_DIVIDER ? SENSE_DIVIDER : 1.0f);
}

void run_diagnostics() {
  Serial.println(F("\n--- driver diagnostics ---"));

  // nFAULT is open drain, so an UNWIRED pin reads high on our internal pull-up
  // and looks exactly like a healthy chip. Pull it down instead: only an
  // external pull-up on the module can hold it high against that, so this
  // separates "no fault" from "no wire" rather than reporting the same word
  // for both.
  pinMode(PIN_DRV_FAULT, INPUT_PULLDOWN);
  delay(20);
  const bool fault_wired = digitalRead(PIN_DRV_FAULT) == HIGH;
  pinMode(PIN_DRV_FAULT, INPUT_PULLUP);
  delay(20);
  if (!fault_wired) {
    // Only a module that fits its own pull-up on nFAULT can be detected this
    // way. A breakout exposing the bare open-drain pin reads identically wired
    // or not, because a healthy chip releases it either way. Say that, rather
    // than reporting a missing wire we cannot actually see.
    Serial.printf("DRV8833 FAULT pin : reads %s, no external pull-up found\n",
                  drv_faulted() ? "LOW" : "high");
    Serial.println(F("  Cannot confirm the wire: this module has no pull-up on"));
    Serial.println(F("  nFAULT, so wired and unwired look the same while the"));
    Serial.println(F("  chip is healthy. A real fault still pulls it LOW."));
  } else {
    Serial.printf("DRV8833 FAULT pin : wired, %s\n",
                  drv_faulted() ? "LOW  <-- CHIP IS REPORTING A FAULT"
                                : "high (no fault reported)");
  }
  if (digitalRead(PIN_DRV_NSLEEP)) {
    Serial.println(F("nSLEEP driven     : HIGH (enabled)"));
  } else {
    // Loud, not a status line. Every output reads dead while the bridge sleeps,
    // so a quiet note here is how a disabled driver gets misread as a fault.
    Serial.println(F("nSLEEP driven     : LOW  <-- DRIVER WAS DISABLED"));
    Serial.println(F("  All outputs read high-Z in this state, which looks"));
    Serial.println(F("  identical to a broken output. Re-asserting nSLEEP HIGH"));
    Serial.println(F("  now; any earlier probe run is void - repeat it."));
    digitalWrite(PIN_DRV_NSLEEP, HIGH);
    delay(5);
  }

  const RunMode saved = run_mode;
  run_mode = RunMode::MANUAL;
  struct Step { const char* what; FanDrive d; };
  // FORWARD drives the output to VM. With no divider fitted that lands 5 V on a
  // 3.3 V ADC pin, so the step is skipped rather than quietly risking the board.
  const Step with_div[] = {{"intake OFF ", FanDrive::OFF},
                           {"intake FWD ", FanDrive::FORWARD},
                           {"intake OFF ", FanDrive::OFF}};
  const Step no_div[]   = {{"intake OFF ", FanDrive::OFF},
                           {"intake OFF ", FanDrive::OFF}};
  if (!SENSE_HAS_DIVIDER) {
    Serial.println(F("NOTE: no divider fitted (SENSE_HAS_DIVIDER=false), so the"));
    Serial.println(F("  FORWARD step is SKIPPED - it would put VM on GPIO 32."));
    Serial.println(F("  Use 'probe a'/'probe b'; those never drive an output high."));
  }
  const Step* steps = SENSE_HAS_DIVIDER ? with_div : no_div;
  const size_t nsteps = SENSE_HAS_DIVIDER ? 3u : 2u;
  for (size_t si = 0; si < nsteps; ++si) {
    const Step& s = steps[si];
    motor_drive(PIN_INTAKE_IN1, PIN_INTAKE_IN2, s.d);
    delay(250);
    Serial.printf("%s -> sense reads %5.2f V   (fault %s)\n", s.what,
                  sense_volts(), drv_faulted() ? "LOW" : "high");
  }
  motor_drive(PIN_INTAKE_IN1, PIN_INTAKE_IN2, FanDrive::OFF);
  digitalWrite(PIN_DRV_NSLEEP, HIGH);
  run_mode = saved;

  Serial.println(F("If sense stays near 0 V while the pin is driven FWD, the"));
  Serial.println(F("output is not reaching the row the divider is in."));
  Serial.println(F("---------------------------\n"));
}

// Continuity tester built from the ESP32 itself - no multimeter, no divider.
//
// The trick is to never drive the output to 5 V. An H-bridge has two safe
// states for this: COAST (both inputs low, outputs high-impedance) and BRAKE
// (both inputs high, both outputs pulled to ground). With PIN_SENSE held by
// its internal pull-up, a row that is genuinely connected to that output will
// read HIGH during coast and LOW during brake. A row that is not connected
// sits HIGH the whole time. The sense pin never sees more than 3.3 V.
void run_probe(int in1, int in2, const char* label) {
  pinMode(PIN_SENSE, INPUT_PULLUP);
  // A sleeping DRV8833 puts every output in high-Z, which reads exactly like a
  // severed output wire. Asserting nSLEEP here instead of trusting whatever the
  // previous command left behind is the difference between measuring the board
  // and measuring our own last mistake.
  digitalWrite(PIN_DRV_NSLEEP, HIGH);
  delay(5);
  Serial.printf("\n--- continuity probe: %s ---\n", label);
  Serial.printf("driver: nSLEEP=HIGH (asserted for this test), FAULT=%s\n",
                drv_faulted() ? "LOW <-- CHIP IS FAULTING, result is void" : "high");
  Serial.println(F("Touch a jumper from GPIO 32 to the row you want to test."));
  Serial.println(F("CONNECTED rows follow the output. Unconnected rows stay high."));

  int follows = 0, total = 0;
  for (int cycle = 0; cycle < 6; ++cycle) {
    // COAST: outputs high-Z, pull-up should win
    digitalWrite(in1, LOW); digitalWrite(in2, LOW);
    delay(120);
    const int coast = digitalRead(PIN_SENSE);
    // BRAKE: both outputs tied low, a connected row is dragged down
    digitalWrite(in1, HIGH); digitalWrite(in2, HIGH);
    delay(120);
    const int brake = digitalRead(PIN_SENSE);

    ++total;
    if (coast == HIGH && brake == LOW) ++follows;
    Serial.printf("  cycle %d: coast=%s brake=%s  %s\n", cycle + 1,
                  coast ? "HIGH" : "LOW ", brake ? "HIGH" : "LOW ",
                  (coast == HIGH && brake == LOW) ? "<-- FOLLOWS" : "");
  }
  motor_drive(in1, in2, FanDrive::OFF);
  digitalWrite(PIN_DRV_NSLEEP, HIGH);

  if (follows == total) {
    Serial.printf("RESULT: CONNECTED to %s. The output reaches this row.\n", label);
  } else if (follows == 0) {
    Serial.printf("RESULT: NOT CONNECTED to %s. Nothing reaches this row.\n", label);
  } else {
    Serial.printf("RESULT: INTERMITTENT (%d of %d) - bad joint or loose pin.\n",
                  follows, total);
  }
  Serial.println(F("--------------------------------\n"));
}

// Node classifier. Answers "is this node really grounded, or is the firmware
// lying to me?" without trusting a single reading.
//
// A node is read twice, once pulled up and once pulled down. Floating follows
// the pull; tied does not. GPIO 33 is read the same way as a control - nothing
// is wired to it, so it MUST come back floating. If the control fails, the pull
// resistors or the read path are broken and every other number here is void.
void run_node_test() {
  Serial.println(F("\n--- node classifier ---"));

  // Coast both bridges first. OFF is BRAKE in this firmware, which actively
  // holds the outputs at ground, so classifying an output straight after a
  // probe run reports our own command back as a short in the board.
  digitalWrite(PIN_INTAKE_IN1, LOW);  digitalWrite(PIN_INTAKE_IN2, LOW);
  digitalWrite(PIN_EXHAUST_IN1, LOW); digitalWrite(PIN_EXHAUST_IN2, LOW);
  delay(30);

  pinMode(PIN_SENSE, INPUT_PULLUP);    delay(60);
  const int up = digitalRead(PIN_SENSE);
  pinMode(PIN_SENSE, INPUT_PULLDOWN);  delay(60);
  const int dn = digitalRead(PIN_SENSE);

  const int ctl = 33;  // deliberately unwired
  pinMode(ctl, INPUT_PULLUP);           delay(60);
  const int cup = digitalRead(ctl);
  pinMode(ctl, INPUT_PULLDOWN);         delay(60);
  const int cdn = digitalRead(ctl);

  Serial.printf("CONTROL GPIO %d (nothing wired): pullup=%s pulldown=%s -> %s\n",
                ctl, cup ? "HIGH" : "LOW ", cdn ? "HIGH" : "LOW ",
                (cup == HIGH && cdn == LOW) ? "floating, as it must be"
                                            : "*** CONTROL FAILED ***");
  if (!(cup == HIGH && cdn == LOW)) {
    Serial.println(F("The pull resistors or the read path are broken."));
    Serial.println(F("Ignore the result below - this is a firmware fault."));
    Serial.println(F("--------------------------------\n"));
    return;
  }

  Serial.printf("GPIO %d (your probe):          pullup=%s pulldown=%s\n",
                PIN_SENSE, up ? "HIGH" : "LOW ", dn ? "HIGH" : "LOW ");
  if (up == HIGH && dn == LOW)
    Serial.println(F("VERDICT: FLOATING. Nothing is driving this node."));
  else if (up == LOW && dn == LOW)
    Serial.println(F("VERDICT: TIED TO GROUND. It beats a 45k pullup - a real short."));
  else if (up == HIGH && dn == HIGH)
    Serial.println(F("VERDICT: TIED HIGH. Something holds this node at a rail."));
  else
    Serial.println(F("VERDICT: unstable - reads differently run to run."));
  Serial.println(F("--------------------------------\n"));
}

// Wire tester. Toggles one ESP32 output and checks whether PIN_SENSE follows
// it. Touch the sense jumper to the far end of a wire - a driver input pad,
// say - and this proves whether the signal actually arrives there. Tests the
// jumper, the breadboard row and the solder joint in one shot, at 3.3 V.
void run_wire_probe(int drive_pin, const char* label) {
  // PULLDOWN, not floating. A floating input reads random noise, which is
  // indistinguishable from a genuinely intermittent joint - the pulldown makes
  // a disconnected probe read a steady LOW instead, so "not touching" and
  // "bad connection" no longer look the same.
  pinMode(PIN_SENSE, INPUT_PULLDOWN);
  pinMode(drive_pin, OUTPUT);
  Serial.printf("\n--- wire probe: GPIO %d (%s) ---\n", drive_pin, label);
  Serial.println(F("Touch the GPIO 32 jumper to the far end of that wire."));
  if (drive_pin == PIN_DRV_NSLEEP)
    Serial.println(F("NOTE: this toggles the driver enable; it is re-asserted after."));

  int follows = 0;
  for (int i = 0; i < 6; ++i) {
    digitalWrite(drive_pin, HIGH); delay(120);
    const int hi = digitalRead(PIN_SENSE);
    digitalWrite(drive_pin, LOW); delay(120);
    const int lo = digitalRead(PIN_SENSE);
    if (hi == HIGH && lo == LOW) ++follows;
    Serial.printf("  cycle %d: drive HIGH -> sense %s | drive LOW -> sense %s  %s\n",
                  i + 1, hi ? "HIGH" : "LOW ", lo ? "HIGH" : "LOW ",
                  (hi == HIGH && lo == LOW) ? "<-- FOLLOWS" : "");
  }
  // Restore the board to its documented rest state. Toggling nSLEEP used to
  // strand the driver asleep with no indication, and every probe run after it
  // then reported a dead output that was really just a disabled bridge - a
  // fault this tool invented and then blamed on the hardware.
  digitalWrite(drive_pin, LOW);
  digitalWrite(PIN_DRV_NSLEEP, HIGH);
  motor_drive(PIN_INTAKE_IN1, PIN_INTAKE_IN2, FanDrive::OFF);
  motor_drive(PIN_EXHAUST_IN1, PIN_EXHAUST_IN2, FanDrive::OFF);

  if (follows == 6)
    Serial.printf("RESULT: WIRE GOOD. GPIO %d reaches the probe point.\n", drive_pin);
  else if (follows == 0)
    Serial.printf("RESULT: BROKEN. GPIO %d does NOT reach the probe point.\n", drive_pin);
  else
    Serial.printf("RESULT: INTERMITTENT (%d/6) - cold joint or loose pin.\n", follows);
  Serial.println(F("--------------------------------\n"));
}

// ---- Bring-up console -------------------------------------------------------
void print_help() {
  Serial.println(F(
      "\ncommands:\n"
      "  help                 this list\n"
      "  status               full state, sensor health, pin map\n"
      "  scan                 I2C bus scan\n"
      "  diag                 driver fault pin + output voltage sweep\n"
      "  probe a|b            continuity test an output against GPIO 32\n"
      "  wire <gpio>          does that GPIO reach the GPIO 32 probe point?\n"
      "  oled                 re-probe and re-attach the three panels\n"
      "  intake on|off|rev    drive the intake fan (on=forward)\n"
      "  exhaust on|off|rev   drive the exhaust fan (on=forward)\n"
      "  buzz on|off|pat      test the buzzer\n"
      "  sim <inF> <outF>     inject temperatures, e.g. `sim 85 70`\n"
      "  sim off              return to the real sensors\n"
      "  auto                 leave manual override, resume closed loop\n"
      "\nintake/exhaust/buzz enter MANUAL override; the control loop keeps\n"
      "running and tracing but stops driving the pins. `auto` hands it back.\n"));
}

void print_status() {
  const VentOutputs o = controller.outputs();
  char ti[8], to[8];
  display_value(ti, sizeof(ti), t_inside_c);
  display_value(to, sizeof(to), t_outside_c);

  Serial.println(F("\n--- status ---"));
  Serial.printf("mode          : %s%s\n",
                run_mode == RunMode::AUTO ? "AUTO (closed loop)" : "MANUAL OVERRIDE",
                sim_active ? " + SIMULATED INPUT" : "");
  Serial.printf("state         : %s  (%lu ms in state)\n",
                VentController::state_name(controller.state()),
                static_cast<unsigned long>(controller.ms_in_state(millis())));
  Serial.printf("inside        : %sF   ok=%lu fail=%lu streak=%lu\n", ti,
                (unsigned long)stat_inside.ok,
                (unsigned long)stat_inside.fail,
                (unsigned long)stat_inside.consecutive_fail);
  Serial.printf("outside       : %sF   ok=%lu fail=%lu streak=%lu\n", to,
                (unsigned long)stat_outside.ok,
                (unsigned long)stat_outside.fail,
                (unsigned long)stat_outside.consecutive_fail);
  Serial.printf("latches       : hot=%s crossvent=%s faultstreak=%u\n",
                controller.hot_latched() ? "yes" : "no",
                controller.cross_latched() ? "yes" : "no",
                static_cast<unsigned>(controller.fail_streak()));
  Serial.printf("outputs       : intake=%s exhaust=%s buzzer=%d\n",
                VentController::fan_name(o.intake),
                VentController::fan_name(o.exhaust),
                static_cast<int>(o.buzzer));
  Serial.printf("panels        : %u found  (IN %s  OUT %s  STATE %s)\n",
                panels_found, oled_in ? "ok" : "--", oled_out ? "ok" : "--",
                oled_state ? "ok" : "--");
  Serial.printf("pins          : tempIn=%d tempOut=%d  i2c0=%d/%d i2c1=%d/%d\n",
                PIN_TEMP_INSIDE, PIN_TEMP_OUTSIDE, PIN_I2C0_SDA,
                PIN_I2C0_SCL, PIN_I2C1_SDA, PIN_I2C1_SCL);
  Serial.printf("                intake=%d/%d exhaust=%d/%d nsleep=%d buzzer=%d\n",
                PIN_INTAKE_IN1, PIN_INTAKE_IN2, PIN_EXHAUST_IN1, PIN_EXHAUST_IN2,
                PIN_DRV_NSLEEP, PIN_BUZZER);
  if (run_mode == RunMode::MANUAL)
    Serial.printf("manual for    : %lu s of %lu\n",
                  (unsigned long)(static_cast<int32_t>(millis() - manual_since) / 1000),
                  (unsigned long)(MANUAL_TIMEOUT_MS / 1000));
  Serial.printf("uptime        : %lu s\n\n",
                static_cast<unsigned long>(millis() / 1000));
}

void enter_manual() {
  if (run_mode != RunMode::MANUAL) {
    run_mode = RunMode::MANUAL;
    Serial.println(F("** MANUAL OVERRIDE -- control loop no longer drives the pins."
                     " Type `auto` to hand it back."));
  }
  manual_since = millis();
}

void enter_auto() {
  if (run_mode != RunMode::AUTO) {
    Serial.println(F("** AUTO -- closed loop has the pins again."));
  }
  run_mode = RunMode::AUTO;
  manual_intake = FanDrive::OFF;
  manual_exhaust = FanDrive::OFF;
  manual_buzzer = BuzzerMode::OFF;
}

// Returns true if the argument was understood.
bool motor_command(const char* arg, FanDrive& target) {
  if (!arg) return false;
  if (!strcmp(arg, "on") || !strcmp(arg, "fwd")) {
    enter_manual();
    target = FanDrive::FORWARD;
    return true;
  }
  if (!strcmp(arg, "off")) {
    enter_manual();
    target = FanDrive::OFF;
    return true;
  }
  if (!strcmp(arg, "rev")) {
    enter_manual();
    target = FanDrive::REVERSE;
    Serial.println(F("   (reversed -- confirms both half-bridges work)"));
    return true;
  }
  return false;
}

void handle_command(char* line) {
  char* cmd = strtok(line, " \t");
  if (!cmd) return;
  char* a1 = strtok(nullptr, " \t");
  char* a2 = strtok(nullptr, " \t");

  if (!strcmp(cmd, "help") || !strcmp(cmd, "?")) {
    print_help();
  } else if (!strcmp(cmd, "status")) {
    print_status();
  } else if (!strcmp(cmd, "scan")) {
    uint8_t found[16];
    for (int b = 0; b < 2; ++b) {
      TwoWire& bus = b ? Wire1 : Wire;
      int n = i2c_scan(bus, found, 16);
      Serial.printf("I2C bus %d: %d device(s)\n", b, n);
      for (int i = 0; i < n; ++i) Serial.printf("  0x%02X\n", found[i]);
      if (n == 0)
        Serial.println(F("  nothing answered - check SDA/SCL not swapped,"
                         " 3.3 V present, common ground."));
    }
  } else if (!strcmp(cmd, "node")) {
    run_node_test();
  } else if (!strcmp(cmd, "diag")) {
    run_diagnostics();
  } else if (!strcmp(cmd, "wire")) {
    const int g = a1 ? atoi(a1) : -1;
    const RunMode saved = run_mode;
    run_mode = RunMode::MANUAL;
    switch (g) {
      case 25: run_wire_probe(25, "IN1 intake"); break;
      case 26: run_wire_probe(26, "IN2 intake"); break;
      case 27: run_wire_probe(27, "IN3 exhaust"); break;
      case 14: run_wire_probe(14, "IN4 exhaust"); break;
      case 13: run_wire_probe(13, "nSLEEP"); break;
      default: Serial.println(F("usage: wire 25|26|27|14|13"));
    }
    run_mode = saved;
  } else if (!strcmp(cmd, "probe")) {
    const RunMode saved = run_mode;
    run_mode = RunMode::MANUAL;
    if (a1 && a1[0] == 'b')
      run_probe(PIN_EXHAUST_IN1, PIN_EXHAUST_IN2, "OUT3/OUT4 (exhaust)");
    else
      run_probe(PIN_INTAKE_IN1, PIN_INTAKE_IN2, "OUT1/OUT2 (intake)");
    run_mode = saved;
  } else if (!strcmp(cmd, "oled")) {
    oled_attach();
    report_panel("IN", slot_of_in);
    report_panel("OUT", slot_of_out);
    report_panel("STATE", slot_of_state);
    for (int i = 0; i < 3; ++i) oled_refresh();
  } else if (!strcmp(cmd, "intake")) {
    if (!motor_command(a1, manual_intake))
      Serial.println(F("usage: intake on|off|rev"));
  } else if (!strcmp(cmd, "exhaust")) {
    if (!motor_command(a1, manual_exhaust))
      Serial.println(F("usage: exhaust on|off|rev"));
  } else if (!strcmp(cmd, "buzz")) {
    if (a1 && !strcmp(a1, "on")) {
      enter_manual();
      manual_buzzer = BuzzerMode::STEADY;
    } else if (a1 && !strcmp(a1, "off")) {
      enter_manual();
      manual_buzzer = BuzzerMode::OFF;
    } else if (a1 && !strcmp(a1, "pat")) {
      enter_manual();
      manual_buzzer = BuzzerMode::PATTERN;
    } else {
      Serial.println(F("usage: buzz on|off|pat"));
    }
  } else if (!strcmp(cmd, "sim")) {
    if (a1 && !strcmp(a1, "off")) {
      sim_active = false;
      sim_in_c = sim_out_c = NAN;
      // Drop the latches too. Without this the injected values keep deciding
      // the state through the hysteresis band after the injection has stopped.
      controller.reset_latches();
      Serial.println(F("** simulation off -- real sensors back in the loop,"
                       " latches cleared."));
    } else if (a1 && a2) {
      sim_in_c = f_to_c(atof(a1));
      sim_out_c = f_to_c(atof(a2));
      sim_active = true;
      Serial.printf("** SIMULATED INPUT: inside %.1fF outside %.1fF."
                    " NOT real sensor data. `sim off` to clear.\n",
                    c_to_f(sim_in_c), c_to_f(sim_out_c));
    } else {
      Serial.println(F("usage: sim <insideF> <outsideF>   |   sim off"));
    }
  } else if (!strcmp(cmd, "auto")) {
    enter_auto();
  } else {
    Serial.printf("unknown command: %s   (try `help`)\n", cmd);
  }
}

void poll_console() {
  while (Serial.available()) {
    char ch = static_cast<char>(Serial.read());
    if (ch == '\r') continue;
    if (ch == '\n') {
      console[console_len] = '\0';
      if (console_len) handle_command(console);
      console_len = 0;
      continue;
    }
    if (console_len < CONSOLE_BUF - 1) console[console_len++] = ch;
  }
}

// ---- Sensors ----------------------------------------------------------------
// DS18B20 conversions are started here and collected ~900 ms later, so the
// loop never blocks waiting on a sensor. DallasTemperature reports a
// disconnected probe as -127 C, which our range check already rejects; it is
// mapped to NaN so the rest of the code has one representation of "no data".
// DS18B20 is rated -55..125 C. We accept a narrower band matching the control
// law's own sanity check, so anything outside it is treated as no data rather
// than as a value.
constexpr float SENSOR_MIN_C = -40.0f;
constexpr float SENSOR_MAX_C = 80.0f;

bool readingValid(float c) {
  return !isnan(c) && c >= SENSOR_MIN_C && c <= SENSOR_MAX_C;
}

void start_conversions() {
  ds_inside.requestTemperatures();
  ds_outside.requestTemperatures();
}

float collect(DallasTemperature& ds, SensorStats& st) {
  const float c = ds.getTempCByIndex(0);
  if (c == DEVICE_DISCONNECTED_C || !readingValid(c)) {
    ++st.fail;
    ++st.consecutive_fail;
    return NAN;
  }
  ++st.ok;
  st.consecutive_fail = 0;
  return c;
}

void boot_self_test() {
  Serial.println(F("\n=== power-on self test ==="));

  uint8_t found[16];
  for (int b = 0; b < 2; ++b) {
    TwoWire& bus = b ? Wire1 : Wire;
    const int n = i2c_scan(bus, found, 16);
    Serial.printf("I2C bus %d      : %d device(s)\n", b, n);
    for (int i = 0; i < n; ++i) Serial.printf("                 0x%02X\n", found[i]);
  }

  report_panel("IN", slot_of_in);
  report_panel("OUT", slot_of_out);
  report_panel("STATE", slot_of_state);
  if (panels_found < 3) {
    Serial.println(F("                 roles are filled in probe order, so two"
                     " panels give you IN and OUT."));
    Serial.println(F("                 wire one panel per bus while both are"
                     " still at 0x3C."));
  }

  Serial.printf("DS18B20 inside : %d probe(s) on GPIO %d\n",
                ds_inside.getDeviceCount(), PIN_TEMP_INSIDE);
  Serial.printf("DS18B20 outside: %d probe(s) on GPIO %d\n",
                ds_outside.getDeviceCount(), PIN_TEMP_OUTSIDE);
  if (ds_inside.getDeviceCount() == 0 || ds_outside.getDeviceCount() == 0) {
    Serial.println(F("                 a missing probe usually means no 4.7k"
                     " pull-up on that data line."));
  }
  Serial.println(F("=== end self test ===  type `help` for bring-up commands\n"));
}

}  // namespace

void setup() {
  Serial.begin(SERIAL_BAUD);

  // Keep the bridge asleep until its inputs are driven, so a floating pin
  // cannot spin a fan during power-up.
  pinMode(PIN_DRV_NSLEEP, OUTPUT);
  digitalWrite(PIN_DRV_NSLEEP, LOW);

  const int motor_pins[] = {PIN_INTAKE_IN1, PIN_INTAKE_IN2, PIN_EXHAUST_IN1,
                            PIN_EXHAUST_IN2};
  for (int pin : motor_pins) {
    pinMode(pin, OUTPUT);
    digitalWrite(pin, LOW);
  }
  pinMode(PIN_DRV_FAULT, INPUT_PULLUP);
  analogSetPinAttenuation(PIN_SENSE, ADC_11db);
  pinMode(PIN_BUZZER, OUTPUT);
  // Silent level, not simply LOW - on an active-low module LOW is ON, which
  // would have the alarm sounding from the moment it powers up.
  digitalWrite(PIN_BUZZER, BUZZER_ACTIVE_LOW ? HIGH : LOW);

  digitalWrite(PIN_DRV_NSLEEP, HIGH);

  ds_inside.begin();
  ds_outside.begin();
  // Collect results on our own schedule rather than blocking in the call.
  ds_inside.setWaitForConversion(false);
  ds_outside.setWaitForConversion(false);
  start_conversions();

  Wire.begin(PIN_I2C0_SDA, PIN_I2C0_SCL);
  Wire1.begin(PIN_I2C1_SDA, PIN_I2C1_SCL);
  oled_attach();

  Serial.println();
  Serial.println(F("ESDL Project 1 -- ventilation controller"));
  Serial.println(F("hot ON 80.0F / OFF 77.0F, intake deadband 2.0F, dwell 10 s"));
  boot_self_test();
}

void loop() {
  const uint32_t now = millis();

  poll_console();

  // Kick off both conversions, then come back for the answers once they have
  // had time to finish. Nothing here waits on a sensor.
  if (due(now, due_convert)) {
    start_conversions();
    reschedule(now, due_convert, SENSOR_PERIOD_MS);
  }
  if (due(now, due_read)) {
    t_inside_c = collect(ds_inside, stat_inside);
    t_outside_c = collect(ds_outside, stat_outside);
    reschedule(now, due_read, SENSOR_PERIOD_MS);
  }

  // One control tick per sensor cycle. The fault counter counts *reads*, so
  // calling this every loop pass would trip FAULT within milliseconds.
  if (due(now, due_control)) {
    if (sim_active) {
      controller.update(now, sim_in_c, sim_out_c);
    } else {
      controller.update(now, t_inside_c, t_outside_c);
    }
    reschedule(now, due_control, SENSOR_PERIOD_MS);

    if (controller.state() != last_state) {
      last_state = controller.state();
      start_chirp(now);
      trace(now, true);
      reschedule(now, due_trace, TRACE_PERIOD_MS);
    }
  }

  // Bench safety: never leave a motor running unattended.
  //
  // Must use due()'s signed difference, not an unsigned subtraction. `now` is
  // captured at the top of loop() but poll_console() calls millis() again a
  // few microseconds later, so manual_since can be GREATER than now. Unsigned,
  // that underflows to ~4.29e9 and the timeout fires instantly - which is
  // exactly what stopped the fans from ever spinning on the bench.
  if (run_mode == RunMode::MANUAL && due(now, manual_since + MANUAL_TIMEOUT_MS)) {
    Serial.println(F("** manual override timed out -- returning to AUTO."));
    enter_auto();
  }

  // Actuators follow every pass so the buzzer pattern stays smooth.
  if (run_mode == RunMode::AUTO) {
    const VentOutputs out = controller.outputs();
    motor_drive(PIN_INTAKE_IN1, PIN_INTAKE_IN2, out.intake);
    motor_drive(PIN_EXHAUST_IN1, PIN_EXHAUST_IN2, out.exhaust);
    buzzer_write(now, out.buzzer);
  } else {
    motor_drive(PIN_INTAKE_IN1, PIN_INTAKE_IN2, manual_intake);
    motor_drive(PIN_EXHAUST_IN1, PIN_EXHAUST_IN2, manual_exhaust);
    buzzer_write(now, manual_buzzer);
  }

  if (due(now, due_oled)) {
    oled_refresh();
    // three panels share the refresh budget, so each slot is a third of it
    reschedule(now, due_oled, OLED_PERIOD_MS / 3);
  }
  if (due(now, due_trace)) {
    trace(now, false);
    reschedule(now, due_trace, TRACE_PERIOD_MS);
  }
}
