"""
ColabBridge — core framework class.

Usage:
    from colabbridge import ColabBridge

    bridge = ColabBridge(registry_url="https://your-registry.up.railway.app")

    @bridge.websocket("/ws")
    def process(data: bytes) -> dict:
        return {"result": data.decode()}

    @bridge.post("/infer")
    def infer(image_b64: str, threshold: float = 0.3) -> dict:
        return {"label": "cat", "score": 0.97}

    bridge.run(warmup=load_models)
"""

from __future__ import annotations

import asyncio
import inspect
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import Callable, Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import create_model

from .tunnel import CloudflareTunnel
from .registry import RegistryClient


class ColabBridge:
    """
    Wraps FastAPI + Cloudflare tunnel + URL registry into a single callable.

    GPU-safe by design: all decorated functions run on a single dedicated OS thread
    (ThreadPoolExecutor(max_workers=1)) so torch.compile CUDA graphs — which are
    bound to the OS thread that ran the warmup — always execute on the correct thread.
    An asyncio.Lock serializes concurrent requests so only one runs at a time.

    Args:
        registry_url:   URL of your deployed registry service. Optional — if omitted,
                        the tunnel URL is printed but not registered anywhere.
        registry_token: Token to authenticate with the registry (set REGISTRY_TOKEN
                        env var on the registry side). Leave empty to disable auth.
        port:           Port uvicorn listens on (default 8000).
        enable_tunnel:  Set False to skip Cloudflare tunnel (local-only or bring-your-own
                        tunnel).
    """

    def __init__(
        self,
        registry_url: Optional[str] = None,
        registry_token: str = "",
        port: int = 8000,
        enable_tunnel: bool = True,
    ):
        self.registry_url = registry_url
        self.registry_token = registry_token
        self.port = port
        self.enable_tunnel = enable_tunnel

        # Single OS thread for all inference — required for torch CUDA graph correctness.
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cb-infer")
        # Prevents concurrent GPU use when multiple WebSocket frames arrive simultaneously.
        self._lock: asyncio.Lock | None = None  # created inside the event loop
        self._public_url: Optional[str] = None
        self._start_time = time.time()
        self._request_count = 0

        @asynccontextmanager
        async def _lifespan(app: FastAPI):
            # Create the lock inside the running event loop (asyncio.Lock is loop-bound).
            self._lock = asyncio.Lock()
            yield

        self.app = FastAPI(title="ColabBridge Server", lifespan=_lifespan)
        self._register_builtins()

    # ── Built-in endpoints ────────────────────────────────────────────────────

    def _register_builtins(self):
        bridge = self

        @self.app.get("/health")
        async def _health():
            return {
                "status": "ok",
                "uptime_s": round(time.time() - bridge._start_time, 1),
                "requests": bridge._request_count,
                "public_url": bridge._public_url,
            }

        @self.app.get("/stats")
        async def _stats():
            uptime = time.time() - bridge._start_time
            return {
                "uptime_s": round(uptime, 1),
                "requests": bridge._request_count,
                "rps": round(bridge._request_count / uptime, 2) if uptime > 0 else 0,
            }

    # ── Decorators ────────────────────────────────────────────────────────────

    def websocket(self, path: str = "/ws"):
        """
        Register a synchronous function as a WebSocket streaming endpoint.

        The function receives raw bytes and must return a JSON-serializable dict.
        Handles connection lifecycle, per-frame error recovery, and graceful disconnect.

        Example::

            @bridge.websocket("/ws")
            def process(data: bytes) -> dict:
                result = my_model(data)
                return {"output": result}
        """
        def decorator(func: Callable[[bytes], dict]):
            bridge = self

            @self.app.websocket(path)
            async def _handler(ws: WebSocket):
                await ws.accept()
                loop = asyncio.get_running_loop()
                try:
                    while True:
                        data = await ws.receive_bytes()
                        bridge._request_count += 1
                        try:
                            async with bridge._lock:
                                result = await loop.run_in_executor(
                                    bridge._executor, func, data
                                )
                        except Exception as e:
                            import traceback
                            traceback.print_exc()
                            result = {"error": f"{type(e).__name__}: {e}"}

                        try:
                            await ws.send_text(json.dumps(result))
                        except RuntimeError as e:
                            # Client closed the socket while this frame was processing.
                            if "websocket.close" in str(e):
                                break
                            raise
                except WebSocketDisconnect:
                    pass

            return func
        return decorator

    def post(self, path: str):
        """
        Register a synchronous function as an HTTP POST endpoint.

        Function parameters with type annotations become the JSON body schema.
        Default values become optional fields.

        Example::

            @bridge.post("/classify")
            def classify(image_b64: str, top_k: int = 5) -> dict:
                return {"labels": [...]}
        """
        def decorator(func: Callable):
            bridge = self
            sig = inspect.signature(func)

            # Build a Pydantic model from the function signature.
            fields: dict = {}
            for name, param in sig.parameters.items():
                annotation = (
                    param.annotation
                    if param.annotation != inspect.Parameter.empty
                    else str
                )
                if param.default != inspect.Parameter.empty:
                    fields[name] = (annotation, param.default)
                else:
                    fields[name] = (annotation, ...)

            RequestModel = create_model(f"{func.__name__}_Request", **fields)

            @self.app.post(path)
            async def _handler(body: RequestModel):
                bridge._request_count += 1
                kwargs = body.model_dump()
                loop = asyncio.get_running_loop()
                try:
                    async with bridge._lock:
                        result = await loop.run_in_executor(
                            bridge._executor, lambda: func(**kwargs)
                        )
                    return result
                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    return {"error": f"{type(e).__name__}: {e}"}

            return func
        return decorator

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self, warmup: Optional[Callable] = None):
        """
        Start the server, Cloudflare tunnel, and URL registry registration.

        Args:
            warmup: Optional callable executed in the inference executor BEFORE the
                    server starts accepting requests. Use to load models, pre-allocate
                    GPU memory, or run torch.compile warmup passes. Runs on the SAME
                    OS thread as all subsequent inference calls — required for torch's
                    CUDA graph correctness (the graph is captured by thread identity).

        Example::

            def load():
                global model
                model = MyModel().cuda()
                # torch.compile warmup goes here

            bridge.run(warmup=load)
        """
        if warmup is not None:
            print("[ColabBridge] Running warmup on inference thread...")
            future = self._executor.submit(warmup)
            future.result()  # block; propagates exceptions
            print("[ColabBridge] Warmup done.")

        threading.Thread(target=self._tunnel_and_register, daemon=True).start()

        uvicorn.run(self.app, host="0.0.0.0", port=self.port, log_level="info")

    def _tunnel_and_register(self):
        """Polls for server readiness, then starts tunnel and registers URL."""
        import requests

        # Wait for uvicorn to be up (up to 3 min).
        for _ in range(90):
            time.sleep(2)
            try:
                if requests.get(f"http://localhost:{self.port}/health", timeout=2).ok:
                    break
            except Exception:
                pass
        else:
            print("[ColabBridge] Server did not start — tunnel skipped.", flush=True)
            return

        if not self.enable_tunnel:
            print(f"[ColabBridge] Server ready on port {self.port} (tunnel disabled).")
            return

        tunnel = CloudflareTunnel(port=self.port)
        url = tunnel.start()
        if not url:
            print("[ColabBridge] Tunnel failed to start.", flush=True)
            return

        self._public_url = url
        print(f"\n[ColabBridge] ✓ Public URL: {url}", flush=True)

        if self.registry_url:
            client = RegistryClient(self.registry_url, self.registry_token)
            client.register(url)
        else:
            print("[ColabBridge] No registry_url set — clients must connect manually.")
