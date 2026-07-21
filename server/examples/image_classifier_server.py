"""
ResNet-50 image classifier server.

Classifies images sent as base64 strings via HTTP POST.
Returns top-K ImageNet labels with confidence scores.

Run on Google Colab (T4 GPU):
    !pip install colabbridge-server torch torchvision
    # then run this script or paste into a cell
"""

import base64
import io

import torch
from PIL import Image
from torchvision.models import ResNet50_Weights, resnet50

from colabbridge import ColabBridge

bridge = ColabBridge(
    registry_url="https://your-registry.up.railway.app",  # replace with your registry URL
)

model = None
weights = None


def load_models():
    global model, weights
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[classifier] Loading ResNet-50 on {device}...")
    weights = ResNet50_Weights.IMAGENET1K_V2
    model = resnet50(weights=weights).to(device).eval()
    # Warmup pass so the first real request isn't slow.
    dummy = torch.randn(1, 3, 224, 224).to(device)
    with torch.no_grad():
        model(dummy)
    print("[classifier] Ready.")


@bridge.post("/classify")
def classify(image_b64: str, top_k: int = 5) -> dict:
    device = next(model.parameters()).device
    image_bytes = base64.b64decode(image_b64)
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    preprocess = weights.transforms()
    tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)

    probs = torch.softmax(logits, dim=1)[0]
    top = probs.topk(top_k)
    categories = weights.meta["categories"]

    return {
        "predictions": [
            {"label": categories[idx], "score": round(score.item(), 4)}
            for idx, score in zip(top.indices.tolist(), top.values.tolist())
        ]
    }


if __name__ == "__main__":
    bridge.run(warmup=load_models)
