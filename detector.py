# ==============================================================
# FILE     : detector.py
# PURPOSE  : Real-time webcam detection + Arduino signal control
# PROJECT  : Ambulance Priority Traffic Signal
# CLASSES  : car (class 0)  +  ambulance (class 1)
# TEAM     : TNI26165 | TN-IMPACT 2026 | SRIT
# ==============================================================
#
# WHAT THIS SCRIPT DOES (every frame):
# -------------------------------------
#   1. Opens webcam
#   2. Splits frame → LEFT = Lane 1   RIGHT = Lane 2
#   3. Runs YOLOv8 on both halves
#   4. Detects car and ambulance in each lane
#   5. Decides which lane gets GREEN using priority rules
#   6. Sends GREEN:1 or GREEN:2 to Arduino via USB
#   7. Arduino switches LEDs instantly
#   8. Shows result on screen
#   9. Repeat
#
# PRIORITY RULES:
# ---------------
#   Rule 1 → Ambulance in Lane 1 only       → Lane 1 GREEN
#   Rule 2 → Ambulance in Lane 2 only       → Lane 2 GREEN
#   Rule 3 → Ambulance in both lanes        → Lane 1 wins
#   Rule 4 → Car only in Lane 1             → Lane 1 GREEN
#   Rule 5 → Car only in Lane 2             → Lane 2 GREEN
#   Rule 6 → Cars in both, Lane 1 has more  → Lane 1 GREEN
#   Rule 7 → Cars in both, Lane 2 has more  → Lane 2 GREEN
#   Rule 8 → Equal / nothing detected       → No change
#
# HOW TO RUN:
# -----------
#   Step 1 → Edit SERIAL_PORT to your Arduino COM port
#   Step 2 → Edit MODEL_PATH to where your best.pt is saved
#   Step 3 → Open terminal inside detection folder
#   Step 4 → python detector.py
#
# INSTALL PACKAGES (run once):
#   pip install ultralytics opencv-python pyserial
# ==============================================================


# ── IMPORTS ───────────────────────────────────────────────────
import cv2                    # webcam capture + drawing boxes on screen
import serial                 # USB serial communication with Arduino
import time                   # sleep/delays
import sys                    # exit program on error
from pathlib import Path      # check if best.pt file exists
from ultralytics import YOLO  # YOLOv8 model for detection


# ==============================================================
#  SETTINGS — ✏️ EDIT THESE 3 LINES BEFORE RUNNING
# ==============================================================

# Full path to your trained best.pt model file
# If you placed best.pt inside training/runs/train/ambulance_model/weights/
MODEL_PATH = "../training/runs/train/ambulance_model/weights/best.pt"

# Your Arduino USB port
#   Windows → open Device Manager → Ports → look for COM number (e.g. COM3, COM4)
#   Linux   → /dev/ttyUSB0  or  /dev/ttyACM0
#   Mac     → /dev/cu.usbmodem...
SERIAL_PORT = "COM3"

# Camera to use
#   0 = built-in laptop webcam
#   1 = external USB webcam
CAMERA_INDEX = 0


# ==============================================================
#  CONSTANTS — do not change these
# ==============================================================

# Serial baud rate — must be same as Arduino Serial.begin(9600)
BAUD_RATE = 9600

# YOLO minimum confidence
# 0.45 means YOLO must be 45% sure before counting a detection
# Lower this (e.g. 0.3) if detections are being missed
# Raise this (e.g. 0.6) if you are getting false detections
CONFIDENCE_THRESHOLD = 0.45

# How many frames in a row a detection must appear before we trust it
# This stops a single blurry/wrong frame from triggering the signal
STABLE_FRAMES_NEEDED = 2

# Class names — must exactly match what you typed in your annotation tool
# and must match the names order in data.yaml
CLASS_CAR       = "car"        # class 0
CLASS_AMBULANCE = "ambulance"  # class 1

# List of all vehicle classes the model should look for
ALL_VEHICLE_CLASSES = [CLASS_CAR, CLASS_AMBULANCE]


