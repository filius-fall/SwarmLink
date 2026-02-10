import json
import socket
from typing import Any

BUFFER_SIZE = 64 * 1024


def send_json_line(conn: socket.socket, payload: dict[str, Any]) -> None:
    """Send one JSON message followed by newline.

    Why newline framing:
    - TCP is stream based, not message based.
    - Newline gives us a simple message boundary for request/response flow.
    """

    conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))


def recv_json_line(conn: socket.socket) -> dict[str, Any] | None:
    """Receive one newline-delimited JSON object.

    Returns:
        Parsed dict if a full line is received.
        None if connection closes before full message.

    Why this helper:
    - Centralizes framing/parsing rules for all TCP handlers.
    - Avoids duplicated recv loops throughout the code.
    """

    data = b""
    while b"\n" not in data:
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            return None
        data += chunk
        if len(data) > 20 * 1024 * 1024:
            raise ValueError("Incoming payload too large")

    line = data.split(b"\n", 1)[0]
    return json.loads(line.decode("utf-8"))
