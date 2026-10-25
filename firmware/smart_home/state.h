/**
 * state.h - the shared "whiteboard" of the system.
 *
 * Every module WRITES its own fields here and the display READS all of them.
 * Modules never talk to each other directly, they only go through this state.
 */
#pragma once
#include <Arduino.h>

struct SystemState {
  // security
  bool armed      = false;   // security mode on?
  bool windowOpen = false;   // MC-38 says the window is open?
  bool alarmOn    = false;   // alarm active (armed AND window open)

  // next systems will add their fields here, e.g.:
  // bool  doorOpen = false;
  // bool  lightOn  = false;
  // float tempC    = 0;
  // bool  fanOn    = false;
};

extern SystemState sys;      // the one shared instance (defined in smart_home.ino)
