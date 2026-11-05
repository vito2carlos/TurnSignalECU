"""Switch ECU: sends 0x100 every 100 ms and on change. Type o, l, r or h, then Enter."""
import socket
import struct
import sys
import threading
import time

COMMANDS = {"o": 0, "l": 1, "r": 2, "h": 3}
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
command = 0


def send():
    frame = struct.pack("<IB3x8s", 0x100, 8, bytes([command]))
    sock.sendto(frame, ("127.0.0.1", 47100))


def send_cyclically():
    while True:
        send()
        time.sleep(0.1)


threading.Thread(target=send_cyclically, daemon=True).start()
for line in sys.stdin:
    command = COMMANDS.get(line.strip(), command)
    send()
