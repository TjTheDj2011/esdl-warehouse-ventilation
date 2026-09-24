/*
  ESDL Project 1 - Automated Warehouse Ventilation System
  ===== TINKERCAD CIRCUITS VERSION =====

  Tinkercad has no ESP32 and no DHT22, so this is the Arduino Uno port:

      real build                  this simulation
      ------------------------    ----------------------------
      ESP32-WROOM-32              Arduino Uno R3
      2x DHT22 (digital 1-wire)   2x TMP36 (analog)
      DRV8833 H-bridge            L293D H-bridge
      I2C LCD (PCF8574)           parallel 16x2 LCD
      active buzzer module        piezo

  The CONTROL LAW is identical to firmware/src/control.cpp - same thresholds,
  same hysteresis, same five states. Only the hardware layer differs.

  Everything lives in one file because Tinkercad's editor accepts only one.

  HOW TO DRIVE THE DEMO
    Click a TMP36 in the simulator and drag its temperature slider.
      inside 72 / outside 65  -> STANDBY
      inside 85 / outside 65  -> CROSS_VENT    (both fans forward)
      inside 85 / outside 84  -> EXHAUST_ONLY  (intake off, exhaust on)
      inside 85 / outside 95  -> SEALED        (both fans stop, alarm)
    Allow ~10 s between changes: the minimum dwell deliberately blocks
    faster transitions.
    To force FAULT, move a TMP36's centre wire from its pin to GND. That
    reads about -50 C, which is outside the sensor's valid range, and after
    three consecutive bad reads the controller fails safe.
*/

#include <LiquidCrystal.h>

// ---------------------------------------------------------------- states
// Plain ints, deliberately NOT an enum. The Arduino IDE auto-generates
// function prototypes and injects them at the very top of the sketch -
// above the #include, above anything you can write. A custom type used in
// a function signature therefore can never be declared early enough, and
// you get "'FanDrive' does not name a type". Ints sidestep it entirely.
const int STANDBY      = 0;
const int CROSS_VENT   = 1;
const int EXHAUST_ONLY = 2;
const int SEALED       = 3;
const int FAULT        = 4;

const int FAN_OFF = 0;   // both driver inputs low - motor stopped
const int FAN_FWD = 1;
const int FAN_REV = 2;

// ---------------------------------------------------------------- pins
const int PIN_TMP_INSIDE   = A0;   // chamber sensor
const int PIN_TMP_OUTSIDE  = A1;   // ambient sensor
const int PIN_INTAKE_IN1   = 6;    // L293D pin 2   (IN1)
const int PIN_INTAKE_IN2   = 7;    // L293D pin 7   (IN2)
const int PIN_EXHAUST_IN1  = 8;    // L293D pin 10  (IN3)
const int PIN_EXHAUST_IN2  = 9;    // L293D pin 15  (IN4)
const int PIN_BUZZER       = 10;

LiquidCrystal lcd(12, 11, 5, 4, 3, 2);   // RS, E, D4, D5, D6, D7

// ---------------------------------------------------- control thresholds
// Fahrenheit shown for readability; all control maths is in Celsius.
const float HOT_ON_C      = 26.667;   // 80.0 F  - fans engage above this
const float HOT_OFF_C     = 25.000;   // 77.0 F  - and release below this
const float CROSS_ENTER_C =  1.111;   // outside 2.0 F cooler -> open intake
const float CROSS_EXIT_C  =  0.556;   // release at 1.0 F
const float SEAL_ENTER_C  = -1.667;   // outside 3.0 F HOTTER -> stop exchanging
const float SEAL_EXIT_C   = -0.833;   // release at 1.5 F

const int      FAULT_STREAK  = 3;     // consecutive bad reads before FAULT
const unsigned long MIN_DWELL_MS = 10000UL;
const unsigned long TICK_MS      = 2500UL;   // one control decision per tick
const unsigned long LCD_MS       = 500UL;    // 2 Hz display refresh
const unsigned long BUZZ_MS      = 125UL;    // 4 Hz fault pattern

// TMP36 is rated -40..125 C. Anything outside this is not a real reading.
const float SENSOR_MIN_C = -40.0;
const float SENSOR_MAX_C =  80.0;

