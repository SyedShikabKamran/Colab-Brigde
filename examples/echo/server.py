"""Echo server — paste this into a Colab cell or run as a script."""
from colabbridge import ColabBridge

bridge = ColabBridge(
    registry_url="https://your-registry.up.railway.app",  # replace with your registry URL
)


@bridge.websocket("/ws")
def echo(data: bytes) -> dict:
    text = data.decode("utf-8", errors="replace")
    return {"echo": text, "length": len(data)}


@bridge.post("/ping")
def ping(message: str = "hello") -> dict:
    return {"pong": message}


bridge.run()
