from typing import BinaryIO


class InMemoryImageStorage:
    def __init__(self, bucket: str):
        self.bucket = bucket
        self._store = {}  # key -> bytes

    def save_image(self, key: str, image_data: BinaryIO) -> str:
        self._store[key] = image_data.read()
        return key

    def get_image(self, key: str):
        return self._store.get(key)

    def bucket_exists(self):
        return True