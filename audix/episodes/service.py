import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, UploadFile
from mutagen import File as MutagenFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from audix.database import SessionDep
from audix.podcasts.models import Podcast
from audix.podcasts.service import PodcastService, PodcastServiceDep
from audix.shared.errors import ForbbiddenException, NotFoundException
from audix.shared.minio.service import MinioService, MinioServiceDep
from audix.users.enums import UserRoles
from audix.users.models import User

from .models import Episode
from .schemas import EpisodeCreate


class EpisodeService:
    def __init__(
        self,
        session: AsyncSession,
        minio_service: MinioService,
        podcast_service: PodcastService,
    ):
        self.session = session
        self.minio_service = minio_service
        self.podcast_service = podcast_service

    async def create(
        self,
        data: EpisodeCreate,
        podcast_id: int,
        current_user: User,
    ) -> Episode:

        podcast_db = await self.podcast_service.get_by_id(podcast_id=podcast_id)

        if (
            podcast_db.author_id != current_user.id
            and current_user.role != UserRoles.ADMIN
        ):
            raise ForbbiddenException(detail="Você não tem permissão")

        new_episode = Episode(
            title=data.title,
            description=data.description,
            episode_number=data.episode_number,
            podcast_id=podcast_id,
        )

        self.session.add(new_episode)
        await self.session.commit()

        new_episode.podcast = podcast_db

        return new_episode

    async def get_by_id(self, episode_id: int) -> Episode:
        query = (
            select(Episode)
            .options(joinedload(Episode.podcast).joinedload(Podcast.author))
            .where(Episode.id == episode_id)
        )
        episode_db = await self.session.scalar(query)

        if not episode_db:
            raise NotFoundException(item="Episódio", item_id=episode_id)

        return episode_db

    async def list_by_podcast(
        self,
        podcast_id: int,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Episode]:
        
        await self.podcast_service.get_by_id(podcast_id=podcast_id)

        query = (
            select(Episode)
            .options(joinedload(Episode.podcast).joinedload(Podcast.author))
            .where(Episode.podcast_id == podcast_id)
            .order_by(Episode.episode_number.asc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.scalars(query)
        episodes_list = list(result.all())

        for episode in episodes_list:
            episode.audio_url = await self.minio_service.get_file_url(
                episode.audio_url
            )
            episode.image_url = await self.minio_service.get_file_url(
                episode.image_url
            )

        return episodes_list

    async def upload_episode_image(
        self,
        file: UploadFile,
        episode_id: int,
        user: User,
    ) -> Episode:
        db_episode = await self.get_by_id(episode_id=episode_id)

        if (
            db_episode.podcast.author_id != user.id
            and user.role.value != UserRoles.ADMIN.value
        ):
            raise ForbbiddenException(detail="Você não tem permissão para isso")

        if db_episode.image_url:
            await self.minio_service.delete_file(
                object_name=db_episode.image_url
            )

        extensao = Path(file.filename or "").suffix

        object_name = (
            f"{db_episode.podcast.name}/episodes/{db_episode.title}-"
            f"{db_episode.episode_number}/images/{uuid.uuid4()}{extensao}"
        )

        await self.minio_service.upload_file(file=file, object_name=object_name)

        db_episode.image_url = object_name

        self.session.add(db_episode)
        await self.session.commit()
        await self.session.refresh(db_episode)

        return db_episode

    async def upload_audio(
        self,
        episode_id: int,
        file: UploadFile,
        current_user: User,
    ) -> Episode:
        episode = await self.get_by_id(episode_id)

        if (
            episode.podcast.author_id != current_user.id
            and current_user.role.value != UserRoles.ADMIN
        ):
            raise ForbbiddenException(
                detail="Sem permissão para alterar este episódio"
            )

        try:
            audio_info = MutagenFile(file.file)
            if audio_info is not None and audio_info.info is not None:
                episode.duration = int(round(audio_info.info.length))
            else:
                episode.duration = 0
        except Exception as e:
            print(f"Erro ao extrair metadados de duração: {e}")
            episode.duration = 0

        await file.seek(0)

        extensao = Path(file.filename or "").suffix

        object_name = (
            f"{episode.podcast.name}/episodes/{episode.title}-"
            f"{episode.episode_number}/audio/{uuid.uuid4()}{extensao}"
        )

        if episode.audio_url:
            try:
                await self.minio_service.delete_file(episode.audio_url)
            except Exception as e:
                print(f"Erro ao deletar áudio antigo: {e}")

        await self.minio_service.upload_file(file=file, object_name=object_name)

        episode.audio_url = object_name

        self.session.add(episode)
        await self.session.commit()
        await self.session.refresh(episode)

        return episode

    async def delete(self, episode_id: int, current_user: User) -> None:
        episode = await self.get_by_id(episode_id=episode_id)

        if (
            episode.podcast.author_id != current_user.id
            and current_user.role.value != UserRoles.ADMIN.value
        ):
            raise ForbbiddenException(
                detail="Você não tem permissão para deletar este episódio"
            )

        if episode.audio_url:
            try:
                await self.minio_service.delete_file(episode.audio_url)
            except Exception as e:
                print(
                    f"Erro ao deletar arquivo de áudio do MinIO durante a remoção: {e}"
                )

        if episode.image_url:
            try:
                await self.minio_service.delete_file(episode.image_url)
            except Exception as e:
                print(
                    f"Erro ao deletar arquivo de imagem do MinIO durante a remoção: {e}"
                )

        await self.session.delete(episode)
        await self.session.commit()

async def get_episode_service(
    session: SessionDep,
    minio_service: MinioServiceDep,
    podcast_service: PodcastServiceDep,
):
    return EpisodeService(
        session=session,
        minio_service=minio_service,
        podcast_service=podcast_service,
    )


EpisodeServiceDep = Annotated[EpisodeService, Depends(get_episode_service)]
