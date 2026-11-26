#!/usr/bin/env python3
"""Mock DevBox Manager + Gateway for offline end-to-end skill verification.

Speaks the real protocol the SDK uses:
- Manager REST: /templates, /sandboxes CRUD + lifecycle
- Gateway Connect protocol: 5-byte envelope (flags=0, 4-byte BE length) + JSON frames
  for /process.Process/* and /filesystem.Filesystem/*, plus /files REST
- Command semantics: canned stdout per known command; stdin/signal/reconnect
  driven by per-PID queues so background handles behave realistically.
"""
import base64
import json
import os as _os
import re
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

API_KEY = "mock-key-123"
GW_HOST = _os.environ.get("MOCK_GATEWAY_HOST", "127.0.0.1")
BIND_HOST = _os.environ.get("MOCK_BIND", "127.0.0.1")
STATE = {"sandboxes": {}, "deleted": set()}
LOCK = threading.Lock()

# pid -> {"kind": "cat"|"readline"|"sleep"|"batch", "transform": callable,
#         "mailbox": {"queue": [("data", str) | ("end", int)], "done": Event}}
# The mailbox is the per-stream inbox; /process.Process/Connect swaps in a new
# mailbox so reconnected streams only receive post-reconnect output (no replay).
PROCESSES = {}


def connect_frame(obj: dict) -> bytes:
    data = json.dumps(obj, separators=(",", ":")).encode()
    return bytes([0]) + len(data).to_bytes(4, "big") + data


# ---- minimal protobuf wire codec (CLI exec uses the proto codec) ----
def pb_varint(n: int) -> bytes:
    out = b""
    while True:
        b = n & 0x7F
        n >>= 7
        out += bytes([b | (0x80 if n else 0)])
        if not n:
            return out


def pb_read_varint(buf: bytes, i: int):
    result, shift = 0, 0
    while True:
        b = buf[i]
        result |= (b & 0x7F) << shift
        i += 1
        if not b & 0x80:
            return result, i
        shift += 7


def pb_field(num: int, wire: int, payload):
    tag = pb_varint((num << 3) | wire)
    if wire == 0:
        return tag + pb_varint(payload)
    return tag + pb_varint(len(payload)) + payload


def pb_parse(buf: bytes) -> dict:
    fields: dict[int, list] = {}
    i = 0
    while i < len(buf):
        tag, i = pb_read_varint(buf, i)
        num, wire = tag >> 3, tag & 7
        if num == 0:
            break  # trailing padding / invalid field 0 (real CLI appends one)
        if wire == 0:
            v, i = pb_read_varint(buf, i)
        elif wire == 2:
            ln, i = pb_read_varint(buf, i)
            v = buf[i:i + ln]
            i += ln
        else:
            break
        fields.setdefault(num, []).append(v)
    return fields


def pb_bytes(num: int, inner: bytes) -> bytes:
    return pb_field(num, 2, inner)


def pb_proto_start_event(pid: int) -> bytes:
    # ProcessEvent{ start = 1: StartEvent{ pid = 1 varint } }
    return pb_bytes(1, pb_bytes(1, pb_field(1, 0, pid)))


def pb_proto_data_event(text: str) -> bytes:
    # ProcessEvent{ data = 2: DataEvent{ stdout = 1 bytes } }
    data_event = pb_field(1, 2, text.encode())
    return pb_bytes(1, pb_bytes(2, data_event))


def pb_proto_end_event(code: int) -> bytes:
    # StartResponse{ event = 1: ProcessEvent{ end = 3: EndEvent{...} } }
    end_event = pb_sint32_field(1, code) + pb_field(2, 0, 1) + pb_bytes(3, b"ok")
    return pb_bytes(1, pb_bytes(3, end_event))


def pb_sint32_field(num: int, value: int) -> bytes:
    # sint32 uses ZigZag mapping before the varint; pb_field(wire=0) encodes it
    return pb_field(num, 0, (value << 1) ^ (value >> 31))


def pb_proto_start_request(raw: bytes):
    """Parse a StartRequest proto body -> (cmd_text, stdin_flag)."""
    top = pb_parse(raw)
    proc = top.get(1, [b""])[0]
    pc = pb_parse(proc)
    cmd = pc.get(1, [b""])[0].decode(errors="replace")
    args = [a.decode(errors="replace") for a in pc.get(2, [])]
    text = (cmd + " " + " ".join(args)).strip()
    return text


