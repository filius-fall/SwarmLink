import socket
import time

def main():
   
    
    PORT = 37020

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    
    print("Listening to the brodcast for new messages.....")
    
    while True:
        data, addr = sock.recvfrom(4096)
        print(f"Recieved data from {addr}: {data.decode()}") 


if __name__ == "__main__":
    main()
