/**
 * security.h - window alarm: MC-38 sensor + ARM toggle + buzzer.
 *
 * Rule: alarmOn = armed AND windowOpen.
 *   window opens while armed -> buzzer ON (continuous) + "ALERT:WINDOW_OPEN" sent once
 *   window closes            -> buzzer OFF at once
 */
#pragma once

/**
 * Set up the sensor, toggle and buzzer pins.
 * @return void
 */
void securityBegin();

/**
 * Read the inputs, update sys.armed / sys.windowOpen / sys.alarmOn and drive the buzzer.
 * Call it every loop; it never blocks.
 * @return void
 */
void securityUpdate();
