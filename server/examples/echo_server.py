"""
Minimal echo server — no GPU required.

Run on Google Colab:
    !pip install colabbridge-server
    # then run this script or paste into a cell

Any message sent via WebSocket is echoed back with metadata.
"""

from colabbridge import ColabBridge

bridge = ColabBridge(
    registry_url="https://your-registry.up.railway.app",  # replace with your registry URL
)


@bridge.websocket("/ws")
def echo(data: bytes) -> dict:
    text = data.decode("utf-8", errors="replace")
    return {
        "echo": text,
        "length": len(data),
    }


@bridge.post("/ping")
def ping(message: str = "hello") -> dict:
    return {"pong": message}


if __name__ == "__main__":
    bridge.run()
