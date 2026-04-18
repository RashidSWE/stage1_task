from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.db.session import create_db_and_Tables
from fastapi.middleware.cors import CORSMiddleware
import httpx

from app.models.model import NameAnalysis, GenderCategory, GenderResult, AgeResult, NationalizeResult
from app.api.routes import analyze



@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_Tables()
    yield


app = FastAPI(lifespan=lifespan)

#Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


# Handle any unexpected server errors
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status":"500", "message":f"Internal server error"}
    )


app.include_router(analyze.router, prefix="/api")