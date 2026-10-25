/**
 * display.h - 16x2 I2C LCD: shows the state of every module.
 *
 * Priority: alarm screen > status screen.
 */
#pragma once

/**
 * Start the LCD, turn on the backlight and show the welcome screen.
 * @return void
 */
void displayBegin();

/**
 * Redraw the screen from the shared state (only changed lines are rewritten).
 * Call it every loop; it never blocks.
 * @return void
 */
void displayUpdate();
