"""Opt-in live API check. Uses the configured OpenAI account and incurs usage."""

import os
from pathlib import Path
import socket
import subprocess
import sys
import time

import httpx
from dotenv import dotenv_values


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_for_server(process, port):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("A verification server exited during startup.")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError("Verification server startup timed out.")


def main():
    root = Path(__file__).resolve().parents[1]
    settings = dotenv_values(root / ".env")
    # The backend gives .env priority; use its configured local MCP port.
    mcp_url = settings.get("MCP_SERVER_URL") or os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8001/mcp")
    from urllib.parse import urlsplit
    parsed = urlsplit(mcp_url)
    if parsed.hostname not in ("127.0.0.1", "localhost") or parsed.scheme != "http":
        raise RuntimeError("Set MCP_SERVER_URL to a local http://127.0.0.1:8001/mcp address for this check.")
    mcp_port, api_port = parsed.port or 80, free_port()
    processes = []
    try:
        commands = [
            ([sys.executable, "mcp_service/sales_mcp_server.py"],
             dict(os.environ, MCP_HOST="127.0.0.1", MCP_PORT=str(mcp_port)), mcp_port),
            ([sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", str(api_port)],
             dict(os.environ, MCP_SERVER_URL=f"http://127.0.0.1:{mcp_port}/mcp"), api_port),
        ]
        for command, env, port in commands:
            process = subprocess.Popen(
                command, cwd=root, env=env,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            processes.append(process)
            wait_for_server(process, port)
        with httpx.Client(base_url=f"http://127.0.0.1:{api_port}", timeout=100, trust_env=False) as client:
            health = client.get("/health")
            health.raise_for_status()
            if not health.json()["agent_configured"]:
                raise RuntimeError("Configure OPENAI_API_KEY and OPENAI_MODEL before the live check.")
            print("PASS: FastAPI health and agent configuration", flush=True)
            response = client.post("/api/analyze", json={"prompt": (
                "Compare Singapore's sales for 2026-Q2 with target and calculate "
                "the percentage variance. Use the sales, target and variance tools. "
                "Include actual sales, target and percentage variance in your answer."
            )})
            if response.status_code != 200:
                # Only emit our backend's fixed error, never upstream details.
                raise RuntimeError(f"Live request failed: HTTP {response.status_code}; {response.json().get('detail', 'Unknown API error')}")
            answer = response.json()["answer"]
            for expected in ("200", "300", "33.33"):
                if expected not in answer:
                    raise AssertionError(f"Answer did not include expected figure {expected}.")
            print("PASS: live API answer includes actual 200, target 300 and variance magnitude 33.33%")
            print("ANSWER:", answer)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)
        print("Verification servers stopped.", flush=True)


if __name__ == "__main__":
    main()
