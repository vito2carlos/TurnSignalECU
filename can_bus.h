// Connection to the virtual CAN bus (vcan_hub.py).
#ifndef CAN_BUS_H
#define CAN_BUS_H

#include <stdbool.h>
#include <stdint.h>

// A frame is sent over UDP exactly as laid out here: 16 bytes, little endian.
typedef struct {
    uint32_t id;
    uint8_t dlc, unused[3], data[8];
} CanFrame;

bool can_open(void);
void can_send(const CanFrame *frame);
bool can_receive(CanFrame *frame, int timeout_ms); // true = a frame arrived

#endif
