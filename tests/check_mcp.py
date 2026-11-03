"""Run with `python tests/check_mcp.py`; no API key is needed."""

import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from mcp import Client


async def check(port):
    async with Client(f"http://127.0.0.1:{port}/mcp") as client:
        tools = await client.list_tools()
        assert "get_sales" in [tool.name for tool in tools.tools]
        cases = [
            ("Singapore", "2026-Q1", 100),
            ("Singapore", "2026-Q2", 200),
            ("Singapore", "2026-Q3", 300),
            ("Unknown", "2026-Q2", {"error": "Region 'Unknown' not found."}),
            ("Singapore", "2026-Q4", {"error": "Period '2026-Q4' not found."}),
        ]
        for region, period, expected in cases:
            result = await client.call_tool(
                "get_sales", {"region": region, "period": period}
            )
            assert not result.is_error, result
            assert json.loads(result.content[0].text) == expected, result
            print(f"PASS: {region} {period}: {expected}")


def main():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen(
        [sys.executable, str(root / "mcp_service" / "sales_mcp_server.py")],
        env=dict(os.environ, MCP_HOST="127.0.0.1", MCP_PORT=str(port)),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 20
        while True:
            if process.poll() is not None:
                raise RuntimeError("MCP server exited during startup")
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                    break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("MCP startup timed out")
                time.sleep(0.1)
        asyncio.run(check(port))
        print("PASS: MCP tool discovery and five HTTP calls")
    finally:
        process.terminate()
        process.wait(timeout=10)
        print("Verification server stopped.")


if __name__ == "__main__":
    main()
