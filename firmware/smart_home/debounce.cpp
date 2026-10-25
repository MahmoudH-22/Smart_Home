#include "debounce.h"

/**
 * Configure the pin as INPUT_PULLUP and remember the debounce time.
 * @param pin Arduino pin number
 * @param stableMs how long a new level must stay unchanged to be accepted
 * @return void
 */
void DebouncedInput::begin(uint8_t pin, unsigned long stableMs) {
  _pin = pin;
  _stableMs = stableMs;
  pinMode(_pin, INPUT_PULLUP);
  _stable = _lastRaw = digitalRead(_pin);
  _changedAt = millis();
}

/**
 * Read the pin; the value only changes after it stayed stable for stableMs.
 * @return the stable logic level (HIGH / LOW)
 */
bool DebouncedInput::read() {
  bool raw = digitalRead(_pin);
  if (raw != _lastRaw) {            // something moved: restart the timer
    _lastRaw = raw;
    _changedAt = millis();
  }
  if (millis() - _changedAt > _stableMs) _stable = raw;   // quiet long enough: accept it
  return _stable;
}
