#include "Arduino.h"
unsigned long g_millis = 0;
float g_fakeC[2] = {20.0f, 20.0f};
SerialStub Serial;
#include "esdl_vent_tinkercad.ino"

#include <iostream>
static int checks = 0, fails = 0;
static float F2C(float f) { return (f - 32.0f) * 5.0f / 9.0f; }
static const char* NAMES[] = {"STANDBY","CROSS_VENT","EXHAUST_ONLY","SEALED","FAULT"};

static void hold(float inF, float outF, unsigned long ms) {
  g_fakeC[0] = F2C(inF); g_fakeC[1] = F2C(outF);
  for (unsigned long t = 0; t < ms; t += 2500) { g_millis += 2500; loop(); }
}
static void groundSensor(unsigned long ms) {   // wire moved to GND -> -50 C
  g_fakeC[0] = -50.0f;
  for (unsigned long t = 0; t < ms; t += 2500) { g_millis += 2500; loop(); }
}
static void check(bool ok, const char* what) {
  ++checks; if (!ok) ++fails;
  printf("  [%s] %-13s %s\n", ok ? "PASS" : "FAIL", NAMES[state], what);
}

int main() {
  printf("\n=== Tinkercad port: behavioural equivalence ===\n");
  setup();

  printf("\n[1] Cold chamber\n");
  hold(72, 65, 30000); check(state == STANDBY, "72F in / 65F out -> STANDBY");

  printf("\n[2] Hot, outside cooler\n");
  hold(85, 65, 25000); check(state == CROSS_VENT, "85/65 -> CROSS_VENT");
  check(intakeFor(state) == FAN_FWD && exhaustFor(state) == FAN_FWD,
        "both fans forward");

  printf("\n[3] Outside slightly hotter\n");
  hold(85, 87, 25000); check(state == EXHAUST_ONLY, "85/87 -> EXHAUST_ONLY");
  check(intakeFor(state) == FAN_OFF && exhaustFor(state) == FAN_FWD,
        "intake off, exhaust on");

  printf("\n[4] Outside much hotter\n");
  hold(85, 95, 25000); check(state == SEALED, "85/95 -> SEALED");
  check(intakeFor(state) == FAN_OFF && exhaustFor(state) == FAN_OFF,
        "both fans stop - no forced exchange with hotter air");

  printf("\n[5] Seal releases when chamber passes outside\n");
  hold(97, 95, 25000); check(state != SEALED, "97/95 releases the seal");

  printf("\n[6] Hysteresis: 79F must not hold the fans on below 77F\n");
  hold(85, 65, 25000); check(state == CROSS_VENT, "established CROSS_VENT");
  hold(78.5, 65, 25000); check(state == CROSS_VENT, "78.5F still above OFF point");
  hold(74, 65, 25000);  check(state == STANDBY, "74F releases to STANDBY");

  printf("\n[7] Sensor grounded -> FAULT, fail-safe\n");
  hold(85, 65, 25000); check(state == CROSS_VENT, "running normally");
  groundSensor(10000); check(state == FAULT, "3 bad reads -> FAULT");
  check(exhaustFor(state) == FAN_FWD, "FAULT fails SAFE: exhaust still driven");
  check(state != STANDBY, "never silently lands in STANDBY");

  printf("\n[8] Recovery\n");
  hold(85, 65, 25000); check(state == CROSS_VENT, "good reads restore control");

  printf("\n=== %d checks, %d failures ===\n\n", checks, fails);
  return fails ? 1 : 0;
}
