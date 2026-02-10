async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (_) {
      // Ignore JSON parse errors
    }
    throw new Error(detail);
  }

  return response.json();
}

function renderList(elementId, items) {
  const list = document.getElementById(elementId);
  list.innerHTML = "";

  if (!items.length) {
    const li = document.createElement("li");
    li.textContent = "No items";
    list.appendChild(li);
    return;
  }

  for (const item of items) {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  }
}

async function loadNode() {
  const node = await api("/node");
  document.getElementById("nodeInfo").textContent = JSON.stringify(node, null, 2);
}

async function loadPeers() {
  const peers = await api("/peers");
  const items = peers.map(
    (peer) => `${peer.peer_id} | ${peer.name} | ${peer.ip}:${peer.tcp_port}`
  );
  renderList("peerList", items);
}

async function loadMessages() {
  const messages = await api("/messages");
  const container = document.getElementById("messages");
  container.innerHTML = "";

  for (const message of messages) {
    const div = document.createElement("div");
    div.className = "msg-item";
    const timestamp = new Date(message.timestamp * 1000).toLocaleTimeString();
    div.textContent = `[${timestamp}] ${message.direction} ${message.peer_name} (${message.peer_id}): ${message.text}`;
    container.appendChild(div);
  }
}

async function sendChat() {
  const peerId = document.getElementById("chatPeerId").value.trim();
  const text = document.getElementById("chatText").value.trim();
  if (!peerId || !text) {
    alert("Peer ID and message are required");
    return;
  }

  await api("/chat", {
    method: "POST",
    body: JSON.stringify({ peer_id: peerId, text }),
  });

  document.getElementById("chatText").value = "";
  await loadMessages();
}

async function shareFile() {
  const filePath = document.getElementById("sharePath").value.trim();
  if (!filePath) {
    alert("File path is required");
    return;
  }

  const result = await api("/share", {
    method: "POST",
    body: JSON.stringify({ file_path: filePath }),
  });

  document.getElementById("shareResult").textContent = `Shared: ${result.name} (${result.file_id})`;
  await loadLocalFiles();
}

async function loadLocalFiles() {
  const files = await api("/files/local");
  const items = files.map(
    (file) => `${file.file_id} | ${file.name} | ${file.size} bytes | pieces=${file.piece_count}`
  );
  renderList("localFiles", items);
}

async function loadPeerFiles() {
  const peerId = document.getElementById("peerFilesPeerId").value.trim();
  if (!peerId) {
    alert("Peer ID is required");
    return;
  }

  const files = await api(`/files/peer/${peerId}`);
  const items = files.map(
    (file) => `${file.file_id} | ${file.name} | ${file.size} bytes | pieces=${file.piece_count}`
  );
  renderList("peerFiles", items);
}

async function downloadFile() {
  const fileId = document.getElementById("downloadFileId").value.trim();
  const outputPath = document.getElementById("downloadPath").value.trim();
  if (!fileId) {
    alert("File ID is required");
    return;
  }

  const result = await api("/download", {
    method: "POST",
    body: JSON.stringify({ file_id: fileId, output_path: outputPath || null }),
  });

  document.getElementById("downloadResult").textContent = result.message;
}

function wireEvents() {
  document.getElementById("refreshPeers").addEventListener("click", () => loadPeers().catch(alert));
  document.getElementById("sendChat").addEventListener("click", () => sendChat().catch((err) => alert(err.message)));
  document.getElementById("shareFile").addEventListener("click", () => shareFile().catch((err) => alert(err.message)));
  document.getElementById("refreshLocalFiles").addEventListener("click", () => loadLocalFiles().catch(alert));
  document.getElementById("loadPeerFiles").addEventListener("click", () => loadPeerFiles().catch((err) => alert(err.message)));
  document.getElementById("downloadFile").addEventListener("click", () => downloadFile().catch((err) => alert(err.message)));
}

async function init() {
  wireEvents();
  await loadNode();
  await loadPeers();
  await loadLocalFiles();
  await loadMessages();

  setInterval(() => {
    loadPeers().catch(() => {});
    loadMessages().catch(() => {});
  }, 3000);
}

init().catch((err) => alert(err.message));
