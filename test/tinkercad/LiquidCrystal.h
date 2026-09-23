#pragma once
// Host stub. The real library inherits print()/write() from Arduino's Print.
struct LiquidCrystal {
  LiquidCrystal(int, int, int, int, int, int) {}
  void begin(int, int) {}
  void setCursor(int, int) {}
  void write(char) {}
  void clear() {}
  template <class T> void print(T) {}
};
