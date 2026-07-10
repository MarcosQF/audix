import uuid
from pathlib import Path
from typing import Annotated
from urllib.parse import unquote

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
            duration=data.duration,
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
        
        if episode_db.audio_url and not episode_db.audio_url.startswith("http"):
            episode_db.audio_url = await self.minio_service.get_file_url(
                episode_db.audio_url
            )
        if episode_db.image_url and not episode_db.image_url.startswith("http"):
            episode_db.image_url = await self.minio_service.get_file_url(
                episode_db.image_url
            )
            
        episode_db.is_liked = True if like_exists else False
        return episode_db

    async def list_by_podcast(
        self,
        podcast_id: int,
        current_user: User,
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

        liked_episodes_ids = set()
        if current_user and episodes_list:
            episodes_ids = [ep.id for ep in episodes_list]
            
            query_likes = (
                select(episode_likes_association.c.episode_id)
                .where(
                    episode_likes_association.c.user_id == current_user.id,
                    episode_likes_association.c.episode_id.in_(episodes_ids)
                )
            )
            likes_result = await self.session.scalars(query_likes)
            liked_episodes_ids = set(likes_result.all())

        for episode in episodes_list:
            episode.is_liked = episode.id in liked_episodes_ids

            if episode.audio_url and not episode.audio_url.startswith("http"):
                episode.audio_url = await self.minio_service.get_file_url(
                    episode.audio_url
                )
            if episode.image_url and not episode.image_url.startswith("http"):
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
        query = (
            select(Episode)
            .options(joinedload(Episode.podcast))
            .where(Episode.id == episode_id)
        )
        db_episode = await self.session.scalar(query)
        
        if not db_episode:
            raise NotFoundException(item="Episódio", item_id=episode_id)

        if (
            db_episode.podcast.author_id != user.id
            and user.role.value != UserRoles.ADMIN.value
        ):
            raise ForbbiddenException(detail="Você não tem permissão para isso")

        if db_episode.image_url and not db_episode.image_url.startswith("http"):
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

        db_episode.image_url = await self.minio_service.get_file_url(
            db_episode.image_url
        )
        if db_episode.audio_url and not db_episode.audio_url.startswith("http"):
            db_episode.audio_url = await self.minio_service.get_file_url(
                db_episode.audio_url
            )

        return db_episode

    async def generate_audio_upload_url(
        self,
        episode_id: int,
        filename: str,
        current_user: User,
    ) -> dict:
        query = (
            select(Episode)
            .options(joinedload(Episode.podcast))
            .where(Episode.id == episode_id)
        )
        episode = await self.session.scalar(query)

        if not episode:
            raise NotFoundException(item="Episódio", item_id=episode_id)

        if (
            episode.podcast.author_id != current_user.id
            and current_user.role.value != UserRoles.ADMIN
        ):
            raise ForbbiddenException(
                detail="Sem permissão para alterar este episódio"
            )

        extensao = Path(filename).suffix
        
        object_name = (
            f"{episode.podcast.name}/episodes/{episode.title}-"
            f"{episode.episode_number}/audio/{uuid.uuid4()}{extensao}"
        )

        upload_url = await self.minio_service.get_upload_file_url(object_name)

        episode.audio_url = object_name
        self.session.add(episode)
        await self.session.commit()

        return {
            "upload_url": upload_url,
            "object_name": object_name
        }

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

        if db_episode.audio_url and db_episode.audio_url.startswith("http"):
            parts = db_episode.audio_url.split("podcasts/")[-1].split("?")[0]
            db_episode.audio_url = unquote(parts)
            
        if db_episode.image_url and db_episode.image_url.startswith("http"):
            parts = db_episode.image_url.split("podcasts/")[-1].split("?")[0]
            db_episode.image_url = unquote(parts)

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

        audio_path = episode.audio_url
        if audio_path and audio_path.startswith("http"):
            audio_path = unquote(
                audio_path.split("podcasts/")[-1].split("?")[0]
            )

        image_path = episode.image_url
        if image_path and image_path.startswith("http"):
            image_path = unquote(
                image_path.split("podcasts/")[-1].split("?")[0]
            )

        if audio_path:
            try:
                await self.minio_service.delete_file(audio_path)
            except Exception as e:
                print(f"Erro ao deletar arquivo de áudio do MinIO: {e}")

        if image_path:
            try:
                await self.minio_service.delete_file(image_path)
            except Exception as e:
                print(f"Erro ao deletar arquivo de imagem do MinIO: {e}")

        await self.session.delete(episode)
        await self.session.commit()

    async def update_progress(
        self, episode_id: int, user: User, current_time_seconds: int
    ) -> None:
        progress = await self.session.scalar(
            select(EpisodeProgress).where(
                EpisodeProgress.user_id == user.id,
                EpisodeProgress.episode_id == episode_id
            )
        )

        increment = 0
        if progress and current_time_seconds > progress.last_position_seconds:
            diff = current_time_seconds - progress.last_position_seconds
            increment = diff if diff <= 15 else 10
        
        stmt = (
            pg_insert(EpisodeProgress)
            .values(
                user_id=user.id,
                episode_id=episode_id,
                last_position_seconds=current_time_seconds,
                current_time_seconds=current_time_seconds
                if not progress
                else (progress.current_time_seconds + increment),
                view_counted=False,
            )
            .on_conflict_do_update(
                constraint="uq_user_episode_progress",
                set_={
                    "last_position_seconds": current_time_seconds,
                    "current_time_seconds": (
                        progress.current_time_seconds + increment
                    )
                    if progress
                    else current_time_seconds,
                },
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

        updated_progress = await self.session.scalar(
            select(EpisodeProgress).where(
                EpisodeProgress.user_id == user.id,
                EpisodeProgress.episode_id == episode_id
            )
        )

        if updated_progress and not updated_progress.view_counted:
            episode = await self.session.get(Episode, episode_id)
            
            if (
                episode 
                and episode.duration 
                and episode.duration > 0 
                and current_time_seconds > (episode.duration * 0.1)
            ):
                updated_progress.view_counted = True
                episode.views_count += 1
                
                self.session.add(updated_progress)
                self.session.add(episode)
                
                await self.session.commit()
                await self.session.refresh(episode)

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
                last_position_seconds=0,
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
