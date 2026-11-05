"""Virtual CAN bus: sends each frame to all other nodes."""
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 47100))
nodes = set()
while True:
    try:
        packet, sender = sock.recvfrom(16)
    except ConnectionResetError:  # Windows reports a node that has exited
        continue
    nodes.add(sender)
    if len(packet) == 16:
        for node in nodes - {sender}:
            sock.sendto(packet, node)
