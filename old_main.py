import socket, threading
import time


def main():

    PORT = 37020

    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def handle_tcp_connection(conn, udp_connc):
        def recv_conn():
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print(f"peer: {data.decode()}")
                udp_connc.close()

        threading.Thread(target=recv_conn, daemon=True).start()
        while True:
            msg = input("> ")
            conn.sendall(msg.encode())

    def tcp_server():
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.bind(("0.0.0.0", 6001))
        tcp.listen()
        print("TCP listening on 6001")

        while True:
            conn, addr = tcp.accept()
            print(f"TCP connected form {addr}")
            handle_tcp_connection(conn)

    threading.Thread(target=tcp_server, daemon=True).start()

    my_ip = get_ip()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))

    print("Listening to the brodcast for new messages.....")

    while True:
        data, addr = sock.recvfrom(4096)
        print(f"Recieved data from {addr}: {data.decode()}")
        sender_ip = addr[0]
        if sender_ip == my_ip:
            print(f"Both have the same IP addr: {sender_ip}")
            continue
        tcp_port = int(data.decode().split("Port=")[1])
        tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp.connect((sender_ip, tcp_port))
        handle_tcp_connection(tcp,sock)


if __name__ == "__main__":
    main()
