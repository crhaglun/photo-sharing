"""Azure Blob Storage operations."""

from pathlib import Path

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


class BlobStorage:
    """Azure Blob Storage client for photo uploads."""

    def __init__(self, account_name: str):
        """Initialize blob storage client.

        Args:
            account_name: Azure storage account name.
        """
        self.account_name = account_name
        credential = DefaultAzureCredential()
        account_url = f"https://{account_name}.blob.core.windows.net"
        self.client = BlobServiceClient(account_url, credential=credential)

    def upload_original(self, file_path: Path, photo_id: str) -> str:
        """Upload original photo to blob storage.

        Args:
            file_path: Path to the photo file.
            photo_id: SHA-256 hash of the photo (used as blob name).

        Returns:
            URL of the uploaded blob.
        """
        container_client = self.client.get_container_client("originals")

        # Determine content type based on extension
        suffix = file_path.suffix.lower()
        content_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
        }.get(suffix, "application/octet-stream")

        blob_client = container_client.get_blob_client(photo_id)

        with open(file_path, "rb") as f:
            blob_client.upload_blob(f, content_type=content_type, overwrite=True)

        return blob_client.url

    def upload_bytes(self, container: str, blob_name: str, data: bytes, content_type: str = "image/jpeg") -> str:
        """Upload bytes to blob storage.

        Args:
            container: Container name.
            blob_name: Blob name.
            data: Bytes to upload.
            content_type: Content type for the blob.

        Returns:
            URL of the uploaded blob.
        """
        container_client = self.client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data, content_type=content_type, overwrite=True)
        return blob_client.url

    def upload_thumbnail(self, photo_id: str, data: bytes) -> str:
        """Upload thumbnail image."""
        return self.upload_bytes("thumbnails", photo_id, data)

    def upload_default(self, photo_id: str, data: bytes) -> str:
        """Upload default view image."""
        return self.upload_bytes("default", photo_id, data)

    def exists(self, container: str, blob_name: str) -> bool:
        """Check if a blob exists.

        Args:
            container: Container name.
            blob_name: Blob name.

        Returns:
            True if blob exists.
        """
        container_client = self.client.get_container_client(container)
        blob_client = container_client.get_blob_client(blob_name)
        return blob_client.exists()
