# ColabBridge URL Registry

A tiny FastAPI service you deploy **once** and control. It stores the current Colab server's
public URL so clients can find it automatically — without you hardcoding a URL anywhere.

---

## What it does

| Endpoint | Who calls it | Why |
|---|---|---|
| `POST /server-url?url=...` | Colab server (on startup) | "I'm running at this URL" |
| `GET /server-url` | Your app / website | "Where is the server right now?" |
| `GET /health` | Railway health check | Liveness probe |

---

## Deploy to Railway (recommended)

Railway gives you a persistent HTTPS URL for free on the Hobby plan ($5/mo) or free trial.

### Option A — Deploy from GitHub (easiest)

1. Fork this repo on GitHub
2. Go to [railway.app](https://railway.app) → **New Project → Deploy from GitHub repo**
3. Select your fork
4. Set **Root Directory** to `registry` (Railway will find the Dockerfile there)
5. *(Optional)* Add environment variable: `REGISTRY_TOKEN` = your secret token
6. Click **Deploy** — Railway builds and starts the service (~30s)
7. Go to **Settings → Networking → Generate Domain**

Your URL: `https://your-project-name.up.railway.app`

### Option B — Deploy via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Log in
railway login

# From the registry/ directory:
cd registry
railway init          # creates a new Railway project, links this folder

# Set the optional auth token (anyone who knows this token can register a URL)
railway variables set REGISTRY_TOKEN=pick-a-secret-here

# Deploy
railway up
```

After deploy, get your URL:
```bash
railway domain        # generates a public *.up.railway.app URL
```

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `REGISTRY_TOKEN` | No | If set, `POST /server-url` requires `?token=<value>`. Clients (GET) do not need a token. Leave unset to disable auth entirely. |
| `PORT` | Auto (Railway sets it) | Port uvicorn listens on. Railway injects this automatically — do not set it manually. |

---

## Using your registry token

**In your Colab notebook / server script:**
```python
from colabbridge import ColabBridge

bridge = ColabBridge(
    registry_url="https://your-project.up.railway.app",
    registry_token="pick-a-secret-here",   # must match REGISTRY_TOKEN
)
```

**The token is only needed to register (POST), not to read (GET).** Your website or app
does not need the token — it only calls `GET /server-url`.

---

## Verify it's working

```bash
# Health check
curl https://your-project.up.railway.app/health

# Check if a URL is registered
curl https://your-project.up.railway.app/server-url

# Manually register a test URL (with token)
curl -X POST "https://your-project.up.railway.app/server-url?url=https://test.trycloudflare.com&token=pick-a-secret-here"
```

---

## Alternative deployment targets

The registry is a standard FastAPI app — it runs anywhere Python runs.

| Platform | Command |
|---|---|
| **Render** | Connect GitHub repo → set Root Dir to `registry` → free tier works |
| **Fly.io** | `fly launch` from `registry/` → `fly deploy` |
| **VPS / any server** | `pip install fastapi uvicorn && uvicorn registry:app --host 0.0.0.0 --port 8080` |
| **Local (for testing)** | Same as VPS — expose via `ngrok http 8080` if needed |

---

## Notes

- The registry keeps the URL **in memory** — if the service restarts, the URL is cleared
  until the Colab server re-registers. This is fine: Colab re-registers on every session start.
- If you want the URL to survive registry restarts (e.g. Railway sleep), you can add a
  one-line Redis/SQLite backend to `registry.py` — the `_store` dict is the only thing to replace.
- One registry can serve multiple projects — just use different tokens or deploy separate instances.
