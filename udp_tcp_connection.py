import socket
import threading

def main():

    UDP_PORT = 6002
    BROADCAST_IP = "255.255.255.255"
    TCP_PORT = 5002

    def get_ip():
        s = socket.socket(socket.socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip

    def handle_tcp(addr,port, mode="Recv"):

        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM )
        tcp.connect((addr,port))

        def recv_conn():
            while True:
                data = tcp_sock.recv(1024)
                if not data:
                    print("No data recieved from TCP connection")
                    break
                print("TCP recieved data is:",data.decode())
        def send_data(message="Hello test message"):
            tcp_sock.sendall(message.encode())

        if mode == "Recv":
            threading.Thread(target=recv_conn, daemon=True).start()

        else:
            msg = input("Sender:> ")
            send_data(msg)

    
    def udp_listen_server():
       udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       udp_sock.bind(("0.0.0.0",UDP_PORT))

       print("Listening on port:",UDP_PORT)

       while True:
            data,addr = udp_sock.recvfrom(4096)
            print(f"Recieved data from addr {addr} and data is {data.decode()}")
            tcp_port = int(data.decode().split("Port=")[1])

            ans = str(input(f"Do you want to connect to {addr}: (y/n)")).lower()

            if ans == "y":
                handle_tcp(addr,tcp_port,"Recv")
                
    threading.Thread(target=udp_listen_server, daemon=True).start()

    def udp_send_server(message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        ip = get_ip()

        udp_message = f"Sending Message|Port={TCP_PORT}".encode()

        while True:
            sock.sendto(udp_message,(BROADCAST_IP,UDP_PORT))
            print(f"Broadcast is being done on {UDP_PORT}")
            time.sleep(10)

    udp_send_server()
            
                

if __name__ == "__main__":
    main()