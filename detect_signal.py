import sys
import os
import cv2
import time
from ultralytics import YOLO

# ===== add project root path =====
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from python.decision import control_signal
from utils.config import *

# ===== load model =====
model = YOLO(MODEL_PATH)

# ===== open single camera =====
cam = cv2.VideoCapture(CAMERA_LANE1)

if not cam.isOpened():
    print("❌ Camera Not Detected")
    exit()

print("✅ Traffic AI System Started")

while True:

    ret, frame = cam.read()

    if not ret:
        print("Frame Error")
        break

    # ===== split frame into two lanes =====
    height, width, _ = frame.shape

    lane1_frame = frame[:, :width//2]     # left half
    lane2_frame = frame[:, width//2:]     # right half

    # ===== YOLO detection =====
    res1 = model(lane1_frame, conf=0.4)
    res2 = model(lane2_frame, conf=0.4)

    lane1_count = 0
    lane2_count = 0
    amb1 = False
    amb2 = False

    # ===== lane-1 objects =====
    for box in res1[0].boxes:
        cls = int(box.cls[0])

        if cls == CAR_CLASS_ID:
            lane1_count += 1

        elif cls == AMBULANCE_CLASS_ID:
            amb1 = True

    # ===== lane-2 objects =====
    for box in res2[0].boxes:
        cls = int(box.cls[0])

        if cls == CAR_CLASS_ID:
            lane2_count += 1

        elif cls == AMBULANCE_CLASS_ID:
            amb2 = True

    print(f"Lane1:{lane1_count}  Lane2:{lane2_count}")

    # ===== signal decision =====
    control_signal(lane1_count, lane2_count, amb1, amb2)

    # ===== display =====
    cv2.imshow("Lane-1", res1[0].plot())
    cv2.imshow("Lane-2", res2[0].plot())

    # ===== exit key =====
    if cv2.waitKey(1) & 0xFF == 27:
        break

    time.sleep(1)

cam.release()
cv2.destroyAllWindows()