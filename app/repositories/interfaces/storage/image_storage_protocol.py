from typing import Protocol, Optional, BinaryIO


class ImageStorageProtocol(Protocol):
    def save_image(self, key: str, image_data: BinaryIO) -> str: ...

    def get_image(self, key: str): ...
