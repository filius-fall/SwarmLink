FROM python:3.12-slim

WORKDIR /app

COPY main.py /app/main.py
COPY peer_discovery.py /app/peer_discovery.py
COPY file_swarm.py /app/file_swarm.py
COPY tcp_protocol.py /app/tcp_protocol.py
COPY run_node.py /app/run_node.py
COPY api.py /app/api.py

RUN pip install --no-cache-dir fastapi uvicorn
RUN mkdir -p /app/logs

CMD ["python", "run_node.py", "--name", "node", "--tcp-port", "6001"]
