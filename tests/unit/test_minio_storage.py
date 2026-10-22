from unittest.mock import MagicMock, patch
from io import BytesIO
from app.repositories.storage.image.s3_image_storage import S3ImageStorage
from minio import S3Error
import pytest

def test_bucket_created_if_not_exists():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False

    with patch(
        "app.repositories.storage.image.s3_image_storage.Minio",
        return_value=mock_client
    ):
        storage = S3ImageStorage(bucket="test-bucket")

        storage._ensure_bucket()

        mock_client.bucket_exists.assert_called_once_with("test-bucket")
        mock_client.make_bucket.assert_called_once_with("test-bucket")

def test_save_image_calls_put_object():
    mock_client = MagicMock()

    with patch("app.repositories.storage.image.s3_image_storage.Minio", return_value=mock_client):
        storage = S3ImageStorage(bucket="test-bucket")

        image_data = BytesIO(b"image-data")

        result = storage.save_image("key123", image_data, "image/png")

        mock_client.put_object.assert_called_once()
        assert result == "key123"


def test_get_image_reads_and_closes():
    mock_response = MagicMock()
    mock_response.read.return_value = b"file-data"
    mock_response.headers.get.return_value = "image/png"

    mock_client = MagicMock()
    mock_client.get_object.return_value = mock_response

    with patch("app.repositories.storage.image.s3_image_storage.Minio", return_value=mock_client):
        storage = S3ImageStorage(bucket="test-bucket")

        data, mime = storage.get_image("key123")

        assert data == b"file-data"
        assert mime == "image/png"

        mock_client.get_object.assert_called_once_with("test-bucket", "key123")
        mock_response.close.assert_called_once()
        mock_response.release_conn.assert_called_once()


@pytest.mark.parametrize("operation", ["bucket_exists", "make_bucket"])
def test_failed_bucket_initialization_can_be_retried(operation):
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False
    failure = S3Error(
        response=None, code="InvalidAccessKeyId", message="Access key does not exist",
        resource="/images", request_id="request", host_id="host",
    )
    getattr(mock_client, operation).side_effect = [failure, True if operation == "bucket_exists" else None]
    with patch("app.repositories.storage.image.s3_image_storage.Minio", return_value=mock_client):
        storage = S3ImageStorage(bucket="images")
        with pytest.raises(S3Error):
            storage.save_image("key", BytesIO(b"image"), "image/png")
        assert storage._bucket_initialized is False
        mock_client.put_object.assert_not_called()
        assert storage.save_image("key", BytesIO(b"image"), "image/png") == "key"
        assert storage._bucket_initialized is True
        assert mock_client.bucket_exists.call_count == 2
        mock_client.put_object.assert_called_once()


def test_bucket_already_owned_race_is_successful_initialization():
    mock_client = MagicMock()
    mock_client.bucket_exists.return_value = False
    mock_client.make_bucket.side_effect = S3Error(
        response=None, code="BucketAlreadyOwnedByYou", message="Already owned",
        resource="/images", request_id="request", host_id="host",
    )
    with patch("app.repositories.storage.image.s3_image_storage.Minio", return_value=mock_client):
        storage = S3ImageStorage(bucket="images")
        storage._ensure_bucket()
        storage._ensure_bucket()
        assert storage._bucket_initialized is True
        mock_client.bucket_exists.assert_called_once()
