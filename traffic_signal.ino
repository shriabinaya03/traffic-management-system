/*
==============================================================
  FILE     : traffic_signal.ino
  PROJECT  : Ambulance Priority Traffic Signal
  TEAM     : TNI26165 | TN-IMPACT 2026 | SRIT
==============================================================

  WHAT THIS DOES:
  ---------------
  Controls 6 LEDs (2 traffic signals).
  Receives commands from Python via USB and switches lights.
  No internal timers — Python controls everything in real-time.

  WIRING:
  -------
  Lane 1 (left signal):
    Pin 2  →  220Ω  →  RED    LED (+)
    Pin 3  →  220Ω  →  YELLOW LED (+)
    Pin 4  →  220Ω  →  GREEN  LED (+)

  Lane 2 (right signal):
    Pin 5  →  220Ω  →  RED    LED (+)
    Pin 6  →  220Ω  →  YELLOW LED (+)
    Pin 7  →  220Ω  →  GREEN  LED (+)

  All LED (−) legs → Arduino GND

  COMMANDS FROM PYTHON:
  ----------------------
  "GREEN:1" → Lane 1 GREEN, Lane 2 RED
  "GREEN:2" → Lane 2 GREEN, Lane 1 RED
  "HOLD"    → Keep current lights unchanged
  "CLEAR"   → Keep current lights unchanged

  REPLIES TO PYTHON:
  ------------------
  "READY"      → Sent on boot
  "ACK:GREEN1" → Lane 1 is now green
  "ACK:GREEN2" → Lane 2 is now green
  "ACK:HOLD"   → No change
  "ACK:CLEAR"  → No change
==============================================================
*/

// ── PIN NUMBERS ───────────────────────────────────────────────
const int L1_RED    = 2;
const int L1_YELLOW = 3;
const int L1_GREEN  = 4;

const int L2_RED    = 5;
const int L2_YELLOW = 6;
const int L2_GREEN  = 7;


// ── SETUP — runs once on power-on ────────────────────────────
void setup() {

  // Set all 6 LED pins as output
  pinMode(L1_RED,    OUTPUT);
  pinMode(L1_YELLOW, OUTPUT);
  pinMode(L1_GREEN,  OUTPUT);
  pinMode(L2_RED,    OUTPUT);
  pinMode(L2_YELLOW, OUTPUT);
  pinMode(L2_GREEN,  OUTPUT);

  // Start serial at 9600 — must match Python BAUD_RATE = 9600
  Serial.begin(9600);

  // Default state: Lane 1 GREEN, Lane 2 RED
  setLane1Green();

  // Tell Python we are ready to receive commands
  Serial.println("READY");
}


// ── LOOP — runs forever ───────────────────────────────────────
void loop() {

  // Wait for a command from Python over USB
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();           // Remove spaces/newline characters
    processCommand(cmd);  // Handle the command
  }

  // No timers or delays here — Arduino only reacts to Python
}


// ── PROCESS COMMAND ───────────────────────────────────────────
void processCommand(String cmd) {

  if (cmd == "GREEN:1") {
    // Car or ambulance detected in Lane 1 with priority
    setLane1Green();
    Serial.println("ACK:GREEN1");
  }
  else if (cmd == "GREEN:2") {
    // Car or ambulance detected in Lane 2 with priority
    setLane2Green();
    Serial.println("ACK:GREEN2");
  }
  else if (cmd == "HOLD") {
    // Equal vehicles in both lanes — no change
    Serial.println("ACK:HOLD");
  }
  else if (cmd == "CLEAR") {
    // Nothing detected — no change
    Serial.println("ACK:CLEAR");
  }
}


// ── LED CONTROL FUNCTIONS ─────────────────────────────────────

void allOff() {
  // Turn every LED off before switching state
  digitalWrite(L1_RED,    LOW);
  digitalWrite(L1_YELLOW, LOW);
  digitalWrite(L1_GREEN,  LOW);
  digitalWrite(L2_RED,    LOW);
  digitalWrite(L2_YELLOW, LOW);
  digitalWrite(L2_GREEN,  LOW);
}

void setLane1Green() {
  allOff();
  digitalWrite(L1_GREEN, HIGH);  // Lane 1 → GREEN
  digitalWrite(L2_RED,   HIGH);  // Lane 2 → RED
}

void setLane2Green() {
  allOff();
  digitalWrite(L2_GREEN, HIGH);  // Lane 2 → GREEN
  digitalWrite(L1_RED,   HIGH);  // Lane 1 → RED
}
