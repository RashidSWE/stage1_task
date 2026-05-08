from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
from db.session import create_db_and_Tables
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from db.seed import seed_profiles
from models.model import NameAnalysis, GenderCategory, GenderResult, AgeResult, NationalizeResult
from api.routes import analyze, auth
from fastapi.exceptions import RequestValidationError
import time
import logging
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from services.limiter import limiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, create_db_and_Tables)
    await loop.run_in_executor(None, seed_profiles)
    yield

""" logging setup """
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

#Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://hng-projects.fastapicloud.dev" ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)

    process_time = (time.time() - start_time)  * 1000

    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {respone.status_code}"
        f"Latency: {process.time: .2f}ms - "
        f"IP: {request.client.host}"
    )

    return response


""" Handle error exceptions in General """
#Handle all HTTPException errors (400, 404, 422, 500, 502 etc))
@app.exception_handler(HTTPException)
async def http_exception_handelr(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": str(exc.status_code), "message": exc.detail}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"status": "error", "message": "Invalid query parameters"}
    )

# Handle any unexpected server errors
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status":"500", "message":f"Internal server error"}
    )


app.include_router(analyze.router, prefix="/api")
app.include_router(auth.router, prefix="/auth")