// ---------------------------------------------------------------- state
int state = STANDBY;
bool  hotLatched   = false;   // chamber is hot, with hysteresis
bool  crossLatched = false;   // outside meaningfully cooler
bool  sealLatched  = false;   // outside meaningfully hotter
int   failStreak   = 0;
unsigned long enteredMs = 0;
bool  started = false;

float tInsideC  = NAN;
float tOutsideC = NAN;

unsigned long dueTick = 0, dueLcd = 0, dueTrace = 0;
char shadow[2][17];

// ------------------------------------------------------------- sensors
// TMP36: 10 mV per degree C, with a 500 mV offset at 0 C.
float readTempC(int pin) {
  int raw = analogRead(pin);
  float volts = raw * (5.0 / 1023.0);
  return (volts - 0.5) * 100.0;
}

bool readingValid(float c) {
  return !isnan(c) && c >= SENSOR_MIN_C && c <= SENSOR_MAX_C;
}

// ------------------------------------------------------- the control law
// Identical in structure to firmware/src/control.cpp :: VentController.
void updateControl(unsigned long now) {
  bool first = !started;
  if (first) { started = true; enteredMs = now; }

  bool inOk  = readingValid(tInsideC);
  bool outOk = readingValid(tOutsideC);

  if (inOk && outOk) failStreak = 0;
  else if (failStreak < 255) failStreak++;

  int desired;

  if (failStreak >= FAULT_STREAK) {
    // Fail loud and fail safe. Never a silent fall-through to STANDBY with
    // the chamber cooking.
    desired = FAULT;
  } else {
    // Latches only update from trustworthy data; below the fault threshold
    // we ride through a dropout on the last known-good decision.
    if (inOk) {
      if (!hotLatched && tInsideC >= HOT_ON_C)       hotLatched = true;
      else if (hotLatched && tInsideC <= HOT_OFF_C)  hotLatched = false;
    }
    if (inOk && outOk) {
      float diff = tInsideC - tOutsideC;
      if (!crossLatched && diff >= CROSS_ENTER_C)      crossLatched = true;
      else if (crossLatched && diff < CROSS_EXIT_C)    crossLatched = false;
      // Upper bound on exchange: moving air only cools while the air we pull
      // in is not hotter than the air we push out.
      if (!sealLatched && diff <= SEAL_ENTER_C)        sealLatched = true;
      else if (sealLatched && diff > SEAL_EXIT_C)      sealLatched = false;
    }

    if (!hotLatched)        desired = STANDBY;
    else if (sealLatched)   desired = SEALED;      // cannot deadlock: internal
    else if (crossLatched)  desired = CROSS_VENT;  // heat raises T_in until it
    else                    desired = EXHAUST_ONLY;// passes T_out, freeing it
  }

  if (desired != state) {
    // Dwell stops the fans hunting. A fault is a safety event and preempts
    // it, as does the very first decision after power-up.
    bool preempt = first || desired == FAULT;
    if (preempt || (now - enteredMs) >= MIN_DWELL_MS) {
      state = desired;
      enteredMs = now;
    }
  }
}

int intakeFor(int s) {
  // Brushless fans run one way only, so the intake is simply on or off.
  if (s == CROSS_VENT) return FAN_FWD;
  return FAN_OFF;      // STANDBY, EXHAUST_ONLY, SEALED, FAULT
}

int exhaustFor(int s) {
  if (s == CROSS_VENT || s == EXHAUST_ONLY || s == FAULT) return FAN_FWD;
  return FAN_OFF;
}

// --------------------------------------------------------- actuators
void driveFan(int in1, int in2, int d) {
  if (d == FAN_FWD)      { digitalWrite(in1, HIGH); digitalWrite(in2, LOW);  }
  else if (d == FAN_REV) { digitalWrite(in1, LOW);  digitalWrite(in2, HIGH); }
  else                   { digitalWrite(in1, LOW);  digitalWrite(in2, LOW);  }
}

void driveBuzzer(unsigned long now) {
  bool on = false;
  if (state == EXHAUST_ONLY || state == SEALED) on = true;            // steady
  else if (state == FAULT) on = ((now / BUZZ_MS) % 2) != 0;           // 4 Hz
  digitalWrite(PIN_BUZZER, on ? HIGH : LOW);
}

