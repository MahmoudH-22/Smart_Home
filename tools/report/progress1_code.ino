#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// ================= settings =================
const uint8_t LCD_ADDR        = 0x27;   // the address the scanner found
const uint8_t PIN_REED        = 2;      // MC-38 -> D2 + GND
const uint8_t PIN_BUZZER      = 8;      // buzzer + -> D8, - -> GND
const uint8_t PIN_ARM         = 7;      // toggle middle -> D7, side -> GND
const bool    ALWAYS_ARMED    = true;   // true = no toggle needed; false when the toggle is wired
const uint8_t REED_OPEN_LEVEL = HIGH;   // if the window shows reversed, change to LOW
const unsigned int BUZZ_HZ    = 2500;   // buzzer tone frequency

LiquidCrystal_I2C lcd(LCD_ADDR, 16, 2);

bool armed = false, windowOpen = false, alarmOn = false;

/**
 * Read a pin and return its value only after it stays stable for 30 ms.
 * @param pin Arduino pin number
 * @param stable last stable value (updated in place)
 * @param lastRaw last raw reading (updated in place)
 * @param changedAt time of the last raw change (updated in place)
 * @return the stable logic level (HIGH / LOW)
 */
bool readDebounced(uint8_t pin, bool &stable, bool &lastRaw, unsigned long &changedAt) {
  bool raw = digitalRead(pin);
  if (raw != lastRaw) { lastRaw = raw; changedAt = millis(); }
  if (millis() - changedAt > 30) stable = raw;
  return stable;
}

/**
 * Turn the buzzer on (continuous tone) or off. Works for active and passive buzzers.
 * @param on true = sound, false = silent
 * @return void
 */
void buzzer(bool on) {
  static bool isOn = false;
  if (on == isOn) return;
  isOn = on;
  if (on) tone(PIN_BUZZER, BUZZ_HZ); else noTone(PIN_BUZZER);
}

/**
 * Write two lines (padded to 16 chars), redrawing only the lines that changed.
 * @param l1 row 0 text
 * @param l2 row 1 text
 * @return void
 */
void lcdWrite(const char *l1, const char *l2) {
  static char shown[2][17] = { "", "" };
  const char *src[2] = { l1, l2 };
  for (uint8_t r = 0; r < 2; r++) {
    char buf[17];
    snprintf(buf, sizeof(buf), "%-16.16s", src[r]);
    if (strcmp(buf, shown[r]) != 0) {
      lcd.setCursor(0, r);
      lcd.print(buf);
      strcpy(shown[r], buf);
    }
  }
}

/**
 * Read the reed + toggle. Window open while armed = buzzer ON; window closed = buzzer OFF.
 * @return void
 */
void updateSecurity() {
  static bool rS = HIGH, rL = HIGH, aS = HIGH, aL = HIGH;
  static unsigned long rT = 0, aT = 0;
  static bool lastAlarm = false;

  windowOpen = (readDebounced(PIN_REED, rS, rL, rT) == REED_OPEN_LEVEL);
  armed = ALWAYS_ARMED || (readDebounced(PIN_ARM, aS, aL, aT) == LOW);
  alarmOn = armed && windowOpen;

  buzzer(alarmOn);

  if (alarmOn && !lastAlarm) Serial.println("ALERT:WINDOW_OPEN");   // for the ESP8266 later
  lastAlarm = alarmOn;
}

/**
 * Show the alarm or the normal status on the LCD.
 * @return void
 */
void updateLCD() {
  if (alarmOn) { lcdWrite("!! INTRUSION !!", "Window OPEN"); return; }
  char l1[17], l2[17];
  snprintf(l1, 17, "Security:%s", armed ? "ARMED" : "OFF");
  snprintf(l2, 17, "Window:  %s", windowOpen ? "OPEN" : "CLOSED");
  lcdWrite(l1, l2);
}

/**
 * Configure pins and start the LCD and serial port.
 * @return void
 */
void setup() {
  pinMode(PIN_REED, INPUT_PULLUP);
  pinMode(PIN_ARM, INPUT_PULLUP);
  pinMode(PIN_BUZZER, OUTPUT);
  Serial.begin(9600);
  lcd.init();
  lcd.backlight();
  lcdWrite("  SMART HOME", "  MCT331s Team");
  delay(1500);
}

/**
 * Main loop: read the sensors, drive the buzzer, update the screen.
 * @return void
 */
void loop() {
  updateSecurity();
  updateLCD();
}