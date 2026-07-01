from fastapi import APIRouter

from audix.auth.router import router as auth_router
from audix.users.router import router as users_router

router = APIRouter(prefix='/api')


router.include_router(users_router)
router.include_router(auth_router)
