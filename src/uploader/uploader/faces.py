"""Face detection using InsightFace."""

from dataclasses import dataclass

import numpy as np
from insightface.app import FaceAnalysis
from PIL import Image


@dataclass
class DetectedFace:
    """A detected face with bounding box and embedding."""

    bbox_x: int
    bbox_y: int
    bbox_width: int
    bbox_height: int
    embedding: list[float]


class FaceDetector:
    """Detect faces and extract embeddings using InsightFace."""

    # InsightFace buffalo_l model produces 512-dimensional embeddings
    EMBEDDING_DIM = 512

    def __init__(self, det_size: tuple[int, int] = (640, 640)):
        """Initialize InsightFace model.

        Args:
            det_size: Detection input size (width, height). Larger = more accurate but slower.
        """
        self.det_size = det_size
        self.app = FaceAnalysis(
            name="buffalo_l",
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=0, det_size=det_size)

    def detect(self, image: Image.Image) -> list[DetectedFace]:
        """Detect faces in an image.

        Args:
            image: PIL Image to analyze.

        Returns:
            List of DetectedFace objects.
        """
        # Convert PIL Image to numpy array (RGB)
        img_array = np.array(image)

        # InsightFace expects BGR format
        if len(img_array.shape) == 3 and img_array.shape[2] == 3:
            img_array = img_array[:, :, ::-1]  # RGB to BGR

        # Detect faces
        faces = self.app.get(img_array)

        results = []
        for face in faces:
            # Extract bounding box (x1, y1, x2, y2)
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox

            # Convert to x, y, width, height
            bbox_x = max(0, x1)
            bbox_y = max(0, y1)
            bbox_width = x2 - x1
            bbox_height = y2 - y1

            # Extract embedding (512 dimensions)
            embedding = face.embedding.tolist()

            results.append(DetectedFace(
                bbox_x=bbox_x,
                bbox_y=bbox_y,
                bbox_width=bbox_width,
                bbox_height=bbox_height,
                embedding=embedding,
            ))

        return results


# Singleton instance for reuse across uploads
_detector: FaceDetector | None = None


def get_detector() -> FaceDetector:
    """Get or create the face detector singleton."""
    global _detector
    if _detector is None:
        _detector = FaceDetector()
    return _detector


def detect_faces(image: Image.Image) -> list[DetectedFace]:
    """Detect faces in an image using the singleton detector.

    Args:
        image: PIL Image to analyze.

    Returns:
        List of DetectedFace objects with bounding boxes and 512-dim embeddings.
    """
    return get_detector().detect(image)
