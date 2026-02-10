import json
import socket
import threading
import time
from dataclasses import dataclass

UDP_DISCOVERY_PORT = 37020
BROADCAST_IP = "255.255.255.255"
ANNOUNCE_INTERVAL_SECONDS = 3


@dataclass
class PeerInfo:
    """Represents one discovered peer on the LAN.

    Why this exists:
    - We need a stable shape for peer metadata so chat/file commands can reuse it.
    - Using a dataclass keeps peer handling simple and readable.
    """

    peer_id: str
    name: str
    ip: str
    tcp_port: int
    last_seen: float


class PeerRegistry:
    """Thread-safe store for discovered peers.

    Why this exists:
    - Discovery runs in background threads.
    - CLI commands read peer data at the same time.
    - A lock ensures the in-memory registry is safe to update/read concurrently.
    """

    def __init__(self) -> None:
        self._peers: dict[str, PeerInfo] = {}
        self._lock = threading.Lock()

    def upsert(self, peer: PeerInfo) -> bool:
        """Insert or refresh a peer.

        Returns:
            True if this peer was seen for the first time, else False.

        Why this return value matters:
        - Caller can print "new peer discovered" messages only once.
        """

        with self._lock:
            is_new = peer.peer_id not in self._peers
            self._peers[peer.peer_id] = peer
            return is_new

    def get(self, peer_id: str) -> PeerInfo | None:
        """Fetch one peer by id."""

        with self._lock:
            return self._peers.get(peer_id)

    def list_all(self) -> list[PeerInfo]:
        """Return a snapshot list of peers.

        Why snapshot:
        - Prevent callers from holding lock while iterating/printing.
        """

        with self._lock:
            return list(self._peers.values())


class DiscoveryService:
    """Handles UDP broadcast announce + UDP listening for peers.

    Why split this service out:
    - Keeps discovery logic independent from TCP chat/file protocol.
    - Makes main CLI easier to read and maintain.
    """

    def __init__(
        self,
        peer_registry: PeerRegistry,
        self_peer_id: str,
        self_name: str,
        tcp_port: int,
        shutdown_event: threading.Event,
    ) -> None:
        self.peer_registry = peer_registry
        self.self_peer_id = self_peer_id
        self.self_name = self_name
        self.tcp_port = tcp_port
        self.shutdown_event = shutdown_event

    def start(self) -> None:
        """Start both announce and listen loops as daemon threads."""

        threading.Thread(target=self._announce_loop, daemon=True).start()
        threading.Thread(target=self._listen_loop, daemon=True).start()

    def _announce_loop(self) -> None:
        """Broadcast our peer details over UDP repeatedly.

        Why repeated broadcast:
        - Devices can join later and still discover us.
        - Peer entries can naturally refresh with latest IP/port.
        """

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        payload = {
            "type": "ANNOUNCE",
            "peer_id": self.self_peer_id,
            "name": self.self_name,
            "tcp_port": self.tcp_port,
        }

        while not self.shutdown_event.is_set():
            try:
                sock.sendto(
                    json.dumps(payload).encode("utf-8"),
                    (BROADCAST_IP, UDP_DISCOVERY_PORT),
                )
            except OSError as exc:
                print(f"UDP announce warning: {exc}")
            time.sleep(ANNOUNCE_INTERVAL_SECONDS)

        sock.close()

    def _listen_loop(self) -> None:
        """Listen for UDP announces and add/update peers.

        Why ignore our own announce:
        - Some NICs/OS stacks loop back broadcast packets.
        - We do not want to register ourselves as a remote peer.
        """

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", UDP_DISCOVERY_PORT))
        sock.settimeout(1.0)

        while not self.shutdown_event.is_set():
            try:
                payload, addr = sock.recvfrom(64 * 1024)
            except socket.timeout:
                continue
            except OSError as exc:
                print(f"UDP receive warning: {exc}")
                continue

            try:
                message = json.loads(payload.decode("utf-8"))
            except json.JSONDecodeError:
                continue

            if message.get("type") != "ANNOUNCE":
                continue

            peer_id = message.get("peer_id")
            if not peer_id or peer_id == self.self_peer_id:
                continue

            peer = PeerInfo(
                peer_id=peer_id,
                name=message.get("name", "unknown"),
                ip=addr[0],
                tcp_port=int(message.get("tcp_port", 6001)),
                last_seen=time.time(),
            )

            is_new = self.peer_registry.upsert(peer)
            if is_new:
                print(
                    f"Discovered peer: {peer.name} ({peer.peer_id}) at "
                    f"{peer.ip}:{peer.tcp_port}"
                )

        sock.close()
