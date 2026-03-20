import time
from python.arduino_serial import send_signal
from utils.config import GREEN_TIME


def control_signal(lane1_count, lane2_count, amb1, amb2):

    print("Decision Engine Running")

    # 🚑 Ambulance priority
    if amb1:
        print("🚑 Ambulance in Lane-1")
        send_signal('A')
        return

    if amb2:
        print("🚑 Ambulance in Lane-2")
        send_signal('C')
        return

    # 🚫 No vehicles
    if lane1_count == 0 and lane2_count == 0:
        print("🚫 No Vehicles → Both RED")
        send_signal('Z')
        return

    # 🚗 Density comparison
    if lane1_count > lane2_count:
        print("Lane-1 GREEN")
        send_signal('A')
        time.sleep(GREEN_TIME)

    elif lane2_count > lane1_count:
        print("Lane-2 GREEN")
        send_signal('C')
        time.sleep(GREEN_TIME)

    else:
        print("Equal Density → Alternate")
        send_signal('A')
        time.sleep(15)
        send_signal('C')
        time.sleep(15)