from contextlib import asynccontextmanager

from aiobotocore.session import get_session


class MinioClient:
    def __init__(self, endpoint, access_key, secret_key, bucket_name):
        self.config = {
            "endpoint_url": endpoint,
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
        }
        self.bucket_name = bucket_name
        self.session = get_session()

    @asynccontextmanager
    async def get_client(self):
        async with self.session.create_client("s3", **self.config) as client:
            yield client
