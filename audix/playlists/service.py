from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import set_committed_value

from audix.database import SessionDep
from audix.episodes.models import Episode
from audix.episodes.service import EpisodeService, EpisodeServiceDep
from audix.podcasts.models import Podcast
from audix.shared.errors import ForbbiddenException, NotFoundException
from audix.users.models import User

from .models import Playlist
from .schemas import PlaylistCreate


class PlaylistService:
    def __init__(self, session: AsyncSession, episode_service: EpisodeService):
        self.session = session
        self.episode_service = episode_service

    async def create(
        self,
        data: PlaylistCreate,
        current_user: User,
    ) -> Playlist:
        new_playlist = Playlist(
            name=data.name,
            description=data.description,
            user_id=current_user.id
        )

        self.session.add(new_playlist)
        await self.session.commit()

        set_committed_value(new_playlist, "episodes", [])

        return new_playlist

    async def get_by_id(self, playlist_id: int, current_user: User) -> Playlist:
        query = (
            select(Playlist)
            .options(
                selectinload(Playlist.episodes)
                .joinedload(Episode.podcast)
                .joinedload(Podcast.author)
            )
            .where(Playlist.id == playlist_id)
        )
        result = await self.session.scalars(query)
        playlist_db = result.unique().first()

        if not playlist_db:
            raise NotFoundException(item="Playlist", item_id=playlist_id)

        if playlist_db.user_id != current_user.id:
            raise ForbbiddenException(detail="Esta playlist não lhe pertence")

        return playlist_db

    async def add_episode_to_playlist(
        self,
        playlist_id: int,
        episode_id: int,
        current_user: User,
    ) -> Playlist:
        playlist = await self.get_by_id(playlist_id, current_user)
        episode = await self.episode_service.get_by_id(
            episode_id=episode_id,
            current_user=current_user,
        )

        if episode not in playlist.episodes:
            playlist.episodes.append(episode)
            self.session.add(playlist)
            await self.session.commit()
        
        return playlist

    async def list_my_playlists(self, current_user: User) -> list[Playlist]:
        query = (
            select(Playlist)
            .options(
                selectinload(Playlist.episodes)
                .joinedload(Episode.podcast)
                .joinedload(Podcast.author)
            )
            .where(Playlist.user_id == current_user.id)
        )
        result = await self.session.scalars(query)
        
        return list(result.unique().all())

    async def remove_episode_from_playlist(
        self, playlist_id: int, episode_id: int, current_user: User
    ) -> Playlist:
        playlist = await self.get_by_id(playlist_id, current_user)
        
        episode = await self.episode_service.get_by_id(
            episode_id=episode_id,
            current_user=current_user,
        )

        if episode in playlist.episodes:
            playlist.episodes.remove(episode)
            self.session.add(playlist)
            await self.session.commit()
            
        return playlist

    async def delete(self, playlist_id: int, current_user: User) -> None:
        playlist = await self.get_by_id(playlist_id, current_user)
        
        await self.session.delete(playlist)
        await self.session.commit()

async def get_playlist_service(
    session: SessionDep,
    episode_service: EpisodeServiceDep,
):
    return PlaylistService(session=session, episode_service=episode_service)

PlaylistServiceDep = Annotated[PlaylistService, Depends(get_playlist_service)]
