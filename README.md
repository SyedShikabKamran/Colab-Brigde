<div align="center">

# 🚀 Colab Bridge

### Turn any Google Colab notebook into a live REST API in minutes.

Build AI applications without deploying servers. Run your model in Google Colab and access it from your website, mobile app, desktop application, or any HTTP client.

<p>
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg">
  <img src="https://img.shields.io/badge/FastAPI-Powered-009688">
  <img src="https://img.shields.io/badge/Google-Colab-F9AB00">
  <img src="https://img.shields.io/badge/Cloudflare-Tunnel-F38020">
  <img src="https://img.shields.io/badge/Open%20Source-MIT-success">
</p>

</div>

---

## Why Colab Bridge?

Deploying an AI model usually means learning cloud platforms, configuring servers, exposing ports, and managing infrastructure.

**Colab Bridge removes that complexity.**

Simply write your inference function, run your notebook, and your model becomes a public API.

```
             Google Colab
                  │
                  ▼
             Colab Bridge
                  │
                  ▼
           Public HTTPS API
                  │
                  ▼
     Web • Mobile • Desktop • Python
```

## Features

- 🚀 Turn notebooks into REST APIs
- 🌐 Automatic public URL using Cloudflare Tunnel
- 🔍 Automatic server discovery through Registry
- 🪄 Simple Python decorators
- 📦 JavaScript client SDK
- 🔄 Handles changing Colab URLs automatically
- ⚡ Built with FastAPI
- ❤️ Completely open source

---

## Architecture

```
                  Google Colab
                       │
                       ▼
             Colab Bridge Server
                       │
                       ▼
         Cloudflare Tunnel (HTTPS)
                       │
                       ▼
          Railway Registry Server
                       │
                       ▼
      Web • Mobile • Desktop • Python
```


## What can you build?

Colab Bridge works with almost any Python model.

| Project | Example Endpoint |
|----------|-----------------|
| Image Classification | `/classify` |
| Object Detection | `/detect` |
| OCR | `/ocr` |
| Background Removal | `/remove-bg` |
| Speech Recognition | `/transcribe` |
| Image Captioning | `/caption` |
| Text Generation | `/chat` |
| Stable Diffusion | `/generate` |

If your model runs in Colab, it can become an API.

---

# Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/SyedShikabKamran/Colab-Brigde.git
cd Colab-Brigde
```

---

### 2. Install Colab Bridge

```bash
pip install -e server
```

---

### 3. Deploy the Registry

Deploy the **`registry/`** directory to Railway.

After deployment, Railway will generate a URL similar to:

```text
https://your-registry.up.railway.app
```

This Registry keeps track of your active Colab server so your applications can always discover the latest API endpoint.

---

### 4. Configure your Colab Notebook

Add your Registry URL before starting Colab Bridge.

```python
import os

os.environ["REGISTRY_URL"] = "https://your-registry.up.railway.app"
```

This only needs to be configured once for your project.

---

### 5. Create your API

```python
from colabbridge import Bridge

bridge = Bridge()

@bridge.post("/predict")
def predict(image):
    return {
        "message": "Hello from Colab!"
    }

bridge.run()
```

---

### 6. Run inside Google Colab

Once started, Colab Bridge automatically:

- Starts a FastAPI server
- Creates a Cloudflare Tunnel
- Generates a public HTTPS endpoint
- Registers the endpoint with your Railway Registry
- Waits for incoming requests

No manual networking or tunnel configuration required.

---

### 7. Access your API

First, ask the Registry for the active Colab server.

```python
import requests

registry = "https://your-registry.up.railway.app"

server = requests.get(
    f"{registry}/server-url"
).json()["url"]

response = requests.post(
    f"{server}/predict",
    files={"image": open("cat.jpg", "rb")}
)

print(response.json())
```

Or simply use the included JavaScript SDK, which automatically discovers the active server.

---

## How it works

```
             Notebook Starts
                    │
                    ▼
         FastAPI starts in Colab
                    │
                    ▼
     Cloudflare creates public URL
                    │
                    ▼
   Register URL with Railway Registry
                    │
                    ▼
      Client requests active server
                    │
                    ▼
       Registry returns latest URL
                    │
                    ▼
      Client sends request to Colab
                    │
                    ▼
           AI Model processes data
                    │
                    ▼
            JSON response returned
```

The Registry stores the latest Cloudflare Tunnel URL created by your notebook. Whenever your application starts, it asks the Registry for the current server address before sending requests. If Google Colab disconnects and creates a new tunnel, clients automatically discover the new endpoint without any code changes.

---

## Repository Structure

```text
clients/
    JavaScript SDK

server/
    Python Bridge Library

registry/
    Railway Registry Service

examples/
    Example Projects
```

---

## Examples

Included examples:

- Echo Server
- Image Classifier

More examples are welcome through community contributions.

---

## Contributing

Contributions of all sizes are welcome.

Some ideas:

- 🌍 Additional language SDKs
- 🔐 Authentication
- 📡 WebSocket streaming
- 🐳 Docker deployment
- ☁️ Additional cloud providers
- 📚 More example projects
- 📝 Documentation improvements

Feel free to open an Issue or Pull Request.

---

## Support the Project

If Colab Bridge helps your project:

⭐ Star the repository

🐛 Report bugs

💡 Suggest features

🤝 Contribute improvements

Every contribution helps make Colab Bridge better for the open source community.

---

<div align="center">

###### Build your model once. Use it anywhere.
</div>
