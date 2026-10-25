/**
 * MCT331s Smart Home - main sketch.
 *
 * This file only wires the modules together:
 *   config.h    pins and settings
 *   state.h     shared system state (the "whiteboard")
 *   debounce.*  clean switch reading
 *   security.*  window alarm (MC-38 + toggle + buzzer)
 *   display.*   16x2 I2C LCD
 *
 * Every module has begin() (runs once) and update() (runs every loop, never blocks).
 * To add a system (door, lighting, climate): create door.h/.cpp with doorBegin()/doorUpdate(),
 * add its fields to state.h, and call it below.
 *
 * Library: LiquidCrystal I2C (Frank de Brabander) - install from the Library Manager.
 */
#include "config.h"
#include "state.h"
#include "security.h"
#include "display.h"

SystemState sys;   // the one shared state

/**
 * Runs once at power-on: start serial and every module.
 * @return void
 */
void setup() {
  Serial.begin(SERIAL_BAUD);
  securityBegin();
  displayBegin();
  delay(1500);     // keep the welcome screen visible (the only delay in the program)
  Serial.println(F("System ready"));
}

/**
 * Runs forever: each module reads its inputs and updates its outputs, then the LCD shows the result.
 * @return void
 */
void loop() {
  securityUpdate();
  // doorUpdate();      // next
  // lightingUpdate();  // next
  // climateUpdate();   // next
  displayUpdate();
}
