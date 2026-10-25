/**
 * debounce.h - read a switch without the "shaking" (bounce) of its metal contact.
 */
#pragma once
#include <Arduino.h>

class DebouncedInput {
 public:
  /**
   * Configure the pin as INPUT_PULLUP and remember the debounce time.
   * @param pin Arduino pin number
   * @param stableMs how long a new level must stay unchanged to be accepted
   * @return void
   */
  void begin(uint8_t pin, unsigned long stableMs);

  /**
   * Read the pin; the value only changes after it stayed stable for stableMs.
   * Call it often (every loop).
   * @return the stable logic level (HIGH / LOW)
   */
  bool read();

 private:
  uint8_t _pin = 0;
  unsigned long _stableMs = 30;
  bool _stable = HIGH;
  bool _lastRaw = HIGH;
  unsigned long _changedAt = 0;
};
