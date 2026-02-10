import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from main import SwarmLinkNode

app = FastAPI(title="SwarmLink API", version="1.1.0")

NODE: SwarmLinkNode | None = None
NODE_LOCK = threading.Lock()

MESSAGE_LIMIT = 500
CHAT_EVENTS: deque[dict[str, Any]] = deque(maxlen=MESSAGE_LIMIT)
CHAT_LOCK = threading.Lock()

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"


class ChatRequest(BaseModel):
    peer_id: str = Field(..., description="Peer id to message")
    text: str = Field(..., description="Message body")


class ShareRequest(BaseModel):
    file_path: str = Field(..., description="Path to local file to share")


class DownloadRequest(BaseModel):
    file_id: str = Field(..., description="File id to download")
    output_path: str | None = Field(None, description="Optional destination path")


def record_chat(direction: str, peer_id: str, peer_name: str, text: str) -> None:
    """Record chat events for frontend polling.

    Why this function exists:
    - Chat currently happens over TCP sockets with terminal output.
    - Web frontend needs a compact in-memory event list to render messages.
    """

    with CHAT_LOCK:
        CHAT_EVENTS.append(
            {
                "timestamp": time.time(),
                "direction": direction,
                "peer_id": peer_id,
                "peer_name": peer_name,
                "text": text,
            }
        )


def get_or_start_node() -> SwarmLinkNode:
    """Create and start one node instance for API usage.

    Why this helper exists:
    - API handlers need a shared long-lived node for discovery/TCP behavior.
    - Startup logic should run once even with concurrent incoming requests.
    """

    global NODE

    if NODE is not None:
        return NODE

    with NODE_LOCK:
        if NODE is not None:
            return NODE

        tcp_port = int(os.getenv("SWARMLINK_TCP_PORT", "6001"))
        name = os.getenv("SWARMLINK_NODE_NAME")

        NODE = SwarmLinkNode(tcp_port=tcp_port, name=name)

        def on_chat_received(message: dict[str, Any], _addr: tuple[str, int]) -> None:
            record_chat(
                direction="inbound",
                peer_id=message.get("from_peer_id", "unknown"),
                peer_name=message.get("from_name", "unknown"),
                text=message.get("text", ""),
            )

        NODE.on_chat_received = on_chat_received
        NODE.start()
        return NODE


@app.on_event("startup")
def startup_event() -> None:
    """Start SwarmLink node when FastAPI starts."""

    get_or_start_node()


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def home() -> FileResponse:
    if not STATIC_DIR.exists():
        raise HTTPException(status_code=404, detail="Frontend assets missing")
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/node")
def node_info() -> dict[str, Any]:
    node = get_or_start_node()
    return {
        "peer_id": node.peer_id,
        "name": node.name,
        "host_ip": node.host_ip,
        "tcp_port": node.tcp_port,
    }


@app.get("/peers")
def list_peers() -> list[dict[str, Any]]:
    node = get_or_start_node()
    peers = node.peer_registry.list_all()
    return [
        {
            "peer_id": peer.peer_id,
            "name": peer.name,
            "ip": peer.ip,
            "tcp_port": peer.tcp_port,
            "last_seen": peer.last_seen,
        }
        for peer in peers
    ]


@app.post("/chat")
def send_chat(request: ChatRequest) -> dict[str, str]:
    node = get_or_start_node()
    peer = node.peer_registry.get(request.peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    response = node.request_peer(
        peer,
        {
            "type": "CHAT",
            "from_peer_id": node.peer_id,
            "from_name": node.name,
            "text": request.text,
        },
    )

    if not response or not response.get("ok"):
        raise HTTPException(status_code=502, detail="Failed to send chat message")

    record_chat(
        direction="outbound",
        peer_id=peer.peer_id,
        peer_name=peer.name,
        text=request.text,
    )

    return {"status": "sent"}


@app.get("/messages")
def messages() -> list[dict[str, Any]]:
    with CHAT_LOCK:
        return list(CHAT_EVENTS)


@app.post("/share")
def share_file(request: ShareRequest) -> dict[str, str]:
    node = get_or_start_node()
    metadata = node.file_index.share_file(request.file_path)
    if not metadata:
        raise HTTPException(status_code=400, detail="Invalid file path")

    return {
        "status": "shared",
        "file_id": metadata["file_id"],
        "name": metadata["name"],
    }


@app.get("/files/local")
def local_files() -> list[dict[str, Any]]:
    node = get_or_start_node()
    return node.file_index.list_files()


@app.get("/files/find")
def find_files(query: str) -> list[dict[str, Any]]:
    node = get_or_start_node()
    return node.find_files(query)


@app.get("/files/peer/{peer_id}")
def files_for_peer(peer_id: str) -> list[dict[str, Any]]:
    node = get_or_start_node()
    peer = node.peer_registry.get(peer_id)
    if not peer:
        raise HTTPException(status_code=404, detail="Peer not found")

    response = node.request_peer(peer, {"type": "LIST_FILES_REQ"})
    if not response or response.get("type") != "LIST_FILES_RESP":
        raise HTTPException(status_code=502, detail="Failed to list peer files")

    return response.get("files", [])


@app.post("/download")
def download_file(request: DownloadRequest) -> dict[str, str]:
    node = get_or_start_node()
    peers = node.peer_registry.list_all()
    ok, message = node.downloader.download(request.file_id, peers, request.output_path)
    if not ok:
        raise HTTPException(status_code=502, detail=message)

    return {"status": "downloaded", "message": message}
