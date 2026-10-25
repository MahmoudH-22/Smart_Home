#include "security.h"
#include "config.h"
#include "state.h"
#include "debounce.h"

static DebouncedInput reedIn;
static DebouncedInput armIn;

/**
 * Turn the buzzer on (continuous tone) or off. Works for active and passive buzzers.
 * Only touches the pin when the state changes, so the tone stays clean.
 * @param on true = sound, false = silent
 * @return void
 */
static void buzzer(bool on) {
  static bool isOn = false;
  if (on == isOn) return;
  isOn = on;
  if (on) tone(PIN_BUZZER, BUZZ_HZ);
  else noTone(PIN_BUZZER);
}

/**
 * Set up the sensor, toggle and buzzer pins.
 * @return void
 */
void securityBegin() {
  reedIn.begin(PIN_REED, DEBOUNCE_MS);
  armIn.begin(PIN_ARM, DEBOUNCE_MS);
  pinMode(PIN_BUZZER, OUTPUT);
}

/**
 * Read the inputs, update the shared state and drive the buzzer.
 * Sends "ALERT:WINDOW_OPEN" on Serial once, at the moment the alarm starts
 * (the ESP8266 will forward it to the recipients).
 * @return void
 */
void securityUpdate() {
  static bool lastAlarm = false;

  sys.windowOpen = (reedIn.read() == REED_OPEN_LEVEL);
  sys.armed      = ALWAYS_ARMED || (armIn.read() == LOW);
  sys.alarmOn    = sys.armed && sys.windowOpen;

  buzzer(sys.alarmOn);

  if (sys.alarmOn && !lastAlarm) Serial.println(F("ALERT:WINDOW_OPEN"));
  lastAlarm = sys.alarmOn;
}
