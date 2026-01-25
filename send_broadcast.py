import socket
import time

def main():
    BROADCAST_IP = "255.255.255.255"
    PORT = 37020

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    while True:
        message = b"Hello i am brodcasting this test data"
        sock.sendto(message, (BROADCAST_IP,PORT))
        print("Broadcast is sent")
        time.sleep(1)

if __name__ == "__main__":
    main()

