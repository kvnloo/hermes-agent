#!/usr/bin/env python3
"""Loopback reverse proxy that rewrites Tailnet Host for the pinned preview."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import http.client

UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 44923
LISTEN = ("127.0.0.1", 9137)
HOP = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _proxy(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else None
        headers = {key: value for key, value in self.headers.items() if key.lower() not in HOP and key.lower() != "host"}
        headers["Host"] = f"{UPSTREAM_HOST}:{UPSTREAM_PORT}"
        headers["X-Forwarded-Host"] = self.headers.get("Host", "")
        headers["X-Forwarded-Proto"] = "https"
        connection = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=60)
        try:
            connection.request(self.command, self.path, body=body, headers=headers)
            response = connection.getresponse()
            data = response.read()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in HOP and key.lower() != "content-length":
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        finally:
            connection.close()

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _proxy

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    ThreadingHTTPServer(LISTEN, Proxy).serve_forever()
