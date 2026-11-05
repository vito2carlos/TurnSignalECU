"""Test application: tests the ECU only through the CAN bus. Run: python test_ecu.py"""
import os
import socket
import struct
import subprocess
import sys
import time
import unittest

OFF, LEFT, RIGHT, HAZARD = range(4)
FAULT_TIMEOUT, FAULT_INVALID_CMD, FAULT_BAD_DLC = 1, 2, 4
TOLERANCE = 0.05  # seconds: the bus and the operating system are not real time


def frame(can_id, data, dlc=8):
    return struct.pack("<IB3x8s", can_id, dlc, bytes(data))


class TestEcu(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hub = subprocess.Popen([sys.executable, "vcan_hub.py"])
        time.sleep(0.5)
        cls.bus = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        cls.send(b"HELO")

    @classmethod
    def tearDownClass(cls):
        cls.hub.kill()
        cls.hub.wait()
        cls.bus.close()

    @classmethod
    def send(cls, packet):
        cls.bus.sendto(packet, ("127.0.0.1", 47100))

    def start_node(self, *command, **options):
        node = subprocess.Popen(command, **options)
        self.addCleanup(node.__exit__, None, None, None)  # cleanups run last to first
        self.addCleanup(node.kill)
        return node

    def setUp(self):
        self.start_node(os.path.abspath("turn_signal"), stdout=subprocess.DEVNULL)
        time.sleep(0.2)

    def start_switch(self):
        self.switch = self.start_node(sys.executable, "switch_ecu.py", stdin=subprocess.PIPE)
        time.sleep(0.3)

    def press(self, key):
        self.switch.stdin.write(key.encode() + b"\n")
        self.switch.stdin.flush()

    def read_status(self, seconds):
        """Returns (time, left, right, state, faults) of each status frame in this period."""
        statuses, end = [], time.time() + seconds
        while time.time() < end:
            self.bus.settimeout(max(end - time.time(), 0.001))
            try:
                packet, _ = self.bus.recvfrom(16)
            except (TimeoutError, socket.timeout, ConnectionResetError):
                continue
            can_id, dlc, data = struct.unpack("<IB3x8s", packet)
            if can_id == 0x101:
                self.assertEqual(dlc, 8)
                statuses.append((time.time(), *data[:4]))
        return statuses

    def check_flashing(self, key, state, left, right):
        self.start_switch()
        self.press(key)
        self.read_status(0.1)
        statuses = self.read_status(2)
        for _, l, r, s, faults in statuses:
            self.assertEqual((s, faults), (state, 0))
            self.assertEqual((l if left else 0, r if right else 0), (l, r))  # other lamp off
            if left and right:
                self.assertEqual(l, r)
        gaps = [b[0] - a[0] for a, b in zip(statuses, statuses[1:])]
        self.assertLess(max(gaps), 0.1 + TOLERANCE)  # status at least every 100 ms
        lamp = 1 if left else 2
        changes = [b[0] for a, b in zip(statuses, statuses[1:]) if a[lamp] != b[lamp]]
        self.assertGreaterEqual(len(changes), 4)
        for a, b in zip(changes, changes[1:]):
            self.assertAlmostEqual(b - a, 0.4, delta=TOLERANCE)

    def test_left_flashes_left_lamp(self):
        self.check_flashing("l", LEFT, True, False)

    def test_right_flashes_right_lamp(self):
        self.check_flashing("r", RIGHT, False, True)

    def test_hazard_flashes_both_lamps_together(self):
        self.check_flashing("h", HAZARD, True, True)

    def test_off_switches_lamps_off(self):
        self.start_switch()
        self.press("h")
        self.read_status(0.1)
        self.press("o")
        self.read_status(0.1)
        for _, *status in self.read_status(1):
            self.assertEqual(status, [0, 0, OFF, 0])

    def test_lost_switch_goes_to_safe_state_and_recovers(self):
        self.start_switch()
        self.press("l")
        self.read_status(0.1)
        self.switch.kill()
        lost_at = time.time()
        statuses = self.read_status(1)
        safe_at, *status = next(s for s in statuses if s[4] & FAULT_TIMEOUT)
        self.assertEqual(status, [0, 0, OFF, FAULT_TIMEOUT])
        self.assertAlmostEqual(safe_at - lost_at, 0.45, delta=0.05 + TOLERANCE)  # last command 0-100 ms ago
        self.send(frame(0x100, [RIGHT]))
        self.assertEqual(self.read_status(0.1)[-1][1:], (0, 1, RIGHT, 0))

    def test_wrong_frames_do_not_change_the_state(self):
        self.send(frame(0x100, [LEFT]))
        self.send(frame(0x200, [RIGHT]))  # other ID: ignored
        self.assertEqual(self.read_status(0.1)[-1][1:], (1, 0, LEFT, 0))
        self.send(frame(0x100, [RIGHT], dlc=7))
        self.send(frame(0x100, [9]))
        self.assertEqual(self.read_status(0.1)[-1][1:], (1, 0, LEFT, FAULT_BAD_DLC | FAULT_INVALID_CMD))
        self.send(frame(0x100, [LEFT]))  # a valid command clears the faults
        self.assertEqual(self.read_status(0.1)[-1][1:], (1, 0, LEFT, 0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
