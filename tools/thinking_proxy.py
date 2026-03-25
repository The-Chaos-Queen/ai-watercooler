"""
thinking_proxy.py — TCP-level reverse proxy that strips the redact-thinking
beta header. Passes everything else byte-for-byte including SSE streams.

Usage:
  python thinking_proxy.py
  $env:ANTHROPIC_BASE_URL="http://localhost:9099"; claude
"""

import socket
import ssl
import threading
import re
import sys

LOCAL_HOST = "127.0.0.1"
LOCAL_PORT = 9099
REMOTE_HOST = "api.anthropic.com"
REMOTE_PORT = 443
STRIP_PATTERN = re.compile(rb"redact-thinking-[0-9-]+,?\s*")
BETA_CLEANUP = re.compile(rb"anthropic-beta:\s*,\s*", re.IGNORECASE)
EMPTY_BETA = re.compile(rb"anthropic-beta:\s*\r\n", re.IGNORECASE)


def patch_headers(raw_request: bytes) -> bytes:
    """Strip redact-thinking from the anthropic-beta header in raw HTTP."""
    # Split headers from body
    header_end = raw_request.find(b"\r\n\r\n")
    if header_end == -1:
        return raw_request

    headers = raw_request[:header_end]
    rest = raw_request[header_end:]

    original = headers
    # Strip the redact-thinking entry
    headers = STRIP_PATTERN.sub(b"", headers)
    # Clean up trailing/leading commas
    headers = re.sub(rb"(anthropic-beta:\s*),\s*(\S)", rb"\1\2", headers)
    # Remove empty anthropic-beta header
    headers = EMPTY_BETA.sub(b"", headers)
    # Fix Host header
    headers = re.sub(rb"Host:\s*127\.0\.0\.1[:\d]*", b"Host: api.anthropic.com", headers)

    if headers != original:
        print("[PROXY] Stripped redact-thinking header")

    return headers + rest


def forward(src, dst, name, patch=False, buffer_first=False):
    """Forward bytes from src to dst. Optionally patch the first chunk (headers)."""
    first = True
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            if first and patch:
                data = patch_headers(data)
                first = False
            dst.sendall(data)
    except (ConnectionError, OSError):
        pass
    finally:
        try:
            dst.shutdown(socket.SHUT_WR)
        except OSError:
            pass


def handle_client(client_sock: socket.socket):
    """Handle one client connection: connect to Anthropic, patch headers, relay."""
    try:
        # Connect to Anthropic API over TLS
        ctx = ssl.create_default_context()
        raw_sock = socket.create_connection((REMOTE_HOST, REMOTE_PORT), timeout=30)
        remote_sock = ctx.wrap_socket(raw_sock, server_hostname=REMOTE_HOST)

        # Bidirectional forwarding
        # Client → Remote: patch headers on first chunk
        t1 = threading.Thread(target=forward, args=(client_sock, remote_sock, "C→R", True))
        # Remote → Client: pass through unchanged
        t2 = threading.Thread(target=forward, args=(remote_sock, client_sock, "R→C", False))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

    except Exception as e:
        print(f"[PROXY] Error: {e}")
    finally:
        client_sock.close()


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((LOCAL_HOST, LOCAL_PORT))
    server.listen(32)

    print(f"[PROXY] Thinking proxy on http://{LOCAL_HOST}:{LOCAL_PORT}")
    print(f"[PROXY] Forwarding to {REMOTE_HOST}:{REMOTE_PORT} (TLS)")
    print(f"[PROXY] Stripping redact-thinking from anthropic-beta")
    print(f'[PROXY] Launch: $env:ANTHROPIC_BASE_URL="http://{LOCAL_HOST}:{LOCAL_PORT}"; claude')
    print()

    try:
        while True:
            client_sock, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(client_sock,), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n[PROXY] Bye.")
        server.close()


if __name__ == "__main__":
    main()
