# SwarmLink

SwarmLink is a LAN peer-to-peer app in Python 3.12 that does:
- UDP peer discovery
- TCP direct chat
- BitTorrent-style file sharing (piece-by-piece, multi-peer downloads)

## How it works

1. Each node sends UDP broadcast announcements on `37020`.
2. Nodes that receive announcements store peer IP + TCP port.
3. Chat and file commands use direct TCP connections to discovered peers.
4. File download requests are split by pieces and fetched in parallel from multiple seeders.

## Run locally (single node, CLI)

```bash
python main.py
```

Default ports:
- UDP discovery: `37020`
- TCP service: `6001`

## CLI Commands

- `/help`
- `/peers`
- `/chat <peer_id> <message>`
- `/share <file_path>`
- `/myfiles`
- `/find <name-or-file_id>`
- `/download <file_id> [output_path]`
- `/quit`

## FastAPI Interface

SwarmLink now includes an HTTP API wrapper around the same node behavior.

### Run API locally

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

Optional environment variables:
- `SWARMLINK_NODE_NAME` (default: hostname)
- `SWARMLINK_TCP_PORT` (default: `6001`)

### API endpoints

- `GET /health` → health check
- `GET /node` → local node details
- `GET /peers` → discovered peers
- `POST /chat` → send chat to peer
- `POST /share` → share local file
- `GET /files/local` → local shared files
- `GET /files/find?query=<text>` → search files on peers
- `POST /download` → download file from swarm

Example request bodies:

```json
POST /chat
{
  "peer_id": "abc123",
  "text": "hello"
}
```

```json
POST /share
{
  "file_path": "/app/data/video.mp4"
}
```

```json
POST /download
{
  "file_id": "f00dbabe1234",
  "output_path": "downloads/video.mp4"
}
```

## Docker Compose multi-node simulation

This setup lets you simulate multiple devices on one machine.

### Start 3 nodes + API

```bash
docker compose up --build --scale node=3 -d
```

### Scale to more nodes

```bash
docker compose up --scale node=5 -d
```

### Stop everything

```bash
docker compose down
```

## Logging and debugging

All container output is written to the host `logs/` folder:

- `logs/<container_hostname>.log` for simulated nodes
- `logs/api.log` for FastAPI server

Useful debug commands:

```bash
# Real-time compose logs
docker compose logs -f

# See active containers
docker compose ps

# Inspect node log
tail -f logs/<container_hostname>.log

# Inspect api log
tail -f logs/api.log
```

Notes for easier debugging:
- Each node uses its container hostname as node name, so logs are easy to map.
- Discovery events print lines like `Discovered peer: ...`.
- TCP chat and file transfer requests also print warnings/errors in the same log file.

## Code structure

- `main.py`: node orchestration, TCP server handlers, and CLI.
- `peer_discovery.py`: UDP announce/listen service + peer registry.
- `file_swarm.py`: file indexing, piece hashing, and swarm downloader.
- `tcp_protocol.py`: JSON-over-TCP framing helpers.
- `run_node.py`: non-interactive/interactive launcher for local and container simulation.
- `api.py`: FastAPI wrapper exposing SwarmLink operations over HTTP.

## Manual validation flow

1. Start multiple nodes (multi-device LAN or Docker Compose scale).
2. Verify discovery messages appear in logs.
3. Call `GET /peers` from API and verify discovered entries.
4. Share from one node and search/download from another.
5. Verify download completion and checksum pass messages.
