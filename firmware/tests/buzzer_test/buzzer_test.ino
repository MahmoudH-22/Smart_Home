/**
 * Buzzer test: beeps 0.5 s on / 0.5 s off. Wiring: buzzer + -> D8, - -> GND.
 */
const uint8_t PIN_BUZZER = 8;   // buzzer + leg is on D8

/**
 * Set the buzzer pin as an output.
 * @return void
 */
void setup() {
  pinMode(PIN_BUZZER, OUTPUT);
}

/**
 * Beep: 0.5 s on, 0.5 s off. tone() works for active and passive buzzers.
 * @return void
 */
void loop() {
  tone(PIN_BUZZER, 2500);
  delay(500);
  noTone(PIN_BUZZER);
  delay(500);
}
