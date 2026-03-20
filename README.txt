AMBULANCE PRIORITY TRAFFIC SIGNAL
TN-IMPACT 2026 | TNI26165 | SRIT
Classes: car + ambulance
==============================================================

FOLDER STRUCTURE
----------------
traffic_project/
│
├── requirements.txt                  ← install all packages
│
├── arduino/
│   └── traffic_signal.ino            ← upload to Arduino IDE
│
├── dataset/
│   ├── data.yaml                     ← 2 classes: car + ambulance
│   ├── images/
│   │   ├── train/                    ← training images here
│   │   └── val/                      ← validation images here
│   └── labels/
│       ├── train/                    ← YOLO .txt labels here
│       └── val/
│
├── training/
│   ├── train.py                      ← run ONCE to train model
│   └── runs/train/ambulance_model/
│       └── weights/
│           └── best.pt               ← PUT YOUR best.pt HERE
│
├── detection/
│   └── detector.py                   ← MAIN PROGRAM (run daily)
│
└── docs/
    └── README.txt                    ← this file


STEPS TO RUN
------------

1. pip install -r requirements.txt

2. Wire Arduino:
   Pin 2→RED  Pin 3→YEL  Pin 4→GRN   (Lane 1)
   Pin 5→RED  Pin 6→YEL  Pin 7→GRN   (Lane 2)
   All LED minus legs → GND
   Each LED has a 220Ω resistor in series

3. Upload arduino/traffic_signal.ino to Arduino IDE

4. Copy your dataset into dataset/images/ and dataset/labels/
   (skip if you already have best.pt)

5. cd training && python train.py
   (skip if you already have best.pt — just place it in weights/)

6. Edit detection/detector.py:
   - Set SERIAL_PORT to your Arduino COM port
   - Set MODEL_PATH to your best.pt location

7. cd detection && python detector.py


PRIORITY ORDER
--------------
Ambulance in Lane 1 only    → Lane 1 GREEN
Ambulance in Lane 2 only    → Lane 2 GREEN
Ambulance in both lanes     → Lane 1 wins
Car only in Lane 1          → Lane 1 GREEN
Car only in Lane 2          → Lane 2 GREEN
More cars in Lane 1         → Lane 1 GREEN
More cars in Lane 2         → Lane 2 GREEN
Equal / nothing detected    → No change
