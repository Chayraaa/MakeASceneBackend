import base64
from io import BytesIO
from uuid import uuid4

from app.repositories.interfaces.storage.image_storage_protocol import ImageStorageProtocol


def base64_to_binary_io(data_url: str):
    header, b64_data = data_url.split(",", 1)

    mime = header.split(";")[0].replace("data:", "")

    return mime, BytesIO(base64.b64decode(b64_data))


class ImageService:
    def __init__(self, storage: ImageStorageProtocol, base_url: str = "http://127.0.0.1:5000", image_path: str = "api/image"):
        self.storage = storage
        self.base_url = base_url.rstrip("/")
        self.image_path = image_path.lstrip("/").rstrip("/")

    def get_image_stream(self, key: str):
        return self.storage.get_image(key)

    def save_site_account_image(self, image_data: str):
        mime, image_data = base64_to_binary_io(image_data)
        key = self.storage.save_image(f"{self.image_path}/{uuid4()}", image_data, mime)
        return f"{self.base_url}/{key}"