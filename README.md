# Turn Signal ECU

A simulated ECU tested only through a virtual CAN bus. It needs `gcc` and `python3`, with no Python packages.

```
Switch ECU (Python)         Turn Signal ECU (C)              Test application (Python)
switch_ecu.py               turn_signal.c, can_bus.c         test_ecu.py
sends 0x100                 receives 0x100, sends 0x101      reads 0x101, sends test frames
every 100 ms + on change    on change + every 100 ms         starts and stops all the nodes
    |                           |                                |
    +---------------------------+--------------------------------+
      vcan_hub.py: virtual CAN bus (UDP hub, port 47100) on WSL2
```

Every node sends its frames to the hub, and the hub sends each frame to all the other nodes.

## Run the tests

```bash
gcc turn_signal.c can_bus.c -o turn_signal
```

```bash
python3 test_ecu.py
```

On Windows without WSL, add `-lws2_32` to the `gcc` command and use `python` instead of `python3`.

## Try it by hand

Run each command in its own terminal, then type `l`, `r`, `h` or `o` and press Enter in the switch terminal.

```bash
python3 vcan_hub.py
```

```bash
./turn_signal
```

```bash
python3 switch_ecu.py
```

## Requirements

- **Command `0x100`, DLC 8:** byte 0 is 0 OFF, 1 LEFT, 2 RIGHT or 3 HAZARD.
- **Status `0x101`, DLC 8:** left lamp, right lamp, state, faults (bit 0 timeout, 1 invalid command, 2 bad DLC). Sent on change and at least every 100 ms.
- **Flashing:** lamps go 400 ms on, 400 ms off. A new state starts with the lamp on.
- **Timeout:** after 500 ms with no valid command, the ECU goes to OFF and sets the timeout fault.
- **Wrong frames:** other IDs are ignored. A wrong DLC or value sets a fault and keeps the state. A valid command clears all faults.
