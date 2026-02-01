import socket
import threading
import time

def main():

    UDP_PORT = 6002
    BROADCAST_IP = "255.255.255.255"
    TCP_LIST_PORT = 5002
    TCP_SEND_PORT = 5003
    UDP_MESSAGE = f"Sending Message|Port={TCP_LIST_PORT}".encode()

    def get_ip():
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip



    def recieve_tcp_conn():
        tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcp_sock.bind(("0.0.0.0", TCP_LIST_PORT))
        tcp_sock.listen()
        print(f"TCP Server Listening on {TCP_LIST_PORT}")

        def handle_client(conn, addr):
            print(f"New connection from {addr}")
            while True:
                try:
                    data = conn.recv(1024)
                    if not data:
                        break
                    print(f"TCP Recieved data from {addr}: {data.decode()}")
                except Exception as e:
                    print(f"Connection error: {e}")
                    break
            conn.close()
            print(f"Connection closed for {addr}")

        while True:
            try:
                conn, addr = tcp_sock.accept()
                threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
            except Exception as e:
                print(f"Accept error: {e}")

    threading.Thread(target=recieve_tcp_conn, daemon=True).start()

    def send_tcp_message(ip, port):
        # Client logic: persistent chat
        try:
            print(f"Connecting to {ip}:{port}...")
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_sock.connect((ip, port))
            print(f"Connected! Type 'exit' to stop.")
            
            while True:
                msg = input(f"Me -> {ip} > ")
                if msg.lower() == 'exit':
                    break
                client_sock.sendall(msg.encode())
                
            client_sock.close()
            print("Chat ended.")
        except Exception as e:
            print(f"Connection ended or failed: {e}")

    
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
                print(f"You will be connecting to addr: {addr} and port: {tcp_port}")
                print(f"You will be connecting to addr: {addr} and port: {tcp_port}")
                # Use the new send function
                send_tcp_message(addr[0], tcp_port)
                
    threading.Thread(target=udp_listen_server, daemon=True).start()

    def udp_send_server(message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        ip = get_ip()

        

        while True:
            sock.sendto(message,(BROADCAST_IP,UDP_PORT))
            print(f"Broadcast is being done on {UDP_PORT}")
            time.sleep(10)

    udp_send_server(UDP_MESSAGE)
            
                

if __name__ == "__main__":
    main()