def sandbox_payload(sandbox_id: str, state: str = "running", timeout_s: int = 300,
                    lifecycle: dict | None = None):
    now = int(time.time())
    payload = {
        "sandboxId": sandbox_id,
        "templateId": "default",
        "state": state,
        "createdAt": now,
        "expiresAt": now + timeout_s,
        "cpuCount": 2,
        "memoryMB": 2048,
        "diskSizeMB": 10240,
        "metadata": {"purpose": "mock-e2e"},
        "domain": f"http://{GW_HOST}:{GW_PORT}",
        "tunnelId": f"tun-{sandbox_id[:8]}",
        "connectToken": f"tok-{uuid.uuid4().hex}",
        "tokenExpiration": now + 3600,
    }
    if lifecycle:
        payload["lifecycle"] = lifecycle
    return payload


def new_pid() -> int:
    return 9000 + len(PROCESSES) + 1


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


def command_output(cmd: str) -> tuple[str, int]:
    """Canned semantics for commands the skill examples run."""
    m = re.search(r"printf\s+'([^']*)'", cmd) or re.search(r"printf\s+([^'\s].*)$", cmd)
    if m:
        return m.group(1), 0        # generic printf: quoted or bare payload
    m = re.search(r"\bexit\s+(\d+)\s*'?\s*$", cmd)
    if m:
        return "", int(m.group(1))   # exit-code propagation (CLI: bash -lc 'exit N')
    if "printf 'hello from DevBox'" in cmd:
        return "hello from DevBox", 0
    if "printf 'devbox-smoke-ok'" in cmd:
        return "devbox-smoke-ok", 0
    if "python3 --version" in cmd or "python --version" in cmd:
        return "Python 3.12.3 (mock)", 0
    if cmd.startswith("for i in 1 2 3"):
        return "line-1\nline-2\nline-3\n", 0
    if "uname -a" in cmd:
        return "Linux mock-sandbox 6.8.0 x86_64", 0
    if "echo before-pause" in cmd or "printf done" in cmd or "echo devbox" in cmd:
        return "", 0
    if "read line; printf reconnected:$line" in cmd:
        return "", 0  # output arrives via SendInput path
    if cmd == "cat":
        return "", 0  # echoes stdin via SendInput path
    if "sleep" in cmd:
        return "", 0  # batch sleeps finish silently (pure sleeps hang in the stream path)
    if "git " in cmd:
        return "", 0
    if "curl" in cmd or "echo" in cmd or "pwd" in cmd:
        return "/root\n", 0
    return "", 0


