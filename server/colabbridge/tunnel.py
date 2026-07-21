"""
Cloudflare TryCloudflare tunnel — free, no account, no signup.

Launches cloudflared as a subprocess, parses the public HTTPS URL from its output,
and keeps the process alive for the lifetime of the server. Installs cloudflared
automatically on Linux (Google Colab).
"""

import re
import shutil
import subprocess
import sys
import threading
import time


class CloudflareTunnel:
    def __init__(self, port: int = 8000):
        self.port = port
        self._url: str | None = None
        self._proc: subprocess.Popen | None = None

    def start(self, timeout: int = 90) -> str | None:
        """Start tunnel; block until the public URL is captured or timeout expires."""
        self._ensure_cloudflared()

        self._proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{self.port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        url_event = threading.Event()

        def _read():
            for line in self._proc.stdout:
                line = line.rstrip()
                m = re.search(r"https://[\w-]+\.trycloudflare\.com", line)
                if m:
                    self._url = m.group(0)
                    url_event.set()
                if any(w in line for w in ("ERR", "error", "failed")):
                    print(f"[tunnel] {line}", file=sys.stderr)

        threading.Thread(target=_read, daemon=True).start()

        if url_event.wait(timeout=timeout):
            return self._url

        print(f"[tunnel] Timed out after {timeout}s waiting for URL.", file=sys.stderr)
        return None

    def stop(self):
        if self._proc:
            self._proc.terminate()
            self._proc = None

    @staticmethod
    def _ensure_cloudflared():
        if shutil.which("cloudflared"):
            return
        if not sys.platform.startswith("linux"):
            raise RuntimeError(
                "cloudflared not found. Install from:\n"
                "https://developers.cloudflare.com/cloudflare-one/connections/"
                "connect-networks/downloads/"
            )
        print("[tunnel] Installing cloudflared...")
        subprocess.run(
            [
                "wget", "-q", "-O", "/tmp/cloudflared.deb",
                "https://github.com/cloudflare/cloudflared/releases/latest/download/"
                "cloudflared-linux-amd64.deb",
            ],
            check=True,
        )
        subprocess.run(["dpkg", "-i", "/tmp/cloudflared.deb"], capture_output=True, check=True)
        print("[tunnel] cloudflared installed.")
