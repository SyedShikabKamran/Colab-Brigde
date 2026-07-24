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

## ✨ Why Colab Bridge?

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

---

# ⚡ Features

- 🚀 Turn notebooks into REST APIs
- 🌐 Automatic public URL using Cloudflare Tunnel
- 🔍 Automatic server discovery through Registry
- 📦 Simple Python decorators
- 💻 JavaScript client SDK
- 🔄 Handles changing Colab URLs automatically
- 🎯 Built with FastAPI
- ❤️ Completely open source

---

# 💡 What can you build?

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

# 🏃 Quick Start

## 1. Clone the repository

```bash
git clone https://github.com/SyedShikabKamran/Colab-Brigde.git
cd Colab-Brigde
```

---

## 2. Install

```bash
pip install -e server
```

---

## 3. Create your API

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

## 4. Run inside Google Colab

Once started, Colab Bridge automatically

- Starts a FastAPI server
- Opens a Cloudflare Tunnel
- Registers the public URL
- Waits for incoming requests

No manual networking required.

---

## 5. Call your API

```python
import requests

response = requests.post(
    "https://your-server/predict",
    files={"image": open("cat.jpg","rb")}
)

print(response.json())
```

Or use the included JavaScript client.

---

# 🏗 How it works

```
                 Client
                    │
             HTTP Request
                    │
                    ▼
            Registry Server
                    │
     Finds active Colab session
                    │
                    ▼
          Cloudflare Tunnel
                    │
                    ▼
         FastAPI inside Colab
                    │
                    ▼
             Your AI Model
                    │
                    ▼
              JSON Response
```

The Registry keeps track of the latest public URL, so your clients continue working even when Google Colab creates a new tunnel.

---

# 📁 Repository Structure

```
clients/
    JavaScript SDK

server/
    Python Bridge Library

registry/
    URL Registry Service

examples/
    Working example projects
```

---

# 📚 Examples

Included examples:

- Echo Server
- Image Classifier

More examples are welcome through community contributions.

---

# 🤝 Contributing

Contributions of all sizes are welcome.

Ideas include:

- Additional language SDKs
- Authentication
- WebSocket streaming
- Better deployment options
- Example projects
- Documentation improvements

Feel free to open an Issue or Pull Request.

---

# ⭐ Support the Project

If Colab Bridge helps your project,

⭐ Star the repository

🐛 Report bugs

💡 Suggest features

🤝 Contribute code

Every contribution helps improve the project for the community.

---

<div align="center">

###### Build your model once. Use it anywhere.
</div>