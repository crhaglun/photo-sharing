"""DINOv2 embeddings for image similarity search."""

import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModel


class DINOv2Embedder:
    """Generate image embeddings using DINOv2."""

    # Model produces 768-dimensional embeddings (ViT-B/14)
    EMBEDDING_DIM = 768

    def __init__(self, model_name: str = "facebook/dinov2-base", device: str | None = None):
        """Initialize DINOv2 model.

        Args:
            model_name: HuggingFace model name. Options:
                - facebook/dinov2-small (384 dim)
                - facebook/dinov2-base (768 dim) - default
                - facebook/dinov2-large (1024 dim)
                - facebook/dinov2-giant (1536 dim)
            device: Device to run on ('cuda', 'cpu', or None for auto).
        """
        self.model_name = model_name

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = device

        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(device)
        self.model.eval()

    def generate(self, image: Image.Image) -> list[float]:
        """Generate embedding for an image.

        Args:
            image: PIL Image to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        # Preprocess image
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        # Generate embedding
        with torch.no_grad():
            outputs = self.model(**inputs)
            # Use CLS token embedding (first token)
            embedding = outputs.last_hidden_state[:, 0, :]

        # Convert to list of floats
        return embedding.squeeze().cpu().tolist()


# Singleton instance for reuse across uploads
_embedder: DINOv2Embedder | None = None


def get_embedder() -> DINOv2Embedder:
    """Get or create the DINOv2 embedder singleton."""
    global _embedder
    if _embedder is None:
        _embedder = DINOv2Embedder()
    return _embedder


def generate_embedding(image: Image.Image) -> list[float]:
    """Generate embedding for an image using the singleton embedder.

    Args:
        image: PIL Image to embed.

    Returns:
        List of 768 floats representing the embedding vector.
    """
    return get_embedder().generate(image)
