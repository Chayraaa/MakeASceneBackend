import base64
import binascii
from io import BytesIO
from uuid import uuid4
from app.metrics.operation_metrics import monitored

from app.repositories.interfaces.storage.image_storage_protocol import ImageStorageProtocol
from app.domain_models.site_account.SiteAccount import SiteAccount


def base64_to_binary_io(data_url: str):
    try:
        header, b64_data = data_url.split(",", 1)
        if not header.startswith("data:image/") or not header.endswith(";base64"):
            raise ValueError("Expected a base64 image data URL")
        mime = header[5:].split(";", 1)[0]
        binary = base64.b64decode(b64_data, validate=True)
        if not binary:
            raise ValueError("Image must not be empty")
        return mime, BytesIO(binary)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64 image data URL") from exc


class ImageService:
    def __init__(self, storage: ImageStorageProtocol, base_url: str = "http://127.0.0.1:5000", image_path: str = "v1/image"):
        self.storage = storage
        self.base_url = base_url.rstrip("/")
        self.image_path = image_path.lstrip("/").rstrip("/")

    def get_image_stream(self, key: str):
        return self.storage.get_image(key)

    def save_site_account_image(self, image_data: str, site_account: SiteAccount) -> str:
        return self._save_image(image_data, f"site_account/{site_account.id}")

    def _save_image(self, image_data: str, prefix: str) -> str:
        if image_data.startswith(("https://", "http://")):
            return image_data
        mime, binary = base64_to_binary_io(image_data)
        key = self._upload(f"{prefix}/{uuid4()}", binary, mime)
        return f"{self.base_url}/{self.image_path}/{key}"

    @monitored("image", "upload")
    def _upload(self, key, binary, mime):
        return self.storage.save_image(key, binary, mime)

    def save_event_image(self, image_data: str) -> str:
        return self._save_image(image_data, "events")

    def replace_event_images(self, data):
        if isinstance(data, dict):
            return {key: self.replace_event_images(value) for key, value in data.items()}
        if isinstance(data, list):
            return [self.replace_event_images(value) for value in data]
        if isinstance(data, str) and data.startswith("data:image/"):
            return self.save_event_image(data)
        return data
