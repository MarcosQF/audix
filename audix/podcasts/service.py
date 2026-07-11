import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from audix.database import SessionDep
from audix.shared.errors import (
    ForbbiddenException,
    NotFoundException,
)
from audix.shared.minio.service import MinioService, MinioServiceDep
from audix.users.enums import UserRoles
from audix.users.models import User

from .models import Podcast
from .schemas import PodcastCreate, PodcastUpdate


class PodcastService:
    def __init__(
        self,
        session: AsyncSession,
        minio_service: MinioService,
    ):
        self.session = session
        self.minio_service = minio_service

    async def create(
        self,
        podcast_data: PodcastCreate,
        author_id: int,
    ) -> Podcast:

        db_podcast = Podcast(
            name=podcast_data.name,
            description=podcast_data.description,
            category=podcast_data.category,
            author_id=author_id,
        )

        self.session.add(db_podcast)

        await self.session.commit()
        await self.session.refresh(db_podcast)

        return db_podcast

    async def upload_podcast_image(
        self,
        file: UploadFile,
        podcast_id: int,
        user: User,
    ):
        db_podcast = await self.get_by_id(podcast_id=podcast_id)

        if (
            db_podcast.author_id != user.id
            and user.role.value != UserRoles.ADMIN
        ):
            raise ForbbiddenException(detail="Você não tem permissão para isso")

        if db_podcast.image_url:
            await self.delete_podcast_image(image_url=db_podcast.image_url)

        extensao = Path(file.filename or "").suffix
        
        object_name = f"{db_podcast.name}/images/{uuid.uuid4()}{extensao}"

        await self.minio_service.upload_file(
            file=file,
            object_name=object_name
        )

        db_podcast.image_url = object_name

        self.session.add(db_podcast)
        await self.session.commit()
        await self.session.refresh(db_podcast)

        return db_podcast

    async def delete_podcast_image(self, image_url: str):
        return await self.minio_service.delete_file(object_name=image_url)

    async def with_public_image_url(self, podcast: Podcast) -> Podcast:
        podcast.image_url = await self.minio_service.get_file_url(podcast.image_url or None)
        return podcast

    async def get_by_id(self, podcast_id: int) -> Podcast:
        query = (
            select(Podcast)
            .options(joinedload(Podcast.author))
            .where(Podcast.id == podcast_id)
        )

        podcast_db = await self.session.scalar(query)

        if not podcast_db:
            raise NotFoundException(item="Podcast", item_id=podcast_id)

        return podcast_db

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Podcast]:
        query = (
            select(Podcast)
            .offset(skip)
            .limit(limit)
            .options(joinedload(Podcast.author))
        )

        podcasts = await self.session.scalars(query) 
            
        return list(podcasts)

    async def update(
        self,
        podcast_id: int,
        podcast_data: PodcastUpdate,
        current_user: User,
    ) -> Podcast:
        podcast = await self.get_by_id(podcast_id)

        if (
            podcast.author_id != current_user.id
            and current_user.role.value != UserRoles.ADMIN
        ):
            raise ForbbiddenException(detail="Você não tem permissão para isso")

        update_dict = podcast_data.model_dump(exclude_unset=True)

        if "image" in update_dict:
            update_dict["image_url"] = update_dict.pop("image")

        for key, value in update_dict.items():
            setattr(podcast, key, value)

        await self.session.commit()
        await self.session.refresh(podcast)
        return podcast

    async def delete(self, podcast_id: int, current_user: User) -> bool:
        podcast = await self.get_by_id(podcast_id)

        if (
            podcast.author_id != current_user.id
            and current_user.role.value != UserRoles.ADMIN
        ):
            raise ForbbiddenException(detail="Você não tem permissão para isso")

        await self.session.delete(podcast)
        await self.session.commit()
        return True


async def get_podcast_service(
    session: SessionDep,
    minio_service: MinioServiceDep,
):
    return PodcastService(
        session=session,
        minio_service=minio_service,
    )

PodcastServiceDep = Annotated[PodcastService, Depends(get_podcast_service)]
