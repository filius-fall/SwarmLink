# Repository Guidelines

## Project Structure & Module Organization
- `main.py` runs the UDP listener and TCP chat client/server logic.
- `send_broadcast.py` sends UDP broadcast beacons and hosts a TCP server.
- `pyproject.toml` and `uv.lock` define Python version and tool dependencies.
- `README.md` is currently empty; use this document as the primary contributor guide.

## Build, Test, and Development Commands
- `python main.py` starts the listener that discovers peers and accepts TCP chats.
- `python send_broadcast.py` advertises this host over UDP and accepts TCP connections.
- `python -m black .` formats Python sources (requires `black`, listed in `pyproject.toml`).

## Coding Style & Naming Conventions
- Python 3.12 only; follow PEP 8 with 4-space indentation.
- Use `snake_case` for functions/variables and `UPPER_SNAKE_CASE` for constants.
- Keep functions small and focused; prefer explicit sockets and threads over hidden globals.
- Run Black before submitting changes; avoid additional formatting tools unless required.

## Testing Guidelines
- No automated tests exist yet. If you add tests, place them in `tests/` and name files
  `test_*.py` (e.g., `tests/test_broadcast.py`).
- Aim for tests that cover UDP discovery and TCP message handling separately.

## Commit & Pull Request Guidelines
- Commit messages are short, capitalized summaries (e.g., “Added UDP feature…”).
- PRs should include: a concise description, how to run the change, and any manual test
  notes (e.g., “Ran `python main.py` + `python send_broadcast.py` on two machines”).

## Networking & Configuration Notes
- UDP broadcast port: `37020`; TCP ports: `5002` (broadcast server) and `6001` (listener).
- If you change ports, update both scripts and document the new values in the PR.
