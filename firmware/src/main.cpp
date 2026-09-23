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

void buzzer_write(uint32_t now, BuzzerMode mode) {
  bool on = false;
  switch (mode) {
    case BuzzerMode::OFF: on = false; break;
    case BuzzerMode::STEADY: on = true; break;
    case BuzzerMode::PATTERN: on = ((now / BUZZ_PATTERN_MS) & 1u) != 0; break;
  }
  digitalWrite(PIN_BUZZER, on ? HIGH : LOW);
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
  const VentOutputs o = controller.outputs();
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

// ---- Bring-up console -------------------------------------------------------
void print_help() {
  Serial.println(F(
      "\ncommands:\n"
      "  help                 this list\n"
      "  status               full state, sensor health, pin map\n"
      "  scan                 I2C bus scan\n"
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
      Serial.println(F("** simulation off -- real sensors back in the loop."));
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
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_BUZZER, LOW);

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
      trace(now, true);
      reschedule(now, due_trace, TRACE_PERIOD_MS);
    }
  }

  // Bench safety: never leave a motor running unattended.
  if (run_mode == RunMode::MANUAL &&
      static_cast<uint32_t>(now - manual_since) >= MANUAL_TIMEOUT_MS) {
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
