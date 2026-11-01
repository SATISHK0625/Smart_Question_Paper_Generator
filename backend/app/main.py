import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from .api import api_router
from .utils.file_utils import cleanup_old_temp_files

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: cleanup any old temporary files
    cleanup_old_temp_files()
    yield

app = FastAPI(
    title="Smart Question Paper Generator API",
    description="Modular, production-ready backend for analyzing reference PDFs, rule-based question parsing, and generating formatted question papers.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
origins = [o.strip() for o in allowed_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [f"{'.'.join(str(l) for l in err.get('loc', []))}: {err.get('msg', '')}" for err in exc.errors()]
    detail_str = "; ".join(errors)
    print(f"REQUEST VALIDATION ERROR: {detail_str}")
    return JSONResponse(
        status_code=422,
        content={"detail": detail_str}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"An internal server error occurred: {str(exc)}"}
    )

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
