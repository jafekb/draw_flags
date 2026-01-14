from typing import List, Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.common.flag_data import FlagList
from backend.src.flag_searcher import FlagSearcher

# TODO(bjafek) remove the debug eventually
app = FastAPI(debug=True)
flag_searcher = FlagSearcher(top_k=15)  # Server-side filtering with top 15 results

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


class SearchRequest(BaseModel):
    """Request model for flag search with optional filters"""

    text_query: str
    categories: Optional[List[str]] = None  # e.g., ["national", "subdivision"]
    continent: Optional[str] = None  # e.g., "Europe"
    country: Optional[str] = None  # e.g., "United States"


# TODO(bjafek) this isn't 'adding a flag', it's querying based on text
@app.post("/", response_model=FlagList)
async def add_flag(request: SearchRequest):
    filters = {
        "categories": request.categories,
        "continent": request.continent,
        "country": request.country,
    }
    flags = flag_searcher.query(request.text_query, is_image=False, filters=filters)
    return flags


@app.get("/flags")
async def flags_info():
    return {
        "message": "Draw Flags API",
        "usage": 'POST to / with JSON: {"text_query": "your flag description"}',
        "status": "running",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
