# SwarmLink

SwarmLink is a small Python 3.12 prototype that uses UDP broadcast to discover peers
and TCP sockets to exchange messages.

## Quick Start
1. Install dependencies (optional, formatting only):
   - `python -m pip install black`
2. Run the listener:
   - `python main.py`
3. In another terminal (or another machine on the same LAN), run the broadcaster:
   - `python send_broadcast.py`

You should see the listener discover the broadcaster and then open a TCP chat session.

## Notes
- UDP broadcast port: `37020`
- TCP ports: `5002` (broadcaster server), `6001` (listener server)
