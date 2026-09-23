/*
  ESDL Project 1 - TINKERCAD WIRING TEST
  =======================================

  This is NOT the controller. It has no state machine and makes no decisions.
  Its only job is to prove every part is wired correctly, one at a time,
  before you load the real sketch (esdl_vent_tinkercad.ino).

  It walks through four phases, 3 seconds each, forever:

    1. IDLE         both motors stopped, buzzer off
    2. BOTH FWD     both motors spin the same direction
    3. INTAKE REV   motor 1 reverses, motor 2 keeps going
    4. ALARM        motors stopped, buzzer on

  While it does that, the top line shows both temperatures live.

  WHAT A PASS LOOKS LIKE
    - Line 1 shows two believable room temperatures (~70 F each)
    - Dragging a TMP36 slider changes the matching number, and only that one
    - Phase 2: both motors turn
    - Phase 3: motor 1 visibly reverses  <- proves both halves of the H-bridge
    - Phase 4: the piezo sounds

  If any of those fails, fix it here. Do not move on to the real sketch with
  a known-bad connection - you will end up debugging the control logic for a
  wiring fault.

  WIRING
    LCD   RS=12  E=11  D4=5  D5=4  D6=3  D7=2   (note: descending)
    TMP36 inside -> A0     TMP36 outside -> A1
    L293D IN1=6  IN2=7  IN3=8  IN4=9
    Piezo -> 10
*/

#include <LiquidCrystal.h>

LiquidCrystal lcd(12, 11, 5, 4, 3, 2);   // RS, E, D4, D5, D6, D7

const int TMP_INSIDE  = A0;
const int TMP_OUTSIDE = A1;
const int INTAKE_1 = 6, INTAKE_2 = 7;    // L293D IN1 / IN2
const int EXHAUST_1 = 8, EXHAUST_2 = 9;  // L293D IN3 / IN4
const int BUZZER = 10;

const unsigned long PHASE_MS = 3000;

int phase = 0;
unsigned long phaseStarted = 0;

// TMP36: 10 mV per degree C, 500 mV offset at 0 C.
float readTempF(int pin) {
  float volts = analogRead(pin) * (5.0 / 1023.0);
  float celsius = (volts - 0.5) * 100.0;
  return celsius * 9.0 / 5.0 + 32.0;
}

void motor(int pinA, int pinB, int dir) {   // 1 = forward, -1 = reverse, 0 = stop
  digitalWrite(pinA, dir > 0 ? HIGH : LOW);
  digitalWrite(pinB, dir < 0 ? HIGH : LOW);
}

void setup() {
  Serial.begin(9600);
  lcd.begin(16, 2);

  pinMode(INTAKE_1, OUTPUT);
  pinMode(INTAKE_2, OUTPUT);
  pinMode(EXHAUST_1, OUTPUT);
  pinMode(EXHAUST_2, OUTPUT);
  pinMode(BUZZER, OUTPUT);

  lcd.setCursor(0, 0);
  lcd.print("ESDL VENT");
  lcd.setCursor(0, 1);
  lcd.print("WIRING TEST");
  Serial.println("ESDL Project 1 - wiring test");
  phaseStarted = millis();
}

void loop() {
  unsigned long now = millis();

  // Advance the phase without delay(), same non-blocking style as the
  // real firmware.
  if (now - phaseStarted >= PHASE_MS) {
    phase = (phase + 1) % 4;
    phaseStarted = now;

    switch (phase) {
      case 0:                                   // IDLE
        motor(INTAKE_1, INTAKE_2, 0);
        motor(EXHAUST_1, EXHAUST_2, 0);
        digitalWrite(BUZZER, LOW);
        break;
      case 1:                                   // BOTH FORWARD
        motor(INTAKE_1, INTAKE_2, 1);
        motor(EXHAUST_1, EXHAUST_2, 1);
        break;
      case 2:                                   // INTAKE REVERSED
        motor(INTAKE_1, INTAKE_2, -1);
        motor(EXHAUST_1, EXHAUST_2, 1);
        break;
      case 3:                                   // ALARM
        motor(INTAKE_1, INTAKE_2, 0);
        motor(EXHAUST_1, EXHAUST_2, 0);
        digitalWrite(BUZZER, HIGH);
        break;
    }
    Serial.print("phase ");
    Serial.println(phase);
  }

  // Refresh the display twice a second.
  static unsigned long dueLcd = 0;
  if (now >= dueLcd) {
    dueLcd = now + 500;

    char a[8], b[8], line[17];
    dtostrf(readTempF(TMP_INSIDE), 5, 1, a);
    dtostrf(readTempF(TMP_OUTSIDE), 5, 1, b);
    sprintf(line, "I%s O%s F", a, b);
    lcd.setCursor(0, 0);
    lcd.print(line);

    const char* names[] = {"1 IDLE          ",
                           "2 BOTH FORWARD  ",
                           "3 INTAKE REVERSE",
                           "4 ALARM         "};
    lcd.setCursor(0, 1);
    lcd.print(names[phase]);

    Serial.print(line);
    Serial.print("  ");
    Serial.println(names[phase]);
  }
}
