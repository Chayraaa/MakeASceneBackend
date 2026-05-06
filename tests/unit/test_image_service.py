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

    result = base64_to_binary_io(input_str)

    assert result.read() == b"hello"