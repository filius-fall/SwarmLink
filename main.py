import base64
import socket
import threading
import uuid
from typing import Any

from file_swarm import SharedFileIndex, SwarmDownloader
from peer_discovery import DiscoveryService, PeerRegistry
from tcp_protocol import recv_json_line, send_json_line

TCP_DEFAULT_PORT = 6001


def get_local_ip() -> str:
    """Return this machine's LAN IP used for outgoing connections.

    Why fallback to localhost:
    - Some environments (containers/CI) block outbound routing.
    - We still want the app to start for local testing and command checks.
    """

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


class SwarmLinkNode:
    """Main node object that ties discovery, TCP protocol, chat and file sharing.

    Design note:
    - Discovery and file logic are moved to helper modules for modularity.
    - This class focuses on orchestration and user command flow.
    """

    def __init__(
        self, tcp_port: int = TCP_DEFAULT_PORT, name: str | None = None
    ) -> None:
        self.peer_id = uuid.uuid4().hex[:12]
        self.name = name or socket.gethostname()
        self.tcp_port = tcp_port
        self.host_ip = get_local_ip()

        self.shutdown_event = threading.Event()
        self.peer_registry = PeerRegistry()
        self.file_index = SharedFileIndex()
        self.downloader = SwarmDownloader(self.request_peer)
        self.on_chat_received = None

        self.discovery = DiscoveryService(
            peer_registry=self.peer_registry,
            self_peer_id=self.peer_id,
            self_name=self.name,
            tcp_port=self.tcp_port,
            shutdown_event=self.shutdown_event,
        )

    def start(self) -> None:
        """Start TCP server and UDP discovery services."""

        print(
            f"SwarmLink started as {self.name} ({self.peer_id}) "
            f"on {self.host_ip}:{self.tcp_port}."
        )
        threading.Thread(target=self.tcp_server_loop, daemon=True).start()
        self.discovery.start()

    def tcp_server_loop(self) -> None:
        """Serve incoming TCP requests for chat, file listing, metadata and pieces.

        Why this protocol shape:
        - Simple command-based JSON messages are easy to inspect and debug.
        - Each connection handles one request and one response for predictable flow.
        """

        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", self.tcp_port))
        server.listen()
        server.settimeout(1.0)

        print(f"TCP server listening on {self.host_ip}:{self.tcp_port}")

        while not self.shutdown_event.is_set():
            try:
                conn, addr = server.accept()
                threading.Thread(
                    target=self.handle_tcp_client,
                    args=(conn, addr),
                    daemon=True,
                ).start()
            except socket.timeout:
                continue
            except OSError as exc:
                print(f"TCP accept warning: {exc}")

        server.close()

    def handle_tcp_client(self, conn: socket.socket, addr: tuple[str, int]) -> None:
        """Handle a single inbound TCP request.

        Why one-request-per-connection:
        - Keeps implementation straightforward.
        - Avoids complex state handling and simplifies failure recovery.
        """

        try:
            message = recv_json_line(conn)
            if not message:
                return

            msg_type = message.get("type")

            if msg_type == "CHAT":
                from_name = message.get("from_name", "unknown")
                text = message.get("text", "")
                print(f"\n[CHAT] {from_name}@{addr[0]}: {text}")
                if callable(self.on_chat_received):
                    self.on_chat_received(message, addr)
                send_json_line(conn, {"ok": True})
                return

            if msg_type == "LIST_FILES_REQ":
                files = self.file_index.list_files()
                send_json_line(conn, {"type": "LIST_FILES_RESP", "files": files})
                return

            if msg_type == "FILE_INFO_REQ":
                file_id = message.get("file_id", "")
                info = self.file_index.get_file_info(file_id)
                if not info:
                    send_json_line(conn, {"type": "FILE_INFO_RESP", "found": False})
                    return
                send_json_line(
                    conn, {"type": "FILE_INFO_RESP", "found": True, "file": info}
                )
                return

            if msg_type == "PIECE_REQ":
                file_id = message.get("file_id", "")
                piece_index = int(message.get("piece_index", -1))
                piece_data = self.file_index.read_piece(file_id, piece_index)
                if not piece_data:
                    send_json_line(
                        conn,
                        {
                            "type": "PIECE_RESP",
                            "ok": False,
                            "error": "File not found or piece index out of range",
                        },
                    )
                    return

                raw_piece, piece_hash = piece_data
                send_json_line(
                    conn,
                    {
                        "type": "PIECE_RESP",
                        "ok": True,
                        "file_id": file_id,
                        "piece_index": piece_index,
                        "piece_hash": piece_hash,
                        "data": base64.b64encode(raw_piece).decode("utf-8"),
                    },
                )
                return

            send_json_line(conn, {"ok": False, "error": "Unknown message type"})
        except Exception as exc:  # noqa: BLE001
            print(f"TCP handler warning from {addr}: {exc}")
        finally:
            conn.close()

    def request_peer(self, peer, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Send a single TCP request to peer and wait for one response."""

        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.settimeout(8)
        try:
            conn.connect((peer.ip, peer.tcp_port))
            send_json_line(conn, payload)
            return recv_json_line(conn)
        except OSError:
            return None
        finally:
            conn.close()

    def list_peers(self) -> None:
        """Print discovered peers with age of last announce."""

        peers = self.peer_registry.list_all()
        if not peers:
            print("No peers discovered yet.")
            return

        import time

        for peer in peers:
            age_seconds = int(time.time() - peer.last_seen)
            print(
                f"{peer.peer_id} | {peer.name} | {peer.ip}:{peer.tcp_port} | "
                f"last_seen={age_seconds}s"
            )

    def send_chat(self, peer_id: str, text: str) -> None:
        """Send a chat message to one peer by peer_id."""

        peer = self.peer_registry.get(peer_id)
        if not peer:
            print(f"Unknown peer id: {peer_id}")
            return

        response = self.request_peer(
            peer,
            {
                "type": "CHAT",
                "from_peer_id": self.peer_id,
                "from_name": self.name,
                "text": text,
            },
        )
        if response and response.get("ok"):
            print(f"Message sent to {peer.name} ({peer.peer_id})")
        else:
            print(f"Failed to send message to {peer.peer_id}")

    def share_file(self, file_path: str) -> None:
        """Index a local file so peers can discover and download it in pieces."""

        metadata = self.file_index.share_file(file_path)
        if not metadata:
            print(f"Invalid file path: {file_path}")
            return

        print(
            f"Shared: {metadata['name']} | file_id={metadata['file_id']} | "
            f"pieces={len(metadata['piece_hashes'])}"
        )

    def list_my_files(self) -> None:
        """Print the files this peer is currently sharing."""

        files = self.file_index.list_files()
        if not files:
            print("No files shared yet. Use /share <path>.")
            return

        for item in files:
            print(
                f"{item['file_id']} | {item['name']} | {item['size']} bytes | "
                f"pieces={item['piece_count']}"
            )

    def find_files(self, query: str) -> list[dict[str, Any]]:
        """Search files on discovered peers by substring in name or file_id."""

        query_lower = query.lower()
        matches: list[dict[str, Any]] = []

        peers = self.peer_registry.list_all()
        for peer in peers:
            response = self.request_peer(peer, {"type": "LIST_FILES_REQ"})
            if not response or response.get("type") != "LIST_FILES_RESP":
                continue

            for file_entry in response.get("files", []):
                if (
                    query_lower in file_entry.get("name", "").lower()
                    or query_lower in file_entry.get("file_id", "").lower()
                ):
                    matches.append(
                        {
                            "peer_id": peer.peer_id,
                            "peer_name": peer.name,
                            "ip": peer.ip,
                            **file_entry,
                        }
                    )

        return matches

    def download_file(self, file_id: str, output_path: str | None) -> None:
        """Download a file from all available seeders in parallel pieces."""

        peers = self.peer_registry.list_all()
        ok, message = self.downloader.download(file_id, peers, output_path)
        print(message)
        if ok:
            # Optionally auto-share freshly downloaded file in future,
            # but currently we keep behavior explicit for user control.
            return

    def run_cli(self) -> None:
        """Interactive command loop.

        Kept intentionally straightforward and close to your original coding style
        so it remains easy to modify while adding new commands.
        """

        print("Type /help for commands.")

        while not self.shutdown_event.is_set():
            try:
                command = input("swarm> ").strip()
            except (EOFError, KeyboardInterrupt):
                command = "/quit"

            if not command:
                continue

            if command == "/help":
                print("""
Commands:
  /help
  /peers
  /chat <peer_id> <message>
  /share <file_path>
  /myfiles
  /find <name-or-file_id>
  /download <file_id> [output_path]
  /quit
""")
                continue

            if command == "/peers":
                self.list_peers()
                continue

            if command.startswith("/chat "):
                parts = command.split(" ", 2)
                if len(parts) < 3:
                    print("Usage: /chat <peer_id> <message>")
                    continue
                self.send_chat(parts[1], parts[2])
                continue

            if command.startswith("/share "):
                file_path = command.split(" ", 1)[1].strip()
                self.share_file(file_path)
                continue

            if command == "/myfiles":
                self.list_my_files()
                continue

            if command.startswith("/find "):
                query = command.split(" ", 1)[1].strip()
                matches = self.find_files(query)
                if not matches:
                    print("No matching files found on discovered peers.")
                    continue

                for item in matches:
                    print(
                        f"{item['file_id']} | {item['name']} | {item['size']} bytes | "
                        f"peer={item['peer_name']} ({item['peer_id']}) @ {item['ip']}"
                    )
                continue

            if command.startswith("/download "):
                parts = command.split(" ")
                if len(parts) < 2:
                    print("Usage: /download <file_id> [output_path]")
                    continue

                file_id = parts[1]
                output_path = parts[2] if len(parts) > 2 else None
                self.download_file(file_id, output_path)
                continue

            if command == "/quit":
                self.shutdown_event.set()
                print("Shutting down...")
                break

            print("Unknown command. Use /help.")


def main() -> None:
    node = SwarmLinkNode()
    node.start()
    node.run_cli()


if __name__ == "__main__":
    main()
