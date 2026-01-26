import socket, threading
import time


def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
    s.close()

    return ip


def main():
    BROADCAST_IP = "255.255.255.255"
    PORT = 37020
    TCP_PORT = 5002

    def handle_connection(conn, addr):
        print(f"TCP connection accepted: {addr}")
        while True:
       	    data = conn.recv(1024)
       	    if not data:
       	        return
       	    print("peer data is", data.decode()) 
        msg = f"This is message from {my_ip} to {addr}"
        print(msg)
        conn.close()

    def tcp_server():
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(("0.0.0.0", TCP_PORT))
        tcp.listen()
        print(f"Listening to port: {TCP_PORT}")

        while True:
            conn, addr = tcp.accept()

            handle_connection(conn, addr)

    def udp_server():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        while True:
            message = f"Hello|Port=5002".encode()
            sock.sendto(message, (BROADCAST_IP, PORT))
            print("Broadcast is sent")
            time.sleep(2)

    threading.Thread(target=tcp_server, daemon=True).start()
    udp_server()


if __name__ == "__main__":
    main()
