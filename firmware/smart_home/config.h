/**
 * config.h - every pin number and setting in ONE place.
 *
 * Change a pin here and the whole program follows.
 * Pin map for the full house: docs/pin_map.md
 */
#pragma once
#include <Arduino.h>

// ================= display =================
const uint8_t LCD_ADDR = 0x27;          // I2C address found by firmware/tests/i2c_scanner
const uint8_t LCD_COLS = 16;
const uint8_t LCD_ROWS = 2;

// ================= security =================
const uint8_t PIN_REED   = 2;           // MC-38 window sensor -> D2 + GND
const uint8_t PIN_ARM    = 7;           // ARM toggle: middle leg -> D7, side leg -> GND
const uint8_t PIN_BUZZER = 8;           // buzzer + -> D8, - -> GND

const bool    ALWAYS_ARMED    = true;   // true = bench test without the toggle; false when the toggle is wired
const uint8_t REED_OPEN_LEVEL = HIGH;   // window open reads HIGH (INPUT_PULLUP); set LOW if it shows reversed
const unsigned int BUZZ_HZ    = 2500;   // buzzer tone frequency (Hz)

// ================= general =================
const unsigned long DEBOUNCE_MS = 30;   // a switch must stay stable this long to count
const unsigned long SERIAL_BAUD = 9600; // Serial Monitor / ESP8266 speed

// ================= next systems (reserved) =================
// const uint8_t PIN_PIR        = 3;    // PIR motion sensor
// const uint8_t PIN_DHT        = 4;    // DHT11
// const uint8_t PIN_FAN        = 5;    // fan driver (TIP120 base via 1k)
// const uint8_t PIN_BTN_LIGHT  = 6;    // light override button
// const uint8_t PIN_SERVO      = 9;    // door servo SG90
// const uint8_t PIN_LED_EXT    = 10;   // exterior light
// const uint8_t PIN_LED_IN     = 11;   // indoor LEDs
// const uint8_t PIN_BTN_MUTE   = 12;   // alarm mute button
// const uint8_t PIN_LDR        = A0;   // light sensor
// const uint8_t PIN_POT        = A1;   // fan set-point knob