# ==============================================================
#  FUNCTION: connect_arduino
#  Connects to Arduino over USB serial
#  Returns: serial object if Arduino found, None if not found
# ==============================================================
def connect_arduino(port, baud):

    try:
        # Try opening the serial port
        arduino = serial.Serial(port, baud, timeout=1)

        # Arduino resets when serial opens — wait 2 sec for it to reboot
        time.sleep(2)

        # Read the READY message Arduino prints on boot
        if arduino.in_waiting:
            boot_msg = arduino.readline().decode(errors='ignore').strip()
            print(f"  [Arduino boot message] {boot_msg}")

        print(f"  [OK] Arduino connected on port {port}")
        return arduino   # return the open serial connection

    except serial.SerialException as e:
        # Arduino not plugged in or wrong port — run without hardware
        print(f"  [WARNING] Arduino not found on {port}")
        print(f"  [REASON]  {e}")
        print("  [INFO] Running in SIMULATION MODE")
        print("  [INFO] Commands will print to console instead of Arduino")
        return None      # return None so rest of code knows no hardware


# ==============================================================
#  FUNCTION: send_to_arduino
#  Sends a command string to Arduino
#  Only sends if command changed from last time (avoids flooding)
#  Returns: the command that was sent (used to track last command)
# ==============================================================
def send_to_arduino(arduino, command, last_command):

    # If same command as last frame — do nothing, no need to repeat
    if command == last_command:
        return last_command

    # Arduino is connected — send the command
    if arduino:
        try:
            # Arduino reads until newline \n — so we add \n at the end
            arduino.write((command + "\n").encode())

            # Wait a tiny bit then read the acknowledgement from Arduino
            time.sleep(0.02)
            if arduino.in_waiting:
                ack = arduino.readline().decode(errors='ignore').strip()
                print(f"  [Arduino replied] {ack}")

        except serial.SerialException as e:
            print(f"  [ERROR] Failed to send to Arduino: {e}")

    else:
        # No Arduino — simulation mode, just print the command
        print(f"  [SIMULATION] Would send to Arduino: {command}")

    # Return the command so caller can store it as last_command
    return command


# ==============================================================
#  FUNCTION: decide_which_lane
#  Applies the 8 priority rules to decide which lane gets GREEN
#
#  Parameters:
#    lane_data    → dict with detection info for lane 1 and lane 2
#    current_lane → which lane is currently green (1 or 2)
#
#  Returns:
#    command      → what to send to Arduino
#    lane_number  → which lane is now green
# ==============================================================
def decide_which_lane(lane_data, current_lane):

    # Read detection results from both lanes
    amb_in_lane1   = lane_data[1]["has_ambulance"]  # True or False
    amb_in_lane2   = lane_data[2]["has_ambulance"]  # True or False
    count_in_lane1 = lane_data[1]["vehicle_count"]  # number of vehicles (int)
    count_in_lane2 = lane_data[2]["vehicle_count"]  # number of vehicles (int)

    # Rule 1 — ambulance ONLY in lane 1 (not in lane 2)
    # Ambulance always has highest priority
    if amb_in_lane1 and not amb_in_lane2:
        return "GREEN:1", 1

    # Rule 2 — ambulance ONLY in lane 2 (not in lane 1)
    if amb_in_lane2 and not amb_in_lane1:
        return "GREEN:2", 2

    # Rule 3 — ambulance in BOTH lanes at same time
    # Lane 1 wins by default as tie-break
    if amb_in_lane1 and amb_in_lane2:
        return "GREEN:1", 1

    # Rule 4 — cars detected ONLY in lane 1, lane 2 is empty
    if count_in_lane1 > 0 and count_in_lane2 == 0:
        return "GREEN:1", 1

    # Rule 5 — cars detected ONLY in lane 2, lane 1 is empty
    if count_in_lane2 > 0 and count_in_lane1 == 0:
        return "GREEN:2", 2

    # Rule 6 — cars in BOTH lanes, but lane 1 has more cars
    if count_in_lane1 > 0 and count_in_lane2 > 0 and count_in_lane1 > count_in_lane2:
        return "GREEN:1", 1

    # Rule 7 — cars in BOTH lanes, but lane 2 has more cars
    if count_in_lane1 > 0 and count_in_lane2 > 0 and count_in_lane2 > count_in_lane1:
        return "GREEN:2", 2

    # Rule 8a — equal cars in both lanes — keep current green, no change
    if count_in_lane1 > 0 and count_in_lane2 > 0:
        return "HOLD", current_lane

    # Rule 8b — nothing detected in either lane — keep current green, no change
    return "CLEAR", current_lane


