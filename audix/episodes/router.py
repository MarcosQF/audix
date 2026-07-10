from http import HTTPStatus

from fastapi import APIRouter, File, HTTPException, UploadFile

from audix.shared.permissions import RequireUser

from .schemas import (
    EpisodeAnalyticsResponse,
    EpisodeCreate,
    EpisodeProgressResponse,
    EpisodeProgressUpdate,
    EpisodeResponse,
    ListEpisodes,
)
from .service import EpisodeServiceDep

router = APIRouter(tags=["Episodes"])

@router.post(
    "/podcasts/{podcast_id}/episodes",
    response_model=EpisodeResponse,
    status_code=HTTPStatus.CREATED,
    summary="Cria um novo episódio para um podcast",
)
async def create_episode(
    podcast_id: int,
    data: EpisodeCreate,
    service: EpisodeServiceDep,
    current_user: RequireUser,
):
    return await service.create(
        data=data, 
        podcast_id=podcast_id, 
        current_user=current_user
    )


@router.get(
    "/podcasts/{podcast_id}/episodes",
    response_model=ListEpisodes,
    status_code=HTTPStatus.OK,
    summary="Lista todos os episódios de um podcast",
)
async def list_episodes(
    current_user: RequireUser,
    podcast_id: int,
    service: EpisodeServiceDep,
    skip: int = 0,
    limit: int = 100,
):
    episodes_list = await service.list_by_podcast(
        current_user=current_user,
        podcast_id=podcast_id, 
        skip=skip, 
        limit=limit
    )
    
    return {'episodes': episodes_list, 'quantity': len(episodes_list)}

@router.get(
    "/episodes/{episode_id}",
    response_model=EpisodeResponse,
    status_code=HTTPStatus.OK,
    summary="Obtém os detalhes de um episódio específico",
)
async def get_episode(
    current_user: RequireUser,
    episode_id: int,
    service: EpisodeServiceDep,
):
    return await service.get_by_id(
        episode_id=episode_id, current_user=current_user
    )


@router.post(
    "/episodes/{episode_id}/audio",
    response_model=EpisodeResponse,
    status_code=HTTPStatus.OK,
    summary="Faz o upload do arquivo de áudio para o episódio",
)
async def upload_episode_audio(
    episode_id: int,
    service: EpisodeServiceDep,
    current_user: RequireUser,
    file: UploadFile = File(...),
):
    if not (file.content_type or "").startswith("audio/"):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="O arquivo enviado deve ser um áudio válido."
        )

    return await service.upload_audio(
        episode_id=episode_id, 
        file=file, 
        current_user=current_user
    )

@router.post(
    "/episodes/{episode_id}/image",
    response_model=EpisodeResponse,
    status_code=HTTPStatus.OK,
    summary="Faz o upload da imagem para o episódio",
)
async def upload_episode_image(
    episode_id: int,
    service: EpisodeServiceDep,
    current_user: RequireUser,
    file: UploadFile = File(...),
):
    # if not (file.content_type or "").startswith("audio/"):
    #     raise HTTPException(
    #         status_code=HTTPStatus.BAD_REQUEST,
    #         detail="O arquivo enviado deve ser um áudio válido."
    #     )

    return await service.upload_episode_image(
        file=file, 
        episode_id=episode_id, 
        user=current_user
    )

@router.delete(
    "/episodes/{episode_id}",
    status_code=HTTPStatus.NO_CONTENT,
    summary="Deleta um episódio e remove seus arquivos anexos do storage",
)
async def delete_episode(
    episode_id: int,
    service: EpisodeServiceDep,
    current_user: RequireUser,
):
    await service.delete(episode_id=episode_id, current_user=current_user)

@router.post("/episodes/{episode_id}/like", status_code=HTTPStatus.OK)
async def toggle_episode_like(
    episode_id: int,
    service: EpisodeServiceDep,
    current_user: RequireUser,
):
    result = await service.toggle_like(
        episode_id=episode_id, current_user=current_user
    )
    return result


@router.post(
    "/episodes/{episode_id}/listening-progress", 
    status_code=HTTPStatus.OK,
    summary="Atualiza o progresso de áudio ouvido pelo usuário e computa a visualização"
)
async def update_listening_progress(
    episode_id: int,
    data: EpisodeProgressUpdate,
    service: EpisodeServiceDep,
    current_user: RequireUser,
):
    await service.update_progress(
        episode_id=episode_id,
        user=current_user,
        current_time_seconds=data.current_time_seconds
    )
    
    return {"status": "progress_updated"}

@router.get(
    "/{episode_id}/listening-progress",
    response_model=EpisodeProgressResponse,
    summary="Busca o progresso atual de reprodução do usuário para um episódio específico",
)
async def get_listening_progress(
    episode_id: int,
    service: EpisodeServiceDep,
    current_user: RequireUser,
):
    return await service.get_progress(episode_id=episode_id, user=current_user)

@router.get("/episodes/{episode_id}/analytics", response_model=EpisodeAnalyticsResponse)
async def get_episode_analytics(
    episode_id: int,
    service: EpisodeServiceDep,
    current_user: RequireUser,
):
    return await service.get_episode_metrics(episode_id=episode_id, current_user=current_user)