// ------------------------------------------------------------- display
const char* stateLabel() {
  switch (state) {
    case STANDBY:      return "STATE: STANDBY";
    case CROSS_VENT:   return "STATE: CROSS VENT";
    case EXHAUST_ONLY: return "STATE: EXHAUST";
    case SEALED:       return "STATE: SEALED";
    case FAULT:        return "!! SENSOR FAULT";
  }
  return "STATE: ?";
}

// A failed read must look failed, never like a plausible 0.0
void fmtTempF(char* out, float c) {
  if (!readingValid(c)) { strcpy(out, " --.-"); return; }
  dtostrf(c * 9.0 / 5.0 + 32.0, 5, 1, out);
}

void writeLine(int row, const char* text) {
  char padded[17];
  for (int i = 0; i < 16; i++) padded[i] = text[i] ? text[i] : ' ';
  padded[16] = '\0';
  for (int i = 0; i < 16 && text[i]; i++) padded[i] = text[i];
  // rewrite only the characters that changed - a full clear() every refresh
  // is what makes these displays flicker
  for (int col = 0; col < 16; col++) {
    if (padded[col] == shadow[row][col]) continue;
    lcd.setCursor(col, row);
    lcd.write(padded[col]);
    shadow[row][col] = padded[col];
  }
}

void refreshLcd() {
  char ti[8], to[8], line[24];
  fmtTempF(ti, tInsideC);
  fmtTempF(to, tOutsideC);
  sprintf(line, "I%s O%s F", ti, to);
  writeLine(0, line);
  writeLine(1, stateLabel());
}

void trace() {
  char ti[8], to[8];
  fmtTempF(ti, tInsideC);
  fmtTempF(to, tOutsideC);
  Serial.print(millis());
  Serial.print("  ");
  Serial.print(stateLabel());
  Serial.print("  in=");  Serial.print(ti);
  Serial.print("F out="); Serial.print(to);
  Serial.print("F  intake=");
  Serial.print(intakeFor(state) == FAN_FWD ? "fwd" :
               intakeFor(state) == FAN_REV ? "rev" : "off");
  Serial.print(" exhaust=");
  Serial.print(exhaustFor(state) == FAN_FWD ? "fwd" : "off");
  Serial.print("  fail=");
  Serial.println(failStreak);
}

// ------------------------------------------------------------- sketch
void setup() {
  Serial.begin(9600);

  pinMode(PIN_INTAKE_IN1, OUTPUT);
  pinMode(PIN_INTAKE_IN2, OUTPUT);
  pinMode(PIN_EXHAUST_IN1, OUTPUT);
  pinMode(PIN_EXHAUST_IN2, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  digitalWrite(PIN_INTAKE_IN1, LOW);
  digitalWrite(PIN_INTAKE_IN2, LOW);
  digitalWrite(PIN_EXHAUST_IN1, LOW);
  digitalWrite(PIN_EXHAUST_IN2, LOW);
  digitalWrite(PIN_BUZZER, LOW);

  lcd.begin(16, 2);
  for (int r = 0; r < 2; r++)
    for (int c = 0; c < 16; c++) shadow[r][c] = ' ';

  Serial.println("ESDL Project 1 - ventilation controller (Tinkercad)");
  Serial.println("hot ON 80.0F / OFF 77.0F, intake deadband 2.0F, dwell 10 s");
}

void loop() {
  unsigned long now = millis();

  // Non-blocking cooperative scheduler. No delay() anywhere.
  if ((long)(now - dueTick) >= 0) {
    tInsideC  = readTempC(PIN_TMP_INSIDE);
    tOutsideC = readTempC(PIN_TMP_OUTSIDE);
    int before = state;
    updateControl(now);
    dueTick = now + TICK_MS;
    if (state != before) trace();
  }

  driveFan(PIN_INTAKE_IN1,  PIN_INTAKE_IN2,  intakeFor(state));
  driveFan(PIN_EXHAUST_IN1, PIN_EXHAUST_IN2, exhaustFor(state));
  driveBuzzer(now);

  if ((long)(now - dueLcd) >= 0)   { refreshLcd(); dueLcd = now + LCD_MS; }
  if ((long)(now - dueTrace) >= 0) { trace();      dueTrace = now + 5000UL; }
}
