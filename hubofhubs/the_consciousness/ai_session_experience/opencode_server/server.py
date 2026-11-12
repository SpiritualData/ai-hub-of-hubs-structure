"""The loopback HTTP server: standard-library ``ThreadingHTTPServer``, the routes of ``routes``, and the event stream as server-sent events with a heartbeat.

It listens on the loopback interface only: a host that is not a loopback address is refused unless the caller says it is wanted (``allow_remote``), and the default port is 0 (the system picks a free one). It
asks for the per-run token as the client's basic-auth password (user ``opencode``, the client's own ``OPENCODE_PASSWORD`` setting), so another program on the machine cannot read or steer a session. An
event stream starts with ``server.connected`` (the client then reads the snapshot again) and may name the last event it saw (``Last-Event-ID``) to get what it missed from the store's buffer."""
from __future__ import annotations

import base64
import hmac
import ipaddress
import json
import queue
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import routes
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge

USERNAME = "opencode"
HEARTBEAT_SECONDS = 15.0


def is_loopback(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


class OpencodeServer:
    """A running (or startable) server over one ``Bridge``. ``token`` is the per-run password (generated when not given)."""

    def __init__(self, bridge: Bridge, host: str = "127.0.0.1", port: int = 0, token: Optional[str] = None, heartbeat: float = HEARTBEAT_SECONDS, allow_remote: bool = False) -> None:
        if not is_loopback(host) and not allow_remote:
            raise ValueError(f"refusing to listen on {host!r}: the server binds to the loopback interface only unless allow_remote is set")
        self.bridge, self.heartbeat = bridge, heartbeat
        self.token = secrets.token_urlsafe(24) if token is None else token
        self.requests: List[Tuple[str, str, int]] = []
        self.httpd = ThreadingHTTPServer((host, port), self.handler())
        self.httpd.daemon_threads = True
        self.thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return int(self.httpd.server_address[1])

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> "OpencodeServer":
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return self

    def serve_forever(self) -> None:
        self.httpd.serve_forever()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def handler(self) -> Any:
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args: Any) -> None:
                return None

            def allowed(self) -> bool:
                if not server.token:
                    return True
                header = self.headers.get("authorization", "")
                if not header.lower().startswith("basic "):
                    return False
                try:
                    user, _, password = base64.b64decode(header[6:]).decode().partition(":")
                except Exception:  # noqa: BLE001 -- a malformed header is not allowed
                    return False
                return hmac.compare_digest(user, USERNAME) and hmac.compare_digest(password, server.token)

            def send(self, status: int, body: Any) -> None:
                data = b"" if body is None else json.dumps(body).encode()
                self.send_response(status)
                if body is not None:
                    self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def stream(self) -> None:
                store = server.bridge.store
                waiting = store.subscribe(self.headers.get("last-event-id", ""))
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.send_header("cache-control", "no-cache, no-transform")
                self.end_headers()
                try:
                    self.wfile.write(f"data: {json.dumps(store.connected())}\n\n".encode())
                    self.wfile.flush()
                    while True:
                        try:
                            event = waiting.get(timeout=server.heartbeat)
                            self.wfile.write(f"id: {event['id']}\ndata: {json.dumps(event)}\n\n".encode())
                        except queue.Empty:
                            self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
                except (OSError, ValueError):
                    pass
                finally:
                    store.unsubscribe(waiting)

            def handle_request(self) -> None:
                url = urlparse(self.path)
                length = int(self.headers.get("content-length") or 0)
                raw = self.rfile.read(length).decode() if length else ""
                if not self.allowed():
                    server.requests.append((self.command, url.path, 401))
                    return self.send(401, {"_tag": "UnauthorizedError", "message": "Authentication required"})
                if url.path == "/api/event" and self.command == "GET":
                    server.requests.append((self.command, url.path, 200))
                    return self.stream()
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = None
                status, answer = routes.handle(server.bridge, self.command, url.path, parse_qs(url.query), body, server.port)
                server.requests.append((self.command, url.path, status))
                if len(server.requests) > 5000:
                    del server.requests[:1000]
                self.send(status, answer)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = handle_request

        return Handler
