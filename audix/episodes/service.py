import uuid
from pathlib import Path
from typing import Annotated

from fastapi import Depends, UploadFile
from mutagen import File as MutagenFile
from sqlalchemy import delete, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from audix.database import SessionDep
from audix.podcasts.models import Podcast
from audix.podcasts.service import PodcastService, PodcastServiceDep
from audix.shared.errors import (
    ForbbiddenException,
    NotFoundException,
    UnauthorizedException,
)
from audix.shared.minio.service import MinioService, MinioServiceDep
from audix.users.enums import UserRoles
from audix.users.models import User

from .models import Episode, EpisodeProgress, episode_likes_association
from .schemas import EpisodeCreate, EpisodeProgressResponse


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

    async def get_by_id(
        self,
        episode_id: int,
        current_user: User | None = None,
    ) -> Episode:
        query = (
            select(Episode)
            .options(joinedload(Episode.podcast).joinedload(Podcast.author))
            .where(Episode.id == episode_id)
        )
        episode_db = await self.session.scalar(query)

        if not episode_db:
            raise NotFoundException(item="Episódio", item_id=episode_id)

        if not current_user:
            raise UnauthorizedException(detail='Faça o login')

        query_like = select(episode_likes_association).where(
            episode_likes_association.c.user_id == current_user.id,
            episode_likes_association.c.episode_id == episode_id
        )
        like_exists = await self.session.scalar(query_like)
        
        episode_db.audio_url = await self.minio_service.get_file_url(
            episode_db.audio_url
        )
        episode_db.image_url = await self.minio_service.get_file_url(
            episode_db.image_url
        )
        episode_db.is_liked = True if like_exists else False

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
        db_episode = await self.get_by_id(
            episode_id=episode_id, current_user=user
        )

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
        episode = await self.get_by_id(
            episode_id=episode_id, current_user=current_user
        )

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

    async def toggle_like(self, current_user: User, episode_id: int):
        db_episode = await self.get_by_id(
            episode_id=episode_id, current_user=current_user
        )

        query_check_like = (
            select(episode_likes_association)
            .where(
                episode_likes_association.c.user_id == current_user.id,
                episode_likes_association.c.episode_id == episode_id
            )
        )

        like_exists = await self.session.scalar(query_check_like)

        if like_exists:
            statement_delete = (
                delete(episode_likes_association)
                .where(
                    episode_likes_association.c.user_id == current_user.id,
                    episode_likes_association.c.episode_id == episode_id
                )
            )
            await self.session.execute(statement_delete)
            
            db_episode.likes_count = max(0, db_episode.likes_count - 1)
            action = "unliked"
            
        else:
            statement_insert = (
                insert(episode_likes_association)
                .values(
                    user_id=current_user.id,
                    episode_id=episode_id
                )
            )
            await self.session.execute(statement_insert)
            
            db_episode.likes_count += 1
            action = "liked"

        self.session.add(db_episode)
        await self.session.commit()
        await self.session.refresh(db_episode)

        return {
            "action": action,
            "likes_count": db_episode.likes_count
        }

    async def delete(self, episode_id: int, current_user: User) -> None:
        episode = await self.get_by_id(
            episode_id=episode_id, current_user=current_user
        )

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

    async def update_progress(
            self, episode_id: int, user: User, current_time_seconds: int
    ) -> None:
        episode = await self.get_by_id(episode_id=episode_id, current_user=user)

        stmt = pg_insert(EpisodeProgress).values(
            user_id=user.id,
            episode_id=episode_id,
            current_time_seconds=current_time_seconds,
            view_counted=False
        )
        
        stmt = stmt.on_conflict_do_update(
            constraint="uq_user_episode_progress",
            set_={"current_time_seconds": current_time_seconds}
        )

        await self.session.execute(stmt)

        query_check = select(EpisodeProgress).where(
            EpisodeProgress.user_id == user.id,
            EpisodeProgress.episode_id == episode_id
        )

        progress = await self.session.scalar(query_check)

        if (
            progress
            and not progress.view_counted
            and current_time_seconds > (episode.duration * 0.1)
        ):
            progress.view_counted = True
            
            episode.views_count += 1
            
            self.session.add(progress)
            self.session.add(episode)
            
        await self.session.commit()

    async def get_progress(
        self, episode_id: int, user: User
    ) -> EpisodeProgressResponse:
        await self.get_by_id(episode_id=episode_id, current_user=user)

        query = select(EpisodeProgress).where(
            EpisodeProgress.user_id == user.id,
            EpisodeProgress.episode_id == episode_id
        )
        progress = await self.session.scalar(query)

        if not progress:
            return EpisodeProgressResponse(
                episode_id=episode_id,
                current_time_seconds=0,
                view_counted=False
            )

        return EpisodeProgressResponse.model_validate(progress)

    async def get_episode_metrics(
        self, episode_id: int, current_user: User
    ) -> dict:
        episode = await self.get_by_id(
            episode_id=episode_id, current_user=current_user
        )
        if (
            episode.podcast.author_id != current_user.id
            and current_user.role != UserRoles.ADMIN
        ):
            raise ForbbiddenException(detail="Você não é o dono deste podcast.")

        query_avg = (
            select(
                func.avg(EpisodeProgress.current_time_seconds).label("avg_time"),
                func.count(EpisodeProgress.id).label("total_listeners")
            )
            .where(EpisodeProgress.episode_id == episode_id)
        )
        stats = await self.session.execute(query_avg)
        row = stats.first()
        
        avg_seconds = float(row.avg_time or 0) if row else 0.0
        
        completion_rate = 0.0
        if episode.duration and episode.duration > 0:
            completion_rate = (avg_seconds / episode.duration) * 100

        return {
            "episode_id": episode.id,
            "total_views": episode.views_count,
            "total_likes": episode.likes_count,
            "average_time_listened_seconds": round(avg_seconds, 2),
            "completion_rate_percentage": round(completion_rate, 2)
        }

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
