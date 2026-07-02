from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from audix.database import get_session
from audix.setup import create_initial_admin, create_podcast_bucket
from audix.shared.errors import ApiException

from .main_router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async for session in get_session():
        await create_initial_admin(session)
        await create_podcast_bucket()
        break
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(router)

@app.exception_handler(ApiException)
async def api_exception_handler(request: Request, exc: ApiException):
 
    return JSONResponse(
        status_code=exc.status_code,
        content={
            'detail': exc.detail,
            'error_code': exc.headers.get('X-Error-Code', 'UNKNOWN_ERROR'), # type: ignore
            'timestamp': datetime.now(timezone.utc).isoformat(),
        },
    )
