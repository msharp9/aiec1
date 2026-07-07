"""Warmup TCP proxy for running langgraph-api on Vercel.

Vercel gives a container ~15s to accept TCP on $PORT, but the langgraph-api
server needs ~27s to boot (Go core + Python imports + migrations + license
check). This proxy binds $PORT instantly to satisfy Vercel's readiness gate,
then forwards every connection to the real server on an internal port,
retry-dialing the backend while it is still booting so early requests are held
open instead of refused.

Usage: python3 vercel_port_proxy.py <listen_port> <backend_port>
"""

import asyncio
import sys

BACKEND_HOST = "127.0.0.1"
# How long to keep retrying the backend before giving up on a single client.
# Comfortably covers the ~27s cold boot; Vercel's per-request budget is larger.
CONNECT_TIMEOUT_SECS = 120
RETRY_INTERVAL_SECS = 0.25


async def _pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while not reader.at_eof():
            data = await reader.read(65536)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except (ConnectionError, asyncio.CancelledError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def _dial_backend(backend_port: int):
    """Retry-connect to the backend until it is up or we exhaust the budget."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + CONNECT_TIMEOUT_SECS
    while True:
        try:
            return await asyncio.open_connection(BACKEND_HOST, backend_port)
        except (ConnectionError, OSError):
            if loop.time() >= deadline:
                raise
            await asyncio.sleep(RETRY_INTERVAL_SECS)


def make_handler(backend_port: int):
    async def handle(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
        try:
            backend_reader, backend_writer = await _dial_backend(backend_port)
        except (ConnectionError, OSError):
            client_writer.close()
            return
        await asyncio.gather(
            _pipe(client_reader, backend_writer),
            _pipe(backend_reader, client_writer),
        )

    return handle


async def main() -> None:
    listen_port = int(sys.argv[1])
    backend_port = int(sys.argv[2])
    server = await asyncio.start_server(make_handler(backend_port), "0.0.0.0", listen_port)
    print(f"[vercel_port_proxy] listening on 0.0.0.0:{listen_port} -> {BACKEND_HOST}:{backend_port}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
