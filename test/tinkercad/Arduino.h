#pragma once
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
using std::isnan;  // Arduino provides this as a macro from math.h
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define A0 14
#define A1 15
extern unsigned long g_millis;
extern float g_fakeC[2];          // [0]=inside (A0), [1]=outside (A1)
inline unsigned long millis() { return g_millis; }
inline void pinMode(int, int) {}
inline void digitalWrite(int, int) {}
inline int analogRead(int pin) {
  float c = g_fakeC[pin == A0 ? 0 : 1];
  float volts = c / 100.0f + 0.5f;
  int raw = (int)(volts * 1023.0f / 5.0f + 0.5f);
  if (raw < 0) raw = 0;
  if (raw > 1023) raw = 1023;
  return raw;
}
inline char* dtostrf(double v, signed char w, unsigned char p, char* s) {
  char f[16]; snprintf(f, sizeof f, "%%%d.%df", (int)w, (int)p);
  sprintf(s, f, v); return s;
}
struct SerialStub {
  void begin(long) {}
  template <class T> void print(T) {}
  template <class T> void println(T) {}
  void println() {}
} extern Serial;
