from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from io import BytesIO
from typing import Protocol

from minio import Minio
from minio.error import MinioException, S3Error

from app.core.errors import ApiException, ErrorCode


@dataclass(slots=True)
class StoredObject:
    bucket_name: str
    object_key: str
    etag: str | None = None


class ObjectStorage(Protocol):
    async def upload_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject: ...

    async def delete_object(self, *, bucket_name: str, object_key: str) -> None: ...

    async def get_download_url(
        self,
        *,
        bucket_name: str,
        object_key: str,
        expires_in_seconds: int,
    ) -> str: ...

    async def get_object_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> bytes: ...


class MinioObjectStorage:
    def __init__(
        self,
        *,
        endpoint: str,
        access_key: str,
        secret_key: str,
        secure: bool,
    ) -> None:
        self.client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    async def _ensure_bucket(self, bucket_name: str) -> None:
        def _sync_ensure_bucket() -> None:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)

        try:
            await asyncio.to_thread(_sync_ensure_bucket)
        except MinioException as exc:
            raise ApiException(
                status_code=503,
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Object storage is not ready",
                details={"reason": str(exc)},
            ) from exc

    async def upload_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        await self._ensure_bucket(bucket_name)

        def _sync_upload() -> StoredObject:
            result = self.client.put_object(
                bucket_name,
                object_key,
                BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return StoredObject(
                bucket_name=bucket_name,
                object_key=object_key,
                etag=result.etag,
            )

        try:
            return await asyncio.to_thread(_sync_upload)
        except MinioException as exc:
            raise ApiException(
                status_code=503,
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to upload file to object storage",
                details={"reason": str(exc)},
            ) from exc

    async def delete_object(self, *, bucket_name: str, object_key: str) -> None:
        def _sync_delete() -> None:
            self.client.remove_object(bucket_name, object_key)

        try:
            await asyncio.to_thread(_sync_delete)
        except S3Error as exc:
            if exc.code == "NoSuchKey":
                return
            raise ApiException(
                status_code=503,
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to delete file from object storage",
                details={"reason": str(exc)},
            ) from exc
        except MinioException as exc:
            raise ApiException(
                status_code=503,
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to delete file from object storage",
                details={"reason": str(exc)},
            ) from exc

    async def get_download_url(
        self,
        *,
        bucket_name: str,
        object_key: str,
        expires_in_seconds: int,
    ) -> str:
        def _sync_presigned_url() -> str:
            return self.client.presigned_get_object(
                bucket_name,
                object_key,
                expires=timedelta(seconds=expires_in_seconds),
            )

        try:
            return await asyncio.to_thread(_sync_presigned_url)
        except MinioException as exc:
            raise ApiException(
                status_code=503,
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to generate download url",
                details={"reason": str(exc)},
            ) from exc

    async def get_object_bytes(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> bytes:
        def _sync_get_bytes() -> bytes:
            response = self.client.get_object(bucket_name, object_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        try:
            return await asyncio.to_thread(_sync_get_bytes)
        except MinioException as exc:
            raise ApiException(
                status_code=503,
                code=ErrorCode.SERVICE_UNAVAILABLE,
                message="Failed to read file from object storage",
                details={"reason": str(exc)},
            ) from exc
