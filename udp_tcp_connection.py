import socket
import threading

def main():

    PORT = 6002

    def handle_tcp(addr,port, mode="Recv"):

        tcp_sock = socket.socket(AF_INET, socket.SOCK_STREAM )
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
       udp_sock = socket.socket(AF_INET, socket.SOCK_DGRAM)
       udp_sock.bind(("0.0.0.0",PORT))

       print("Listening on port:",PORT)

       while True:
            data,addr = udp_sock.recvfrom(4096)
            print(f"Recieved data from addr {addr} and data is {data.decode()}")
            tcp_port = int(data.decode().split("Port=")[1])

            ans = str(input(f"Do you want to connect to {addr}: (y/n)")).lower()

            if ans == "y":
                handle_tcp(addr,tcp_port,"Recv")
            
                
