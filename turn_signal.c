// Turn Signal ECU: receives commands on 0x100, flashes the lamps, sends its status on 0x101.
#include <stdio.h>
#include <string.h>
#include <time.h>

#include "can_bus.h"

enum { OFF, LEFT, RIGHT, HAZARD };
enum { FAULT_TIMEOUT = 1, FAULT_INVALID_CMD = 2, FAULT_BAD_DLC = 4 };

static uint64_t now_ms(void) {
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    return ts.tv_sec * 1000ull + ts.tv_nsec / 1000000;
}

int main(void) {
    if (!can_open()) {
        puts("cannot connect to the hub");
        return 1;
    }
    uint8_t state = OFF, faults = 0;
    uint64_t cycle_start = now_ms(), last_cmd = cycle_start, last_send = 0;
    CanFrame last = { 0 }, rx;

    for (;;) {
        uint64_t now = now_ms();
        if (now - last_cmd >= 500) { // safe state
            state = OFF;
            faults |= FAULT_TIMEOUT;
        }

        // Status: on change and at least every 100 ms. Lamps: 400 ms on, 400 ms off.
        bool on = (now - cycle_start) / 400 % 2 == 0;
        bool left = on && (state == LEFT || state == HAZARD);
        bool right = on && (state == RIGHT || state == HAZARD);
        CanFrame status = { .id = 0x101, .dlc = 8, .data = { left, right, state, faults } };
        bool changed = memcmp(&status, &last, sizeof status) != 0;
        if (changed || now - last_send >= 100) {
            can_send(&status);
            last = status;
            last_send = now;
        }
        if (changed) printf("left=%d right=%d state=%d faults=%d\n", left, right, state, faults);

        if (!can_receive(&rx, 5) || rx.id != 0x100) continue;
        if (rx.dlc != 8) {
            faults |= FAULT_BAD_DLC;
        } else if (rx.data[0] > HAZARD) {
            faults |= FAULT_INVALID_CMD;
        } else {
            last_cmd = now_ms();
            faults = 0;
            if (rx.data[0] != state) { // a new state starts its flash cycle with the lamp on
                state = rx.data[0];
                cycle_start = last_cmd;
            }
        }
    }
}
