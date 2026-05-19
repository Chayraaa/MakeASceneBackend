from datetime import timedelta
from typing import BinaryIO

from minio import Minio, S3Error


class MinioImageStorage:
    def __init__(self, bucket: str):
        self.client = Minio(
            endpoint="minio:9000",
            access_key="minio",
            secret_key="minio_password",
            secure=False
        )

        self.bucket = bucket
        self._bucket_initialized = False

    def _ensure_bucket(self):
        if self._bucket_initialized:
            return

        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)

        except S3Error as e:
            if e.code != "BucketAlreadyOwnedByYou":
                raise
        finally:
            self._bucket_initialized = True

    def save_image(self, key: str, image_data: BinaryIO) -> str:
        self._ensure_bucket()
        self.client.put_object(
            self.bucket,
            key,
            image_data,
            length=-1,
            part_size=10 * 1024 * 1024
        )

        return key

    def get_image(self, key: str):
        self._ensure_bucket()
        response = self.client.get_object(self.bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