# ==============================================================
#  FUNCTION: run_yolo_on_lane
#  Runs YOLO on one lane image and returns detection results
#
#  Parameters:
#    model          → loaded YOLO model
#    lane_frame     → cropped image (half of webcam frame)
#    lane_id        → 1 or 2
#    stable_tracker → shared dict tracking frame counts per detection
#
#  Returns:
#    dict with has_ambulance (bool), vehicle_count (int), boxes (list)
# ==============================================================
def run_yolo_on_lane(model, lane_frame, lane_id, stable_tracker):

    # Start with empty results for this lane
    lane_result = {
        "has_ambulance" : False,   # will be set True if ambulance confirmed
        "vehicle_count" : 0,       # confirmed vehicles count
        "boxes"         : []       # bounding boxes for drawing on screen
    }

    # Run YOLO inference on this lane's image
    yolo_output = model(lane_frame, conf=CONFIDENCE_THRESHOLD, verbose=False)

    # Track which classes appeared in this frame (used to reset lost detections)
    classes_seen_this_frame = set()

    # Loop through every detection YOLO found
    for result in yolo_output:
        for box in result.boxes:

            # Get the class id number (0=car, 1=ambulance)
            class_id = int(box.cls[0])

            # Convert class id to class name string using model's name map
            class_name = model.names[class_id].lower()  # e.g. "car" or "ambulance"

            # Get confidence score (how sure YOLO is)
            confidence = float(box.conf[0])

            # Skip if detected class is not in our vehicle list
            # (YOLO may detect other objects if base model was used)
            if class_name not in ALL_VEHICLE_CLASSES:
                continue

            # Add to seen set — this class appeared in this frame
            classes_seen_this_frame.add(class_name)

            # Build unique key for stable counter: (lane, class)
            # e.g. (1, "car") = car detections in lane 1
            key = (lane_id, class_name)

            # First time seeing this key — start counter at 0
            if key not in stable_tracker:
                stable_tracker[key] = 0

            # Increment counter — this class appeared one more frame
            stable_tracker[key] += 1

            # Only count as CONFIRMED after STABLE_FRAMES_NEEDED frames in a row
            # This stops flickering false detections from triggering signal
            if stable_tracker[key] >= STABLE_FRAMES_NEEDED:

                # Count this as a real vehicle
                lane_result["vehicle_count"] += 1

                # Flag lane as having ambulance if class is ambulance
                if class_name == CLASS_AMBULANCE:
                    lane_result["has_ambulance"] = True

                # Save bounding box coordinates for drawing
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                lane_result["boxes"].append({
                    "coords"       : (x1, y1, x2, y2),
                    "label"        : f"{class_name.upper()} {confidence:.2f}",
                    "is_ambulance" : (class_name == CLASS_AMBULANCE)
                })

    # Reset frame counter for any class that was NOT seen this frame
    # e.g. car was detected last frame but not this frame → reset to 0
    for key in list(stable_tracker.keys()):
        key_lane, key_class = key
        if key_lane == lane_id and key_class not in classes_seen_this_frame:
            stable_tracker[key] = 0

    return lane_result


