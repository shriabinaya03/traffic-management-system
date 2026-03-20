import serial
import time
from utils.config import SERIAL_PORT

ser = None

try:
    ser = serial.Serial(SERIAL_PORT, 9600)
    time.sleep(2)
    print("✅ Arduino Connected")
except Exception as e:
    print("❌ Arduino Connection Failed:", e)


def send_signal(data):
    if ser:
        ser.write(data.encode())
        print("📡 Signal Sent:", data)