"""
Registry client — posts the public URL to the URL registry so clients can auto-connect.

The registry is a tiny FastAPI app (see /registry/) you deploy once to Railway/Render/Fly.
Clients poll it to find the current Colab server URL.
"""

from __future__ import annotations

import time
from typing import Optional


class RegistryClient:
    def __init__(self, registry_url: str, token: str = ""):
        self.registry_url = registry_url.rstrip("/")
        self.token = token

    def register(self, url: str, retries: int = 3) -> bool:
        """POST the public URL to the registry. Returns True on success."""
        import requests

        params: dict = {"url": url}
        if self.token:
            params["token"] = self.token

        for attempt in range(1, retries + 1):
            try:
                r = requests.post(
                    f"{self.registry_url}/server-url",
                    params=params,
                    timeout=10,
                )
                if r.ok:
                    print(f"[ColabBridge] Registered with registry.")
                    return True
                print(f"[ColabBridge] Registry returned {r.status_code}: {r.text}")
            except Exception as e:
                print(f"[ColabBridge] Registry unreachable (attempt {attempt}): {e}")
            if attempt < retries:
                time.sleep(2)
        return False

    def get_url(self) -> Optional[str]:
        """Fetch the current server URL from the registry."""
        import requests

        try:
            r = requests.get(f"{self.registry_url}/server-url", timeout=10)
            if r.ok:
                return r.json().get("url")
        except Exception:
            pass
        return None
