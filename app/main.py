from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.db.session import create_db_and_Tables
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
from app.db.seed import seed_profiles
from app.models.model import NameAnalysis, GenderCategory, GenderResult, AgeResult, NationalizeResult
from app.api.routes import analyze
from fastapi.exceptions import RequestValidationError


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, create_db_and_Tables)
    await loop.run_in_executor(None, seed_profiles)
    yield


app = FastAPI(lifespan=lifespan)

#Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

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