from fastapi import APIRouter

from audix.auth.router import router as auth_router
from audix.episodes.router import router as episodes_router
from audix.playlists.router import router as playlists_router
from audix.podcasts.router import router as podcasts_router
from audix.users.router import router as users_router

router = APIRouter(prefix='/api')


router.include_router(auth_router)
router.include_router(users_router)
router.include_router(podcasts_router)
router.include_router(episodes_router)
router.include_router(playlists_router)
