import base64
from io import BytesIO
from app.repositories.interfaces.storage.image_storage_protocol import ImageStorageProtocol


def base64_to_binary_io(data_url: str):
    header, b64_data = data_url.split(",", 1)
    file_bytes = base64.b64decode(b64_data)
    return BytesIO(file_bytes)


class ImageService:
    def __init__(self, storage: ImageStorageProtocol, base_url: str = "http://127.0.0.1:5000", image_path: str = "api/image"):
        self.storage = storage
        self.base_url = base_url.rstrip("/")
        self.image_path = image_path.lstrip("/").rstrip("/")

    def get_image_stream(self, key: str):
        return self.storage.get_image(key)