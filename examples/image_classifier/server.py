"""ResNet-50 image classifier — paste this into a Colab cell or run as a script."""
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
    print(f"Loading ResNet-50 on {device}...")
    weights = ResNet50_Weights.IMAGENET1K_V2
    model = resnet50(weights=weights).to(device).eval()
    dummy = torch.randn(1, 3, 224, 224).to(device)
    with torch.no_grad():
        model(dummy)
    print("ResNet-50 ready.")


@bridge.post("/classify")
def classify(image_b64: str, top_k: int = 5) -> dict:
    device = next(model.parameters()).device
    image = Image.open(io.BytesIO(base64.b64decode(image_b64))).convert("RGB")
    tensor = weights.transforms()(image).unsqueeze(0).to(device)

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


bridge.run(warmup=load_models)
