from unittest.mock import MagicMock
from app.services.image_service import ImageService


def test_get_image_stream():
    storage = MagicMock()

    service = ImageService(storage)

    storage.get_image.return_value = b"image-bytes"

    result = service.get_image_stream("abc123")

    storage.get_image.assert_called_once_with("abc123")
    assert result == b"image-bytes"

def test_image_service_url_cleanup():
    storage = MagicMock()

    service = ImageService(
        storage,
        base_url="http://localhost:5000/",
        image_path="/api/image/"
    )

    assert service.base_url == "http://localhost:5000"
    assert service.image_path == "api/image"

def test_base64_to_binary_io():
    from app.services.image_service import base64_to_binary_io
    import base64

    data = base64.b64encode(b"hello").decode()
    input_str = f"data:image/png;base64,{data}"

    mime, result = base64_to_binary_io(input_str)

    assert mime == "image/png"
    assert result.read() == b"hello"


def test_nested_event_images_and_urls():
    from app.repositories.storage.image.mem_image_storage import InMemoryImageStorage

    storage = InMemoryImageStorage("images")
    service = ImageService(storage)
    data = [{"items": [{"image": "data:image/png;base64,aGVsbG8="}]}, "https://example.com/a.png"]
    result = service.replace_event_images(data)
    assert result[1] == data[1]
    assert data[0]["items"][0]["image"].startswith("data:image/")
    url = result[0]["items"][0]["image"]
    assert storage.get_image(url.split("/v1/image/")[1]) == (b"hello", "image/png")


def test_invalid_base64_is_rejected_before_upload():
    import pytest

    storage = MagicMock()
    with pytest.raises(ValueError, match="Invalid base64"):
        ImageService(storage).save_event_image("data:image/png;base64,!!!")
    storage.save_image.assert_not_called()
