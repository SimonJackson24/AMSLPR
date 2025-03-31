import socket
import sys

# Create UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(5)

print("Sending broadcast message...")
sock.sendto(b"ONVIF_TEST", ("239.255.255.250", 3702))
print("Waiting for responses...")

try:
    while True:
        data, addr = sock.recvfrom(4096)
        print(f"Received response from {addr[0]}:{addr[1]}")
except socket.timeout:
    print("No more responses")
finally:
    sock.close()