class Base(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0) or 0)
        return self.rfile.read(length) if length else b""

    def _json_body(self) -> dict:
        return self._json_body_bytes(self._read_body())

    def _json_body_bytes(self, raw: bytes) -> dict:
        if raw[:1] == b"\x00" or (raw[:1] not in (b"", b"{", b"[")):
            # connect envelope frame
            size = int.from_bytes(raw[1:5], "big")
            return json.loads(raw[5 : 5 + size])
        return json.loads(raw) if raw else {}

    def _reply_json(self, obj, status: int = 200, headers: dict | None = None):
        data = json.dumps(obj).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _reply_204(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


class ManagerHandler(Base):
    def _auth_ok(self) -> bool:
        return self.headers.get("X-API-Key") == API_KEY

    def do_GET(self):
        if not self._auth_ok():
            self._reply_json({"error": "invalid_api_key", "message": "invalid api key"}, 401)
            return
        path = urlparse(self.path).path
        if path == "/templates":
            # match the real CLI JSON tags: templateID/buildID (capital ID)
            self._reply_json([{
                "templateID": "default", "name": "Mock Linux", "aliases": ["default", "linux"],
                "buildID": "b1", "cpuCount": 2, "memoryMB": 2048, "diskSizeMB": 10240,
            }])
        elif path == "/sandboxes":
            with LOCK:
                items = [sandbox_payload(sid, s["state"], s["timeout"], lifecycle=s.get("lifecycle"))
                         for sid, s in STATE["sandboxes"].items() if sid not in STATE["deleted"]]
            self._reply_json(items, headers={"X-Total-Running": str(len(items))})
        elif m := re.match(r"^/sandboxes/([^/]+)$", path):
            sid = m.group(1)
            with LOCK:
                if sid not in STATE["sandboxes"] or sid in STATE["deleted"]:
                    self._reply_json({"error": "not_found", "message": "resource not found"}, 404)
                    return
                s = STATE["sandboxes"][sid]
            self._reply_json(sandbox_payload(sid, s["state"], s["timeout"],
                                              lifecycle=s.get("lifecycle")))
        else:
            self._reply_json({"error": "not_found", "message": "no route"}, 404)

    def do_POST(self):
        if not self._auth_ok():
            self._reply_json({"error": "invalid_api_key", "message": "invalid api key"}, 401)
            return
        path = urlparse(self.path).path
        if path == "/v1/api-keys/check":
            # CLI auth login contract (from cli/internal/auth tests):
            # matching X-API-Key -> 204 No Content; mismatch -> 401
            self._reply_204()
            return
        body = self._json_body()
        if path == "/sandboxes":
            sid = str(uuid.uuid4())
            with LOCK:
                STATE["sandboxes"][sid] = {"state": "running", "timeout": body.get("timeout", 300),
                                           "lifecycle": body.get("lifecycle")}
            self._reply_json(sandbox_payload(sid, "running", body.get("timeout", 300),
                                             lifecycle=body.get("lifecycle")), 201)
        elif m := re.match(r"^/sandboxes/([^/]+)/(connect|pause|resume|timeout|refreshes)$", path):
            sid, action = m.group(1), m.group(2)
            with LOCK:
                if sid not in STATE["sandboxes"]:
                    self._reply_json({"error": "not_found", "message": "resource not found"}, 404)
                    return
                s = STATE["sandboxes"][sid]
                if action == "pause":
                    s["state"] = "paused"
                elif action in ("resume", "connect"):
                    s["state"] = "running"
                    if "timeout" in body:
                        s["timeout"] = body["timeout"]
                elif action == "timeout":
                    s["timeout"] = body.get("timeout", 300)
                elif action == "refreshes":
                    s["timeout"] = max(s["timeout"], body.get("duration", 300))
                state = s["state"]
                timeout = s["timeout"]
            if action in ("pause",):
                self._reply_json({})
            else:
                self._reply_json(sandbox_payload(sid, state, timeout,
                                                 lifecycle=s.get("lifecycle")), 201)
        else:
            self._reply_json({"error": "not_found", "message": "no route"}, 404)

    def do_DELETE(self):
        if not self._auth_ok():
            self._reply_json({"error": "invalid_api_key", "message": "invalid api key"}, 401)
            return
        path = urlparse(self.path).path
        if m := re.match(r"^/sandboxes/([^/]+)$", path):
            sid = m.group(1)
            with LOCK:
                if sid not in STATE["sandboxes"] or sid in STATE["deleted"]:
                    self._reply_json({"error": "gone", "message": "sandbox already deleted"}, 404)
                    return
                STATE["deleted"].add(sid)
            self._reply_204()
        else:
            self._reply_json({"error": "not_found", "message": "no route"}, 404)


class GatewayHandler(Base):
    FILES = {}

    def _auth_ok(self) -> bool:
        return "relay_token=" in self.headers.get("Cookie", "")

    def _denied(self):
        self._reply_json({"code": "unauthenticated", "message": "no relay token"}, 401)

    # ---- REST files ----
    def do_GET(self):
        if not self._auth_ok():
            return self._denied()
        path = urlparse(self.path).path
        q = parse_qs(urlparse(self.path).query)
        if path == "/files":
            data = self.FILES.get(q["path"][0], b"")
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        elif path == "/metrics":
            # EnvD serves snake_case keys (both SDK parsers expect them)
            self._reply_json({
                "ts": int(time.time()), "cpu_count": 2, "cpu_used_pct": 12.5,
                "mem_total": 2048, "mem_used": 512, "mem_cache": 64,
                "disk_total": 10240, "disk_used": 1024,
            })
        elif path == "/envs":
            self._reply_json({"MOCK": "1", "PATH": "/usr/local/bin:/usr/bin:/bin"})
        elif path == "/health":
            self.send_response(200)
            self.send_header("X-Envd-Version", "v0.1.0-mock")
            self.send_header("Content-Length", "0")
            self.end_headers()

    def do_POST(self):
        if not self._auth_ok():
            return self._denied()
        path = urlparse(self.path).path
        if path == "/files":
            q = parse_qs(urlparse(self.path).query)
            target = q["path"][0]
            body = self._read_body()
            self.FILES[target] = body
            self._reply_json({"files": [{
                "name": target.rsplit("/", 1)[-1], "path": target,
                "type": "FILE_TYPE_FILE", "size": len(body),
            }]})
        elif path.startswith("/process.Process/") or path.startswith("/filesystem.Filesystem/"):
            self.handle_connect(path)
        else:
            self._reply_json({}, 404)

    # ---- Connect protocol ----
    def handle_connect(self, path: str):
        raw = self._read_body()
        proto_mode = False
        try:
            body = self._json_body_bytes(raw)
        except Exception:
            proto_mode = True
        state = {"headers_sent": False}

        def send_headers():
            if state["headers_sent"]:
                return
            state["headers_sent"] = True
            self.send_response(200)
            self.send_header("Content-Type",
                             "application/connect+proto" if proto_mode
                             else "application/connect+json")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

        def send(obj):
            send_headers()
            if proto_mode:
                # obj is pre-encoded proto bytes for the proto codec
                frame = bytes([0]) + len(obj).to_bytes(4, "big") + obj
            else:
                frame = connect_frame(obj)
            self.wfile.write(f"{len(frame):x}\r\n".encode() + frame + b"\r\n")
            self.wfile.flush()

        def send_trailer():
            # Connect end-of-stream frame: flags=2; the trailer payload is
            # JSON in BOTH codecs ({"error":...} or empty on success)
            payload = b"{}"
            frame = bytes([2]) + len(payload).to_bytes(4, "big") + payload
            self.wfile.write(f"{len(frame):x}\r\n".encode() + frame + b"\r\n")
            self.wfile.flush()

        if path == "/process.Process/Start":
            if proto_mode:
                # StartRequest proto: strip the connect envelope first, then
                # field1 ProcessConfig{cmd=1, args=2}; the CLI wraps the user
                # command as "/bin/bash -l -c <cmd>" — strip that wrapper so
                # the canned semantics table matches.
                size = int.from_bytes(raw[1:5], "big")
                top = pb_parse(raw[5 : 5 + size])
                pc = pb_parse(top.get(1, [b""])[0])
                cmd_words = [pc.get(1, [b""])[0].decode(errors="replace")]
                cmd_words += [a.decode(errors="replace") for a in pc.get(2, [])]
                cmd = " ".join(w for w in cmd_words if w)
                prefix = "/bin/bash -l -c "
                if cmd.startswith(prefix):
                    cmd = cmd[len(prefix):]
            else:
                cmd = body["process"].get("args", ["", "", ""])[-1]
            pid = new_pid()
            mailbox = {"queue": [], "done": threading.Event()}
            if cmd == "cat":
                kind = "cat"          # echoes stdin until CloseStdin
            elif "read line" in cmd:
                kind = "readline"     # one transformed line, then exits
            elif re.fullmatch(r"sleep\s+\d+(\.\d+)?", cmd.strip()):
                kind = "sleep"        # pure sleep: hangs until signalled
            else:
                kind = "batch"        # runs to completion immediately
            transform = (lambda d: f"reconnected:{d.strip()}") if "reconnected:$line" in cmd else (lambda d: d)
            PROCESSES[pid] = {"kind": kind, "transform": transform, "mailbox": mailbox}
            if proto_mode:
                send(pb_proto_start_event(pid))
                proc = PROCESSES[pid]
                if proc["kind"] == "batch":
                    out, code = command_output(cmd)
                    if out:
                        send(pb_proto_data_event(out))
                    send(pb_proto_end_event(code))
                    send_trailer()
                    self.finish_chunked()
                    return
                # proto streaming mailbox is not needed for CLI flows
                send(pb_proto_end_event(0))
                send_trailer()
                self.finish_chunked()
                return
            send({"event": {"start": {"pid": pid}}})
            proc = PROCESSES[pid]
            if proc["kind"] == "batch":
                out, code = command_output(cmd)
                if out:
                    send({"event": {"data": {"stdout": b64(out)}}})
                send({"event": {"end": {"exitCode": code}}})
                send_trailer()
                self.finish_chunked()
                return
            self.stream_until_done(proc["mailbox"], send, send_trailer)
        elif path == "/process.Process/Connect":
            pid = int(body["process"]["pid"])
            proc = PROCESSES.get(pid)
            if proc is None:
                send({"event": {"start": {"pid": pid}}})
                send({"event": {"end": {"exitCode": 1}}})
                send_trailer()
                self.finish_chunked()
                return
            # redirect future input to this stream; retire the old mailbox
            old = proc["mailbox"]
            proc["mailbox"] = {"queue": [], "done": threading.Event()}
            if not old["done"].is_set():
                old["queue"].append(("end", 0))
                old["done"].set()
            send({"event": {"start": {"pid": pid}}})
            self.stream_until_done(proc["mailbox"], send, send_trailer)
        elif path == "/process.Process/SendInput":
            pid = int(body["process"]["pid"])
            data = base64.b64decode(body["input"]["stdin"]).decode()
            proc = PROCESSES.get(pid)
            if proc and not proc["mailbox"]["done"].is_set():
                proc["mailbox"]["queue"].append(("data", proc.get("transform", lambda d: d)(data)))
                if proc.get("kind") == "readline":
                    proc["mailbox"]["queue"].append(("end", 0))
            self._unary_frame()
        elif path == "/process.Process/CloseStdin":
            pid = int(body["process"]["pid"])
            proc = PROCESSES.get(pid)
            if proc and not proc["mailbox"]["done"].is_set():
                proc["mailbox"]["queue"].append(("end", 0))
                proc["mailbox"]["done"].set()
            self._unary_frame()
        elif path == "/process.Process/SendSignal":
            pid = int(body["process"]["pid"])
            proc = PROCESSES.get(pid)
            if proc and not proc["mailbox"]["done"].is_set():
                proc["mailbox"]["queue"].append(("end", 137))
                proc["mailbox"]["done"].set()
            self._unary_frame()
        elif path == "/process.Process/List":
            procs = [{"pid": pid, "running": not p["mailbox"]["done"].is_set(),
                      "command": f"/bin/bash -l -c <mock-{pid}>"} for pid, p in PROCESSES.items()]
            self._unary_frame_obj({"processes": procs})
        elif path == "/filesystem.Filesystem/MakeDir":
            self._unary_frame()
        elif path == "/filesystem.Filesystem/ListDir":
            target = body["path"]
            entries = [{"name": k.rsplit("/", 1)[-1], "path": k, "type": "FILE_TYPE_FILE",
                        "size": len(v)} for k, v in self.FILES.items() if k.startswith(target)]
            self._unary_frame_obj({"entries": entries})
        elif path == "/filesystem.Filesystem/Stat":
            target = body["path"]
            if target not in self.FILES:
                data = json.dumps({"code": "not_found", "message": "no such file"}).encode()
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            data = self.FILES[target]
            self._unary_frame_obj({"entry": {
                "name": target.rsplit("/", 1)[-1], "path": target,
                "type": "FILE_TYPE_FILE", "size": len(data)}})
        elif path in ("/filesystem.Filesystem/Move", "/filesystem.Filesystem/Remove",
                      "/process.Process/Update"):
            if path.endswith("Move"):
                self.FILES[body["destination"]] = self.FILES.pop(body["source"], b"")
            elif path.endswith("Remove"):
                self.FILES.pop(body["path"], None)
            self._unary_frame()
        elif path == "/filesystem.Filesystem/WatchDir":
            target = body["path"]
            send({"start": {}})
            name = "done.txt" if "nested" in target else "watch-proof.txt"
            send({"filesystem": {"name": name, "type": "EVENT_TYPE_CREATE"}})
            send_trailer()
            self.finish_chunked()
        else:
            self._unary_frame()

    def stream_until_done(self, mailbox, send, send_trailer):
        # feed this stream's mailbox until an end frame arrives
        try:
            while True:
                if mailbox["queue"]:
                    kind, value = mailbox["queue"].pop(0)
                    if kind == "data":
                        send({"event": {"data": {"stdout": b64(value)}}})
                    else:
                        mailbox["done"].set()
                        send({"event": {"end": {"exitCode": value}}})
                        break
                elif mailbox["done"].is_set():
                    send({"event": {"end": {"exitCode": 0}}})
                    break
                else:
                    time.sleep(0.05)
            send_trailer()
            self.finish_chunked()
        except (BrokenPipeError, ConnectionResetError):
            # client disconnected this stream (e.g. handle.disconnect()); retire quietly
            mailbox["done"].set()

    def _unary_frame(self):
        self._unary_frame_obj({})

    def _unary_frame_obj(self, obj):
        # unary Connect responses are plain JSON (no 5-byte envelope)
        data = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def finish_chunked(self):
        self.wfile.write(b"0\r\n\r\n")
        self.wfile.flush()


GW_PORT = 18181
MGR_PORT = 18180


def main():
    mgr = ThreadingHTTPServer((BIND_HOST, MGR_PORT), ManagerHandler)
    gw = ThreadingHTTPServer((BIND_HOST, GW_PORT), GatewayHandler)
    threading.Thread(target=mgr.serve_forever, daemon=True).start()
    threading.Thread(target=gw.serve_forever, daemon=True).start()
    print(f"MOCK READY manager=http://127.0.0.1:{MGR_PORT} gateway=http://127.0.0.1:{GW_PORT}", flush=True)
    threading.Event().wait()


if __name__ == "__main__":
    main()
