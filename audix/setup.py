from aiobotocore.session import get_session
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from audix.auth.hash import get_password_hash
from audix.users.models import User
from audix.users.schemas import UserRoles

from .settings import settings


async def create_initial_admin(session: AsyncSession):
    stmt = select(User).where(User.id == 1)
    db_user = await session.scalar(stmt)

    if not db_user:
        db_user = User(
            name=settings.ADMIN_NAME,
            email=settings.ADMIN_EMAIL,
            password=get_password_hash(settings.ADMIN_PASSWORD),
            role=UserRoles.ADMIN
        )

        session.add(db_user)
        await session.commit()


async def create_podcast_bucket():
    config = {
        "endpoint_url": "http://minio:9000",
        "aws_access_key_id": "minioadmin",
        "aws_secret_access_key": "minioadmin",
    }
    
    session = get_session()
    async with session.create_client("s3", **config) as s3:
        try:
            await s3.create_bucket(Bucket="podcasts") #type: ignore
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ["BucketAlreadyOwnedByYou", "BucketAlreadyExists"]:
                print("Bucket 'podcasts' já existe.")
            else:
                raise e
