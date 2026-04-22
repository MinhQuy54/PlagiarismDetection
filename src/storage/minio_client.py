"""MinIO client wrapper for file storage."""

import logging
import os
import tempfile
from typing import Optional
from pathlib import Path

from minio import Minio
from minio.error import S3Error

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class MinioClient:
    """MinIO client for file storage operations."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Minio] = None

    @property
    def client(self) -> Minio:
        """Get or create MinIO client."""
        if self._client is None:
            self._client = Minio(
                endpoint=self.settings.minio_url,
                access_key=self.settings.minio_access_key,
                secret_key=self.settings.minio_secret_key,
                secure=self.settings.minio_use_ssl,
            )
        return self._client

    def health_check(self) -> dict:
        """Check MinIO connection health."""
        try:
            buckets = self.client.list_buckets()
            return {
                "healthy": True,
                "buckets_count": len(buckets),
                "message": "MinIO connection successful",
            }
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return {"healthy": False, "error": str(e)}

    def bucket_exists(self, bucket_name: str) -> bool:
        """Check if bucket exists."""
        try:
            return self.client.bucket_exists(bucket_name)
        except S3Error as e:
            logger.error(f"Failed to check bucket: {e}")
            return False

    def object_exists(self, bucket_name: str, object_path: str) -> bool:
        """Check if object exists in bucket."""
        try:
            self.client.stat_object(bucket_name, object_path)
            return True
        except S3Error:
            return False

    def get_object_info(self, bucket_name: str, object_path: str) -> Optional[dict]:
        """Get object metadata."""
        try:
            stat = self.client.stat_object(bucket_name, object_path)
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
                "metadata": stat.metadata,
            }
        except S3Error as e:
            logger.error(f"Failed to get object info: {e}")
            return None

    def download_file(
        self, bucket_name: str, object_path: str, local_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Download file from MinIO to local path.

        Args:
            bucket_name: MinIO bucket name
            object_path: Path to object in bucket
            local_path: Optional local path to save file. If None, creates temp file.

        Returns:
            Local file path if successful, None otherwise.
        """
        temp_file_created = False
        try:
            if local_path is None:
                # Create temp file with same extension
                suffix = Path(object_path).suffix or ".pdf"
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, suffix=suffix
                )
                local_path = temp_file.name
                temp_file.close()
                temp_file_created = True

            self.client.fget_object(bucket_name, object_path, local_path)
            logger.info(f"Downloaded {bucket_name}/{object_path} to {local_path}")
            return local_path

        except S3Error as e:
            logger.error(f"Failed to download file: {e}")
            if temp_file_created and local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading file: {e}")
            if temp_file_created and local_path and os.path.exists(local_path):
                os.remove(local_path)
            return None

    def upload_file(
        self,
        bucket_name: str,
        object_path: str,
        file_path: str,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """
        Upload a file to MinIO from a local path.

        Args:
            bucket_name: MinIO bucket name
            object_path: Path in bucket
            file_path: Local path to file
            content_type: MIME type

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Ensure bucket exists
            if not self.bucket_exists(bucket_name):
                logger.info(f"Creating bucket: {bucket_name}")
                self.client.make_bucket(bucket_name)

            self.client.fput_object(
                bucket_name=bucket_name,
                object_name=object_path,
                file_path=file_path,
                content_type=content_type,
            )
            logger.info(f"Uploaded {file_path} to {bucket_name}/{object_path}")
            return True
        except S3Error as e:
            logger.error(f"Failed to upload file: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            return False

    def upload_fileobj(
        self,
        bucket_name: str,
        object_path: str,
        data,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> bool:
        """
        Upload a file-like object to MinIO.

        Args:
            bucket_name: MinIO bucket name
            object_path: Path in bucket
            data: File-like object or bytes
            length: Length of data
            content_type: MIME type

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Ensure bucket exists
            if not self.bucket_exists(bucket_name):
                logger.info(f"Creating bucket: {bucket_name}")
                self.client.make_bucket(bucket_name)

            self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_path,
                data=data,
                length=length,
                content_type=content_type,
            )
            logger.info(f"Uploaded fileobj to {bucket_name}/{object_path}")
            return True
        except S3Error as e:
            logger.error(f"Failed to upload fileobj: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False

    def download_file_to_memory(
        self, bucket_name: str, object_path: str
    ) -> Optional[bytes]:
        """
        Download file from MinIO to memory.

        Args:
            bucket_name: MinIO bucket name
            object_path: Path to object in bucket

        Returns:
            File content as bytes if successful, None otherwise.
        """
        response = None
        try:
            response = self.client.get_object(bucket_name, object_path)
            data = response.read()
            logger.info(f"Downloaded {bucket_name}/{object_path} to memory ({len(data)} bytes)")
            return data
        except S3Error as e:
            logger.error(f"Failed to download file to memory: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
        finally:
            if response:
                response.close()
                response.release_conn()

    def list_objects(
        self, bucket_name: str, prefix: str = "", recursive: bool = True
    ) -> list[dict]:
        """List objects in bucket with optional prefix filter."""
        try:
            objects = self.client.list_objects(
                bucket_name, prefix=prefix, recursive=recursive
            )
            return [
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "is_dir": obj.is_dir,
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Failed to list objects: {e}")
            return []

    def close(self):
        """Close the MinIO client and release resources."""
        if self._client:
            # MinIO client uses urllib3 connection pool internally
            # Setting to None allows garbage collection
            self._client = None
            logger.info("MinIO client closed")


# Singleton instance
_minio_client: Optional[MinioClient] = None


def get_minio_client() -> MinioClient:
    """Get singleton MinIO client instance."""
    global _minio_client
    if _minio_client is None:
        _minio_client = MinioClient()
    return _minio_client
