from http import HTTPStatus

from fastapi import APIRouter, File, HTTPException, UploadFile

from audix.shared.minio.service import MinioServiceDep
from audix.shared.permissions import RequireUser

from .schemas import ListPodcast, PodcastCreate, PodcastResponse, PodcastUpdate
from .service import PodcastServiceDep

router = APIRouter(prefix="/podcasts", tags=["Podcasts"])

@router.post(
    "/",
    response_model=PodcastResponse,
    status_code=HTTPStatus.CREATED,
    summary="Cria um novo Podcast",
)
async def create_podcast(
    podcast_data: PodcastCreate,
    service: PodcastServiceDep,
    current_user: RequireUser,
):
    return await service.create(
        podcast_data=podcast_data,
        author_id=current_user.id,
    )


@router.get(
    "/{podcast_id}",
    response_model=PodcastResponse,
    summary="Busca um podcast pelo ID",
)
async def get_podcast(
    current_user: RequireUser,
    podcast_id: int,
    service: PodcastServiceDep,
    storage: MinioServiceDep,
):
    podcast = await service.get_by_id(podcast_id)
    podcast.image_url = await storage.get_file_url(podcast.image_url or None)

    return podcast


@router.get(
    "/",
    response_model=ListPodcast,
    summary="Lista todos os podcasts",
)
async def list_podcasts(
    current_user: RequireUser,
    service: PodcastServiceDep,
    storage: MinioServiceDep,
    skip: int = 0,
    limit: int = 100,
):
    podcasts = await service.list_all(skip=skip, limit=limit)

    for podcast in podcasts:
        podcast.image_url = await storage.get_file_url(
            podcast.image_url or None
        )

    return {"podcasts": podcasts, "quantity": len(podcasts)}


@router.patch(
    "/{podcast_id}",
    response_model=PodcastResponse,
    summary="Atualiza um podcast",
)
async def update_podcast(
    podcast_id: int,
    podcast_data: PodcastUpdate,
    service: PodcastServiceDep,
    current_user: RequireUser,
):
    return await service.update(
        podcast_id=podcast_id,
        podcast_data=podcast_data,
        current_user=current_user,
    )


@router.delete(
    "/{podcast_id}",
    status_code=HTTPStatus.NO_CONTENT,
    summary="Deleta um podcast",
)
async def delete_podcast(
    podcast_id: int,
    service: PodcastServiceDep,
    current_user: RequireUser,
):
    await service.delete(podcast_id=podcast_id, current_user=current_user)


@router.post(
    "/{podcast_id}/image",
    status_code=HTTPStatus.OK,
    response_model=PodcastResponse,
    summary="Faz o upload da imagem de capa de um podcast existente",
)
async def upload_podcast_image(
    podcast_id: int,
    service: PodcastServiceDep,
    current_user: RequireUser,
    file: UploadFile = File(...),
):
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST,
            detail="O arquivo enviado deve ser uma imagem.",
        )

    return await service.upload_podcast_image(
        file=file,
        podcast_id=podcast_id,
        user=current_user
    )
