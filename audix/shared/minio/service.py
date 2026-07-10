from datetime import timedelta
from typing import Annotated

import anyio
from fastapi import Depends, UploadFile

from audix.settings import settings

from .client import MinioClient


class MinioService:
    def __init__(
        self, client: MinioClient, public_client: MinioClient | None = None
    ):
        self.client = client
        self.public_client = public_client or client

    async def get_upload_file_url(
        self, object_name: str, expires_minutes: int = 15
    ) -> str:
        async with self.public_client.get_client() as s3:
            url = await s3.generate_presigned_url(  # type: ignore
                ClientMethod="put_object",
                Params={
                    "Bucket": self.client.bucket_name,
                    "Key": object_name,
                    "ContentType": "audio/mpeg",
                },
                ExpiresIn=expires_minutes * 60,
            )
            return url

    async def upload_file(self, file: UploadFile, object_name: str):
        async with self.client.get_client() as s3:
            await s3.put_object(  # type: ignore
                Bucket=self.client.bucket_name,
                Key=object_name,
                Body=await file.read(),
                ContentType=file.content_type,
            )
            return f"Arquivo {object_name} enviado com sucesso."

    async def get_file_url(self, object_name: str | None):
        if not object_name:
            return None

        async with self.public_client.get_client() as s3:
            url = await s3.generate_presigned_url(  # type: ignore
                "get_object",
                Params={
                    "Bucket": self.public_client.bucket_name,
                    "Key": object_name,
                },
                ExpiresIn=3600,
            )
            return url

    async def delete_file(self, object_name: str):
        async with self.client.get_client() as s3:
            await s3.delete_object(  # type: ignore
                Bucket=self.client.bucket_name, Key=object_name
            )
        return f"Arquivo {object_name} deletado com sucesso."


def get_minio_service():
    client = MinioClient(
        endpoint=settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        bucket_name="podcasts",
    )

    public_client = MinioClient(
        endpoint=settings.MINIO_PUBLIC_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        bucket_name="podcasts",
    )

    return MinioService(client=client, public_client=public_client)


MinioServiceDep = Annotated[MinioService, Depends(get_minio_service)]