# ==============================================================
#  FUNCTION: draw_on_frame
#  Draws all overlays on the webcam window:
#    - Yellow divider line between lanes
#    - Green/red header bar per lane
#    - Bounding boxes with label around detected vehicles
#    - Bottom status bar showing command + active lane
#
#  Parameters:
#    frame      → current webcam frame (numpy array)
#    lane_data  → detection results for lane 1 and 2
#    green_lane → which lane is currently green (1 or 2)
#    command    → last command sent to Arduino
#
#  Returns: frame with drawings on it
# ==============================================================
def draw_on_frame(frame, lane_data, green_lane, command):

    h, w = frame.shape[:2]   # frame height and width in pixels
    mid  = w // 2            # x position of center divider

    # Draw yellow vertical divider line between the two lanes
    cv2.line(frame, (mid, 0), (mid, h), (0, 255, 255), 2)

    # Draw header bar for Lane 1 and Lane 2
    for lane_id in [1, 2]:

        # Lane 1 starts at x=0, Lane 2 starts at x=mid
        x_start  = 0 if lane_id == 1 else mid

        # Is this lane currently green?
        is_green = (lane_id == green_lane)

        # Detection info for this lane
        has_amb = lane_data[lane_id]["has_ambulance"]
        count   = lane_data[lane_id]["vehicle_count"]

        # Draw colored background bar at top of each lane
        # Dark green if lane is active (green), dark red if lane is stopped (red)
        bar_color = (0, 60, 0) if is_green else (60, 0, 0)
        cv2.rectangle(frame, (x_start, 0), (x_start + mid, 60), bar_color, -1)

        # Write LANE 1 [GREEN] or LANE 2 [RED] label
        signal_text  = "GREEN" if is_green else "RED"
        signal_color = (0, 255, 80) if is_green else (80, 80, 255)
        cv2.putText(
            frame,
            f"LANE {lane_id}  [ {signal_text} ]",
            (x_start + 10, 26),            # position: slightly inside the bar
            cv2.FONT_HERSHEY_SIMPLEX,       # font type
            0.65,                           # font size
            signal_color,                   # font color
            2                               # font thickness
        )

        # Write vehicle count and ambulance alert below the signal text
        if has_amb:
            # Ambulance detected — show bright cyan alert
            info_text  = f"AMBULANCE DETECTED!  Count: {count}"
            info_color = (0, 220, 255)
        else:
            # Normal vehicles — show grey count
            info_text  = f"Cars detected: {count}"
            info_color = (190, 190, 190)

        cv2.putText(
            frame,
            info_text,
            (x_start + 10, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            info_color,
            1
        )

    # Draw bounding boxes around all detected objects
    for lane_id in [1, 2]:

        # Lane 2 boxes must be shifted right because YOLO ran on a
        # cropped image that starts at pixel 0, but Lane 2 starts at mid
        x_offset = 0 if lane_id == 1 else mid

        for b in lane_data[lane_id]["boxes"]:
            x1, y1, x2, y2 = b["coords"]

            # Red box for ambulance, cyan/yellow box for car
            color = (0, 0, 255) if b["is_ambulance"] else (255, 200, 0)

            # Draw rectangle
            cv2.rectangle(
                frame,
                (x1 + x_offset, y1),   # top-left corner
                (x2 + x_offset, y2),   # bottom-right corner
                color, 2               # color, thickness
            )

            # Draw label text above the box
            cv2.putText(
                frame,
                b["label"],                  # e.g. "AMBULANCE 0.87" or "CAR 0.65"
                (x1 + x_offset, y1 - 8),    # just above the box
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                color,
                2
            )

    # Draw bottom status bar showing last command sent to Arduino
    cv2.rectangle(frame, (0, h - 40), (w, h), (15, 15, 15), -1)

    # Green text if a lane is active, grey if holding
    status_color = (0, 230, 80) if "GREEN" in command else (130, 130, 130)

    cv2.putText(
        frame,
        f"COMMAND SENT: {command}     |     Lane {green_lane} is GREEN",
        (10, h - 13),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.54,
        status_color,
        2
    )

    return frame


# ==============================================================
#  MAIN — this is where the program starts
# ==============================================================
def main():

    print("=" * 60)
    print("  AMBULANCE PRIORITY TRAFFIC SIGNAL")
    print("  TN-IMPACT 2026  |  TNI26165  |  SRIT")
    print("  Classes: car  +  ambulance")
    print("=" * 60)

    # ── Step 1: Check model file exists and load it ────────────
    if not Path(MODEL_PATH).exists():
        print(f"\n[ERROR] best.pt not found at this path:")
        print(f"        {MODEL_PATH}")
        print("[FIX]   Update MODEL_PATH at the top of this file")
        print("[FIX]   Make sure best.pt is inside training/runs/train/ambulance_model/weights/")
        sys.exit(1)  # stop program

    print(f"\n[1] Loading YOLO model from:")
    print(f"    {MODEL_PATH}")
    model = YOLO(MODEL_PATH)
    print(f"    Model loaded OK")
    print(f"    Classes in model: {list(model.names.values())}")

    # ── Step 2: Open webcam ────────────────────────────────────
    print(f"\n[2] Opening webcam index {CAMERA_INDEX}...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print(f"    [ERROR] Cannot open webcam index {CAMERA_INDEX}")
        print("    [FIX]   Try changing CAMERA_INDEX = 1 at top of file")
        sys.exit(1)

    # Set webcam resolution to 640x480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    print("    Webcam opened OK")

    # ── Step 3: Connect to Arduino ─────────────────────────────
    print(f"\n[3] Connecting to Arduino on {SERIAL_PORT}...")
    arduino = connect_arduino(SERIAL_PORT, BAUD_RATE)

    # ── Step 4: Set up tracking variables ─────────────────────

    # Which lane is currently green — starts as lane 1 (matches Arduino boot)
    current_green_lane = 1

    # Stores the last command sent — avoids sending duplicate commands
    last_command_sent = ""

    # Tracks how many consecutive frames each (lane, class) was detected
    # Format: { (lane_id, "car"): 3, (lane_id, "ambulance"): 1 }
    stable_tracker = {}

    # ── Ready message ──────────────────────────────────────────
    print("\n[4] Detection is RUNNING!")
    print("-" * 60)
    print("  LEFT  half of webcam window = Lane 1")
    print("  RIGHT half of webcam window = Lane 2")
    print("  Ambulance has highest priority over cars")
    print("  Press Q on the webcam window to quit")
    print("-" * 60 + "\n")

    # ── REAL-TIME DETECTION LOOP ───────────────────────────────
    # This loop runs as fast as possible — one iteration per webcam frame
    while True:

        # Read one frame from the webcam
        ok, frame = cap.read()

        # If webcam fails to give a frame — stop
        if not ok:
            print("[ERROR] Could not read frame from webcam")
            print("[FIX]  Check webcam is plugged in properly")
            break

        # Get frame dimensions
        h, w = frame.shape[:2]
        mid  = w // 2   # center x-pixel = divider between lanes

        # Split the frame into left half (Lane 1) and right half (Lane 2)
        lane1_img = frame[:, :mid]   # all rows, columns 0 to mid = Lane 1
        lane2_img = frame[:, mid:]   # all rows, columns mid to end = Lane 2

        # Run YOLO on Lane 1 image — returns detection results
        lane1_result = run_yolo_on_lane(model, lane1_img, 1, stable_tracker)

        # Run YOLO on Lane 2 image — returns detection results
        lane2_result = run_yolo_on_lane(model, lane2_img, 2, stable_tracker)

        # Combine both results into one dictionary
        all_lane_data = {
            1: lane1_result,
            2: lane2_result
        }

        # Apply priority rules — decide which lane gets GREEN
        command, current_green_lane = decide_which_lane(all_lane_data, current_green_lane)

        # Send command to Arduino only if it changed from last frame
        last_command_sent = send_to_arduino(arduino, command, last_command_sent)

        # Draw lane divider, boxes, labels, and status bar on frame
        frame = draw_on_frame(frame, all_lane_data, current_green_lane, command)

        # Show the annotated frame in a window
        cv2.imshow("Ambulance Priority Signal | TNI26165 | Press Q to quit", frame)

        # Check if user pressed Q key to quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("\n[INFO] Q pressed — quitting...")
            break

    # ── Clean up after loop ends ───────────────────────────────
    cap.release()                # release webcam
    cv2.destroyAllWindows()      # close the display window
    if arduino:
        arduino.close()          # close Arduino serial connection
    print("[DONE] Program closed cleanly.")


# This line makes sure main() only runs when you run this file directly
# (not when it is imported by another file)
if __name__ == "__main__":
    main()
