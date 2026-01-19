"""SHA-256 hashing for photo identification."""

import hashlib
from pathlib import Path


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file.

    Args:
        file_path: Path to the file to hash.

    Returns:
        Lowercase hex string of the SHA-256 hash (64 characters).
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()
