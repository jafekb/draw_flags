from io import BytesIO
from typing import Annotated

import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.common.flag_data import FlagList
from backend.src.flag_searcher import FlagSearcher

# TODO(bjafek) remove the debug eventually
app = FastAPI(debug=True)
flag_searcher = FlagSearcher(top_k=8)

origins = [
    "http://localhost:5173",
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


# Text-based flag search
@app.post("/search/text", response_model=FlagList)
async def search_by_text(text_query: Request):
    data = await text_query.json()  # Get the JSON data
    flags = flag_searcher.query(text_query=data["text_query"])
    return flags


# Image-based flag search
@app.post("/search/image", response_model=FlagList)
async def search_by_image(file: Annotated[UploadFile, File(...)]):
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Read the image data
    image_data = await file.read()
    image_bytes = BytesIO(image_data)

    # Search for similar flags
    flags = flag_searcher.query(image_data=image_bytes)
    return flags


# Legacy endpoint for backward compatibility
@app.post("/", response_model=FlagList)
async def add_flag(text_query: Request):
    data = await text_query.json()  # Get the JSON data
    flags = flag_searcher.query(text_query=data["text_query"])
    return flags


@app.get("/flags")
async def flags_info():
    return {
        "message": "Draw Flags API",
        "endpoints": {
            "text_search": (
                'POST to /search/text with JSON: {"text_query": "your flag description"}'
            ),
            "image_search": "POST to /search/image with multipart/form-data file upload",
            "legacy": 'POST to / with JSON: {"text_query": "your flag description"} (deprecated)',
        },
        "status": "running",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
