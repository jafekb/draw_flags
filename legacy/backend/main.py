import logging
import os
import random
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.common.flag_data import FlagList
from backend.src.flag_searcher import FlagSearcher

MEMORY_LOG_REQUESTS = int(os.getenv("MEMORY_LOG_REQUESTS", "5"))
logger = logging.getLogger("uvicorn.error")


def _get_rss_mb() -> float:
    status_path = Path("/proc/self/status")
    if status_path.exists():
        for line in status_path.read_text().splitlines():
            if line.startswith("VmRSS:"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    return int(parts[1]) / 1024.0
    try:
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
    except Exception:
        return -1.0


def _log_memory(event: str) -> None:
    rss_mb = _get_rss_mb()
    logger.info("memory_rss_mb=%.2f event=%s", rss_mb, event)


# TODO(bjafek) remove the debug eventually
app = FastAPI(debug=True)
app.state.flag_searcher = None
app.state.memory_log_requests_remaining = MEMORY_LOG_REQUESTS

origins = [
    "http://localhost:5173",
    "http://10.0.9.167:5173",
    "https://whatsthatflag.com",
    "https://www.whatsthatflag.com",
    "https://draw-flags-frontend.onrender.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    _log_memory("startup_begin")
    app.state.flag_searcher = FlagSearcher(top_k=15)  # Server-side filtering with top 15 results
    _log_memory("startup_end")


@app.middleware("http")
async def log_memory_middleware(request, call_next):
    response = await call_next(request)
    remaining = app.state.memory_log_requests_remaining
    if remaining and remaining > 0:
        app.state.memory_log_requests_remaining = remaining - 1
        _log_memory(f"request:{request.method} {request.url.path}")
    return response


class SearchRequest(BaseModel):
    """Request model for flag search with optional filters"""

    text_query: str
    top_k: Optional[int] = None
    categories: Optional[List[str]] = None  # e.g., ["national", "subdivision"]
    continent: Optional[str] = None  # e.g., "Europe"
    country: Optional[str] = None  # e.g., "United States"


class BannerFlag(BaseModel):
    name: str
    wikipedia_url: str
    wikipedia_image_url: str


class BannerFlagList(BaseModel):
    flags: List[BannerFlag]


# TODO(bjafek) this isn't 'adding a flag', it's querying based on text
@app.post("/", response_model=FlagList)
async def add_flag(request: SearchRequest):
    filters = {
        "categories": request.categories,
        "continent": request.continent,
        "country": request.country,
    }
    flags = app.state.flag_searcher.query(
        request.text_query,
        is_image=False,
        filters=filters,
        top_k=request.top_k,
    )
    return flags


@app.get("/flags/random", response_model=BannerFlagList)
async def random_flags(limit: int = 12):
    if app.state.flag_searcher is None:
        return BannerFlagList(flags=[])
    flags = app.state.flag_searcher._flags.flags
    if not flags:
        return BannerFlagList(flags=[])

    safe_limit = max(0, min(limit, 50))
    if safe_limit == 0:
        return BannerFlagList(flags=[])
    sample = random.sample(flags, k=min(safe_limit, len(flags)))
    return BannerFlagList(
        flags=[
            BannerFlag(
                name=flag.name,
                wikipedia_url=flag.wikipedia_url,
                wikipedia_image_url=flag.wikipedia_image_url,
            )
            for flag in sample
        ]
    )


@app.get("/flags")
async def flags_info():
    return {
        "message": "Draw Flags API",
        "usage": 'POST to / with JSON: {"text_query": "your flag description", "top_k": 15}',
        "status": "running",
    }


@app.get("/flags/all", response_model=FlagList)
async def all_flags():
    return app.state.flag_searcher.all_flags()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
