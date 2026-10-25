"""
runDevice.py - send one command to a smart-home device.

Usage:  python runDevice.py <target_mac> <command_code>

Writes "MAC|CODE\n" over USB serial (/dev/ttyACM0, 115200 baud) to the ESP32
"antenna", which forwards it to the target device via ESP-NOW.
MAC addresses and command codes are defined in Protocol.json.
AI.py starts this script as a subprocess for each device action.
"""

import serial
import time,sys
import json
# Replace with your actual USB port (e.g., 'COM3' on Windows or '/dev/ttyUSB0' on Linux/Mac)
PORT = '/dev/ttyACM0'
BAUD_RATE = 115200


# Initialize Serial Connection to the ESP32 Antenna
try:
    bridge = serial.Serial(PORT, BAUD_RATE, timeout=1)
    time.sleep(2) # Give the ESP32 a moment to reboot after opening the serial port
    print(f"Connected to ESP32 Bridge on {PORT}")
except Exception as e:
    print(f"Error opening serial port: {e}")
    exit()

def send_esp_now(target_mac, payload):
    # Format the packet: MAC|PAYLOAD\n
    packet = f"{target_mac}|{payload}\n"
    bridge.write(packet.encode('utf-8'))
    print(f"Sent via USB: {packet.strip()}")


target_mac_address = sys.argv[1]
message = int(sys.argv[2])

send_esp_now(target_mac_address, message)