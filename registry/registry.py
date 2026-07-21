"""
ColabBridge URL Registry

A tiny FastAPI service that stores the current Colab server's public URL so clients
can auto-connect without knowing the URL in advance.

Deploy once to Railway/Render/Fly.io. The Colab server POSTs its URL here on startup;
clients GET it to find where to connect.

Endpoints:
    POST /server-url?url=wss://...&token=xxx  → store URL
    GET  /server-url                          → return current URL
    GET  /health                              → liveness check

Environment variables:
    REGISTRY_TOKEN   Optional auth token. If set, POST requests must include ?token=<value>.
                     Leave unset to disable auth (fine for personal/team use).
"""

import os
import time
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ColabBridge URL Registry", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

REGISTRY_TOKEN: str = os.environ.get("REGISTRY_TOKEN", "")

_store: dict = {
    "url": None,
    "registered_at": None,
    "server_info": {},
}


@app.post("/server-url")
def set_url(
    url: str = Query(..., description="Public WebSocket or HTTPS URL of the Colab server"),
    token: str = Query("", description="Auth token (must match REGISTRY_TOKEN env var)"),
    info: Optional[str] = Query(None, description="Optional JSON metadata about the server"),
):
    if REGISTRY_TOKEN and token != REGISTRY_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")

    _store["url"] = url
    _store["registered_at"] = time.time()

    if info:
        import json
        try:
            _store["server_info"] = json.loads(info)
        except Exception:
            pass

    print(f"[registry] URL registered: {url}")
    return {"status": "ok", "url": url}


@app.get("/server-url")
def get_url():
    if _store["url"] is None:
        raise HTTPException(status_code=404, detail="No server URL registered yet")
    return {
        "url": _store["url"],
        "registered_at": _store["registered_at"],
        "age_s": round(time.time() - _store["registered_at"], 1) if _store["registered_at"] else None,
        "server_info": _store["server_info"],
    }


@app.delete("/server-url")
def clear_url(token: str = Query("", description="Auth token")):
    if REGISTRY_TOKEN and token != REGISTRY_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token")
    _store["url"] = None
    _store["registered_at"] = None
    _store["server_info"] = {}
    return {"status": "cleared"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "has_url": _store["url"] is not None,
        "url": _store["url"],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
