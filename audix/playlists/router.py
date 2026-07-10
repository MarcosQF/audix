from http import HTTPStatus

from fastapi import APIRouter, Response

from audix.shared.permissions import RequireUser

from .schemas import ListPlaylists, PlaylistCreate, PlaylistResponse, PlaylistUpdate
from .service import PlaylistServiceDep

router = APIRouter(prefix="/playlists", tags=["Playlists"])


@router.post(
    "", response_model=PlaylistResponse, status_code=HTTPStatus.CREATED
)
async def create_playlist(
    data: PlaylistCreate,
    service: PlaylistServiceDep,
    current_user: RequireUser,
):
    return await service.create(data=data, current_user=current_user)


@router.get("", response_model=ListPlaylists)
async def list_playlists(
    service: PlaylistServiceDep,
    current_user: RequireUser,
):
    playlists = await service.list_my_playlists(current_user=current_user)

    return {"quantity": len(playlists), "playlists": playlists}


@router.get("/{playlist_id}", response_model=PlaylistResponse)
async def get_playlist(
    playlist_id: int,
    service: PlaylistServiceDep,
    current_user: RequireUser,
):
    return await service.get_by_id(playlist_id=playlist_id, current_user=current_user)


@router.patch("/{playlist_id}", response_model=PlaylistResponse)
async def update_playlist(
    playlist_id: int,
    data: PlaylistUpdate,
    service: PlaylistServiceDep,
    current_user: RequireUser,
):
    return await service.update(
        playlist_id=playlist_id,
        data=data,
        current_user=current_user,
    )


@router.post(
    "/{playlist_id}/episodes/{episode_id}", response_model=PlaylistResponse
)
async def add_episode(
    playlist_id: int,
    episode_id: int,
    service: PlaylistServiceDep,
    current_user: RequireUser,
):
    return await service.add_episode_to_playlist(
        playlist_id=playlist_id,
        episode_id=episode_id,
        current_user=current_user,
    )


@router.delete(
    "/{playlist_id}/episodes/{episode_id}", response_model=PlaylistResponse
)
async def remove_episode(
    playlist_id: int,
    episode_id: int,
    service: PlaylistServiceDep,
    current_user: RequireUser,
):
    return await service.remove_episode_from_playlist(
        playlist_id=playlist_id,
        episode_id=episode_id,
        current_user=current_user,
    )


@router.delete("/{playlist_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_playlist(
    playlist_id: int,
    service: PlaylistServiceDep,
    current_user: RequireUser,
):
    await service.delete(playlist_id=playlist_id, current_user=current_user)
    return Response(status_code=HTTPStatus.NO_CONTENT)
