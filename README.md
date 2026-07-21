# ColabBridge

Connect any app or website to GPU compute running on Google Colab — in under 20 lines of Python.

```
Your App / Website
      │  WebSocket / HTTP
      ▼
 URL Registry          ←  "where is the server?"
 (Railway/Render)
      │
      ▼
 Cloudflare Tunnel     ←  free public URL, no signup
      │
      ▼
 Google Colab T4       ←  your GPU compute runs here
```

---

## How it works

1. **You write a function** that does GPU work (inference, image processing, anything)
2. **ColabBridge wraps it** in a FastAPI server with a WebSocket or HTTP endpoint
3. **A free Cloudflare tunnel** gives it a public URL automatically — no account needed
4. **The URL registry** (one-time deploy) stores that URL so your client always knows where to connect
5. **Your app connects** via the JS client, which polls the registry and auto-reconnects

---

## Quick start

### Step 1 — Deploy the registry (one time)

The registry is a tiny service you own and control. Deploy it to Railway in about 2 minutes:

1. Go to [railway.app](https://railway.app) → sign up / log in
2. Click **New Project → Deploy from GitHub repo** → select your fork of this repo
3. Railway detects the `Dockerfile` automatically — set the **Root Directory** to `registry`
4. Add an environment variable (optional but recommended):
   - `REGISTRY_TOKEN` = any secret string you choose (e.g. `mytoken123`)
5. Click **Deploy** → wait ~30 seconds
6. Go to **Settings → Networking → Generate Domain** to get your public URL

Your registry URL will look like: `https://colabbridge-registry-production.up.railway.app`

> **Alternative — deploy via Railway CLI:**
> ```bash
> npm install -g @railway/cli
> railway login
> cd registry
> railway init        # creates a new Railway project
> railway variables set REGISTRY_TOKEN=mytoken123
> railway up          # deploys and prints the URL
> ```

Note the deployed URL — you'll use it in Step 2 and Step 3.

### Step 2 — Write your Colab server

Open a new Colab notebook (Runtime → T4 GPU) and run:

```python
!pip install colabbridge-server torch torchvision
```

```python
import base64, io, torch
from PIL import Image
from torchvision.models import resnet50, ResNet50_Weights
from colabbridge import ColabBridge

bridge = ColabBridge(
    registry_url="https://your-registry.up.railway.app",  # from Step 1
)

model, weights = None, None

def load():
    global model, weights
    weights = ResNet50_Weights.IMAGENET1K_V2
    model = resnet50(weights=weights).cuda().eval()

@bridge.post("/classify")
def classify(image_b64: str, top_k: int = 5) -> dict:
    image = Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
    tensor = weights.transforms()(image).unsqueeze(0).cuda()
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1)[0]
    top = probs.topk(top_k)
    cats = weights.meta["categories"]
    return {"predictions": [{"label": cats[i], "score": round(s.item(), 4)}
                             for i, s in zip(top.indices.tolist(), top.values.tolist())]}

bridge.run(warmup=load)
# Prints: [ColabBridge] ✓ Public URL: https://xxxx.trycloudflare.com
```

### Step 3 — Connect from your website

```html
<script>
class ColabBridgeClient {
  constructor(registryUrl) {
    this.registryUrl = registryUrl;
    this.serverUrl = null;
  }
  async getServerUrl() {
    while (true) {
      try {
        const r = await fetch(`${this.registryUrl}/server-url`);
        if (r.ok) return (await r.json()).url;
      } catch {}
      await new Promise(res => setTimeout(res, 4000));
    }
  }
  async post(path, body) {
    if (!this.serverUrl) this.serverUrl = await this.getServerUrl();
    const r = await fetch(this.serverUrl + path, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body)
    });
    return r.json();
  }
}

const client = new ColabBridgeClient('https://your-registry.up.railway.app');
const result = await client.post('/classify', { image_b64: '...' });
console.log(result.predictions); // [{label: "cat", score: 0.92}, ...]
</script>
```

Or install the npm package:
```bash
npm install colabbridge-client
```

```typescript
import { ColabBridgeClient } from 'colabbridge-client'

const client = new ColabBridgeClient('https://your-registry.up.railway.app')
const result = await client.post('/classify', { image_b64: imageB64 })
```

---

## WebSocket streaming (video / real-time)

For frame-by-frame streaming (webcam, video, sensors):

**Server:**
```python
@bridge.websocket("/ws")
def process_frame(data: bytes) -> dict:
    # data = raw JPEG bytes from the client
    result = my_model(data)
    return {"output": result}  # sent back as JSON

bridge.run()
```

**Client:**
```typescript
const client = new ColabBridgeClient('https://your-registry.up.railway.app')
await client.connect('/ws')

client.onMessage(result => {
  console.log(result.output)
})

// Send a JPEG frame
client.sendBytes(jpegBytes)
```

---

## API reference

### `ColabBridge` (server)

```python
bridge = ColabBridge(
    registry_url=None,       # URL of your deployed registry service
    registry_token="",       # Optional auth token (set REGISTRY_TOKEN env on registry)
    port=8000,               # uvicorn port
    enable_tunnel=True,      # set False to skip Cloudflare tunnel
)
```

| Method | Description |
|---|---|
| `@bridge.websocket(path)` | Register a `bytes → dict` function as a WebSocket endpoint |
| `@bridge.post(path)` | Register a typed function as an HTTP POST endpoint |
| `bridge.run(warmup=None)` | Start server + tunnel + register URL. `warmup` runs on the inference thread before accepting requests — use for model loading and torch.compile warmup |

### Built-in endpoints (always available)

| Endpoint | Description |
|---|---|
| `GET /health` | `{status, uptime_s, requests, public_url}` |
| `GET /stats` | `{uptime_s, requests, rps}` |

### `ColabBridgeClient` (JS/TS)

```typescript
const client = new ColabBridgeClient(registryUrl)

await client.connect('/ws')               // open WebSocket (auto-reconnects)
client.onMessage(data => ...)             // receive JSON results
client.sendBytes(buffer)                  // send raw bytes (e.g. JPEG frame)
client.sendText(str)                      // send text or JSON object
await client.post('/path', body)          // HTTP POST → parsed JSON
await client.health()                     // GET /health
client.disconnect()                       // close without reconnecting
```

### `RegistryClient` (Python)

```python
from colabbridge import RegistryClient

client = RegistryClient('https://your-registry.up.railway.app', token='...')
client.register('https://xxxx.trycloudflare.com')   # POST URL
url = client.get_url()                               # GET current URL
```

---

## Registry API

| Endpoint | Method | Description |
|---|---|---|
| `/server-url` | `POST ?url=...&token=...` | Register server URL |
| `/server-url` | `GET` | Get current URL |
| `/server-url` | `DELETE ?token=...` | Clear URL |
| `/health` | `GET` | Liveness + whether a URL is registered |

Set `REGISTRY_TOKEN` env var on the registry to enable token auth. Leave unset to disable.

---

## Examples

| Example | Description |
|---|---|
| [`examples/echo/`](examples/echo/) | WebSocket echo — no GPU needed |
| [`examples/image_classifier/`](examples/image_classifier/) | ResNet-50 ImageNet classifier with drag-drop web UI |

Each example has:
- `colab_server.ipynb` — open in Colab, set your registry URL, run
- `server.py` — same code as a plain Python script
- `web/index.html` — standalone demo page (no build step)

---

## GPU correctness: the `warmup` argument

If you use `torch.compile` (e.g. with `mode="reduce-overhead"` for CUDA graphs), always load your model inside the `warmup` callable passed to `bridge.run()`:

```python
def load():
    global model
    model = MyModel().cuda()
    model = torch.compile(model, mode="reduce-overhead")
    # Run a warmup pass here so the CUDA graph is captured
    with torch.no_grad():
        model(torch.randn(1, 3, 224, 224).cuda())

bridge.run(warmup=load)
```

**Why:** `torch.compile` with CUDA graphs binds the compiled graph to the OS thread that ran the warmup. ColabBridge uses a `ThreadPoolExecutor(max_workers=1)` so the warmup and every subsequent inference call always run on the same OS thread — but only if model loading happens inside `warmup`, not in module-level code that runs on the main thread.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Google Colab                                              │
│                                                            │
│  ColabBridge.run()                                         │
│    ├── warmup(fn)  → runs on inference thread              │
│    ├── uvicorn  → FastAPI on :8000                         │
│    ├── CloudflareTunnel → https://xxxx.trycloudflare.com   │
│    └── RegistryClient  → POST url to registry              │
│                                                            │
│  Request path (per frame/call):                            │
│    WebSocket bytes → asyncio.Lock → run_in_executor        │
│                              ↓                             │
│                    ThreadPoolExecutor(max_workers=1)        │
│                         your function                       │
│                              ↓                             │
│                    JSON response → WebSocket               │
└────────────────────────────────────────────────────────────┘
         ▲ WSS / HTTPS (Cloudflare TryCloudflare)
         │
┌────────┴───────────────────────────────────────────────────┐
│  URL Registry (Railway/Render)                             │
│    POST /server-url  ← Colab registers on startup          │
│    GET  /server-url  ← clients poll to find server         │
└────────────────────────────────────────────────────────────┘
         ▲ HTTP
         │
┌────────┴───────────────────────────────────────────────────┐
│  Your App / Website                                        │
│    ColabBridgeClient                                       │
│      polls registry → gets WSS URL → connects WebSocket    │
│      auto-reconnects if server restarts (new URL)          │
└────────────────────────────────────────────────────────────┘
```

---

## Repository structure

```
colabbridge/
├── server/                     # pip install colabbridge-server
│   ├── colabbridge/
│   │   ├── bridge.py           # ColabBridge class
│   │   ├── tunnel.py           # CloudflareTunnel
│   │   └── registry.py        # RegistryClient
│   ├── pyproject.toml
│   └── examples/
│       ├── echo_server.py
│       └── image_classifier_server.py
├── registry/                   # deploy once to Railway/Render/Fly
│   ├── registry.py
│   ├── Dockerfile
│   └── railway.json
├── clients/
│   └── js/                     # npm install colabbridge-client
│       └── src/index.ts
└── examples/
    ├── echo/                   # minimal WebSocket echo
    └── image_classifier/       # ResNet-50 + web UI
```

---

## License

MIT
