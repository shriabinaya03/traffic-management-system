# Ambulance Priority Traffic Signal System

An intelligent traffic control system that uses computer vision to detect ambulances and vehicle density to optimize signal switching via Arduino.

## 🚀 How It Works
The system processes a real-time webcam feed by splitting the frame into two halves (Lane 1 and Lane 2). Using a custom-trained YOLOv8 model, it identifies cars and ambulances to make split-second signaling decisions.

### Priority Rules:
1. **Ambulance Priority:** Any lane with an ambulance immediately gets a **GREEN** light.
2. **Tie-Breaker:** If ambulances are in both lanes, Lane 1 (Left) takes priority.
3. **Traffic Density:** If no ambulance is present, the lane with more cars gets the **GREEN** light.
4. **Default:** If counts are equal or zero, the signal remains unchanged.

## 🛠️ Hardware Setup
* **Microcontroller:** Arduino Uno
* **Signals:** 6 LEDs (Red, Yellow, Green for two lanes)
* **Circuit:** Pins 2–7 connected via 220Ω resistors.
* **Communication:** Python sends serial data to Arduino via USB.

## 💻 Tech Stack
* **AI/Vision:** Python, OpenCV, Ultralytics YOLOv8
* **Dataset:** Annotated via Roboflow (`best.pt` model)
* **Hardware Control:** Arduino (C++), PySerial

## 📂 Project Structure
* `detector.py` - YOLOv8 detection and logic script.
* `traffic_signal.ino` - Arduino firmware for LED switching.
* `best.pt` - Trained YOLOv8 weights (to be uploaded).
