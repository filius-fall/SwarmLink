import base64
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
from typing import Any, Callable

from peer_discovery import PeerInfo

PIECE_SIZE = 256 * 1024


class SharedFileIndex:
    """Tracks files this node is seeding and provides metadata/piece access.

    Why this exists:
    - Keeps file indexing logic separate from network server logic.
    - Makes piece/hash operations reusable and easier to test.
    """

    def __init__(self) -> None:
        self._files: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _sha256_bytes(content: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(content)
        return digest.hexdigest()

    def share_file(self, file_path: str) -> dict[str, Any] | None:
        """Index a file for sharing and return file metadata.

        Why return metadata:
        - Caller can immediately print file_id and piece count for user feedback.
        """

        path = Path(file_path).expanduser().resolve()
        if not path.exists() or not path.is_file():
            return None

        file_hash = hashlib.sha256()
        piece_hashes: list[str] = []

        with path.open("rb") as file_obj:
            while True:
                piece = file_obj.read(PIECE_SIZE)
                if not piece:
                    break
                file_hash.update(piece)
                piece_hashes.append(self._sha256_bytes(piece))

        file_size = path.stat().st_size
        file_id_seed = f"{path.name}:{file_hash.hexdigest()}:{file_size}".encode(
            "utf-8"
        )
        file_id = hashlib.sha1(file_id_seed).hexdigest()[:16]

        metadata = {
            "file_id": file_id,
            "name": path.name,
            "size": file_size,
            "piece_size": PIECE_SIZE,
            "piece_hashes": piece_hashes,
            "file_hash": file_hash.hexdigest(),
            "path": str(path),
        }

        with self._lock:
            self._files[file_id] = metadata

        return metadata

    def list_files(self) -> list[dict[str, Any]]:
        """Return lightweight list for CLI and LIST_FILES responses."""

        with self._lock:
            return [
                {
                    "file_id": item["file_id"],
                    "name": item["name"],
                    "size": item["size"],
                    "piece_count": len(item["piece_hashes"]),
                }
                for item in self._files.values()
            ]

    def get_file_info(self, file_id: str) -> dict[str, Any] | None:
        """Return full metadata required by downloaders."""

        with self._lock:
            item = self._files.get(file_id)

        if not item:
            return None

        return {
            "file_id": item["file_id"],
            "name": item["name"],
            "size": item["size"],
            "piece_size": item["piece_size"],
            "piece_hashes": item["piece_hashes"],
            "file_hash": item["file_hash"],
        }

    def read_piece(self, file_id: str, piece_index: int) -> tuple[bytes, str] | None:
        """Read one piece from disk and return (bytes, sha256).

        Why this function:
        - Centralizes piece bounds checks and disk reads.
        - TCP handler can stay small and focus on protocol.
        """

        with self._lock:
            item = self._files.get(file_id)
        if not item:
            return None

        piece_hashes = item["piece_hashes"]
        if piece_index < 0 or piece_index >= len(piece_hashes):
            return None

        with open(item["path"], "rb") as file_obj:
            file_obj.seek(piece_index * item["piece_size"])
            piece = file_obj.read(item["piece_size"])

        return piece, self._sha256_bytes(piece)


class SwarmDownloader:
    """Downloads a file in parallel pieces from multiple peers.

    Why this exists:
    - Encapsulates BitTorrent-like strategy away from CLI orchestration.
    - Keeps download logic readable and maintainable.
    """

    def __init__(
        self, request_fn: Callable[[PeerInfo, dict[str, Any]], dict[str, Any] | None]
    ):
        self.request_fn = request_fn

    @staticmethod
    def _sha256_bytes(content: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(content)
        return digest.hexdigest()

    def collect_seeders(
        self, peers: list[PeerInfo], file_id: str
    ) -> tuple[list[tuple[PeerInfo, dict[str, Any]]], dict[str, Any] | None]:
        """Find peers seeding the requested file and validate consistent metadata.

        Why metadata consistency check:
        - Protects against mixing pieces from different files with same name.
        """

        seeders: list[tuple[PeerInfo, dict[str, Any]]] = []
        canonical: dict[str, Any] | None = None

        for peer in peers:
            response = self.request_fn(
                peer, {"type": "FILE_INFO_REQ", "file_id": file_id}
            )
            if (
                not response
                or response.get("type") != "FILE_INFO_RESP"
                or not response.get("found")
            ):
                continue

            info = response.get("file")
            if not info:
                continue

            if canonical is None:
                canonical = info
            elif canonical.get("file_hash") != info.get("file_hash") or canonical.get(
                "piece_hashes"
            ) != info.get("piece_hashes"):
                continue

            seeders.append((peer, info))

        return seeders, canonical

    def download(
        self,
        file_id: str,
        peers: list[PeerInfo],
        output_path: str | None = None,
    ) -> tuple[bool, str]:
        """Download file pieces in parallel and verify hashes.

        Returns:
            (True, message) on success or (False, error_message) on failure.
        """

        seeders, file_info = self.collect_seeders(peers, file_id)
        if not seeders or not file_info:
            return False, "No peers currently seed this file."

        piece_hashes = file_info["piece_hashes"]
        total_pieces = len(piece_hashes)
        piece_store: dict[int, bytes] = {}
        lock = threading.Lock()

        def fetch_piece(piece_index: int) -> bool:
            # Rotate starting seeder by piece index to spread load.
            for offset in range(len(seeders)):
                peer = seeders[(piece_index + offset) % len(seeders)][0]
                response = self.request_fn(
                    peer,
                    {
                        "type": "PIECE_REQ",
                        "file_id": file_id,
                        "piece_index": piece_index,
                    },
                )
                if not response or not response.get("ok"):
                    continue

                raw = base64.b64decode(response.get("data", ""))
                if self._sha256_bytes(raw) != piece_hashes[piece_index]:
                    continue

                with lock:
                    piece_store[piece_index] = raw
                return True

            return False

        with ThreadPoolExecutor(max_workers=min(8, max(1, len(seeders) * 2))) as pool:
            results = list(pool.map(fetch_piece, range(total_pieces)))

        if not all(results) or len(piece_store) != total_pieces:
            return (
                False,
                "Download failed: some pieces could not be fetched or verified.",
            )

        target_name = output_path or file_info["name"]
        target = Path(target_name).expanduser().resolve()

        with target.open("wb") as file_obj:
            for index in range(total_pieces):
                file_obj.write(piece_store[index])

        with target.open("rb") as file_obj:
            final_hash = hashlib.sha256(file_obj.read()).hexdigest()

        if final_hash != file_info["file_hash"]:
            target.unlink(missing_ok=True)
            return False, "Download failed: final file checksum mismatch."

        return True, f"Download complete: {target}"
