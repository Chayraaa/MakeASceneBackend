from unittest.mock import MagicMock, patch
from io import BytesIO
from app.repositories.storage.minio_image_storage import MinioImageStorage

def test_bucket_created_if_not_exists():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False

    with patch("app.repositories.storage.minio_image_storage.Minio", return_value=mock_client):
        storage = MinioImageStorage(bucket="test-bucket")

        mock_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_client.make_bucket.assert_called_once_with("test-bucket")

def test_save_image_calls_put_object():
    mock_client = MagicMock()

    with patch("app.repositories.storage.minio_image_storage.Minio", return_value=mock_client):
        storage = MinioImageStorage(bucket="test-bucket")

        image_data = BytesIO(b"image-data")

        result = storage.save_image("key123", image_data)

        mock_client.put_object.assert_called_once()
        assert result == "key123"

def test_get_image_reads_and_closes():
    mock_response = MagicMock()
    mock_response.read.return_value = b"file-data"

    mock_client = MagicMock()
    mock_client.get_object.return_value = mock_response

    with patch("app.repositories.storage.minio_image_storage.Minio", return_value=mock_client):
        storage = MinioImageStorage(bucket="test-bucket")

        result = storage.get_image("key123")

        assert result == b"file-data"

        mock_client.get_object.assert_called_once_with("test-bucket", "key123")
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()