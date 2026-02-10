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

## Run locally (single node)

```bash
python main.py
```

Default ports:
- UDP discovery: `37020`
- TCP service: `6001`

## Commands

- `/help`
- `/peers`
- `/chat <peer_id> <message>`
- `/share <file_path>`
- `/myfiles`
- `/find <name-or-file_id>`
- `/download <file_id> [output_path]`
- `/quit`

## Docker Compose multi-node simulation

This setup lets you simulate multiple devices on one machine.

### Start 3 nodes

```bash
docker compose up --build --scale node=3 -d
```

### Scale to more nodes

You can increase the swarm size any time:

```bash
docker compose up --scale node=5 -d
```

### Stop everything

```bash
docker compose down
```

## Logging and debugging

All container output is written to the host `logs/` folder, one file per container:

- `logs/<container_hostname>.log`

Useful debug commands:

```bash
# Real-time compose logs
docker compose logs -f

# See active containers
docker compose ps

# Inspect one node log file
tail -f logs/<container_hostname>.log
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

## Manual validation flow

1. Start multiple nodes (multi-device LAN or Docker Compose scale).
2. Verify discovery messages appear in logs.
3. Run one interactive node locally (`python main.py`) and verify `/peers`.
4. Share from one node and search/download from another.
5. Verify download completion and checksum pass messages.
