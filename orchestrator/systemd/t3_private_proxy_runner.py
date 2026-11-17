#!/usr/bin/env python3
"""Run T3 beside a loopback-to-UNIX HTTPS proxy bridge in its network namespace."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import signal
import sys

from https_connect_broker import pipe_stream


def clean_child_environment(state_dir: str, proxy_port: int) -> dict[str, str]:
    endpoint = f"http://127.0.0.1:{proxy_port}"
    return {
        "HOME": state_dir,
        "XDG_CONFIG_HOME": f"{state_dir}/.config",
        "XDG_DATA_HOME": f"{state_dir}/.local/share",
        "XDG_CACHE_HOME": f"{state_dir}/.cache",
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C",
        "HTTPS_PROXY": endpoint,
        "https_proxy": endpoint,
        "NO_PROXY": "localhost,127.0.0.1",
        "no_proxy": "localhost,127.0.0.1",
    }


async def bridge_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    socket_path: Path,
    connect_unix=asyncio.open_unix_connection,
) -> None:
    upstream_writer: asyncio.StreamWriter | None = None
    try:
        upstream_reader, upstream_writer = await connect_unix(str(socket_path))
        await asyncio.gather(
            pipe_stream(reader, upstream_writer),
            pipe_stream(upstream_reader, writer),
        )
    except (ConnectionError, OSError):
        writer.write(b"HTTP/1.1 502 Proxy broker unavailable\r\nConnection: close\r\n\r\n")
        try:
            await writer.drain()
        except (ConnectionError, OSError):
            pass
    finally:
        if upstream_writer is not None:
            upstream_writer.close()
            await upstream_writer.wait_closed()
        writer.close()
        await writer.wait_closed()


async def run(state_dir: str, socket_path: Path, proxy_port: int, command: list[str]) -> int:
    if not command:
        raise ValueError("T3 command is required after --")
    server = await asyncio.start_server(
        lambda reader, writer: bridge_client(reader, writer, socket_path),
        host="127.0.0.1", port=proxy_port, limit=8192,
    )
    child = await asyncio.create_subprocess_exec(
        *command,
        env=clean_child_environment(state_dir, proxy_port),
    )
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(signum, child.terminate)
        except NotImplementedError:
            pass
    try:
        return await child.wait()
    finally:
        server.close()
        await server.wait_closed()
        if child.returncode is None:
            child.terminate()
            try:
                await asyncio.wait_for(child.wait(), timeout=5)
            except asyncio.TimeoutError:
                child.kill()
                await child.wait()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--upstream-socket", required=True, type=Path)
    parser.add_argument("--proxy-port", type=int, default=3128)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not 1024 <= args.proxy_port <= 65535:
        parser.error("--proxy-port must be in the range 1024..65535")
    try:
        return asyncio.run(run(args.state_dir, args.upstream_socket, args.proxy_port, command))
    except (OSError, ValueError) as exc:
        print(f"proxy runner: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
