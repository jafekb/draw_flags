import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.flag_searcher import FlagSearcher
from src.utils import Flag, Flags, Image

app = FastAPI(debug=True)
flag_searcher = FlagSearcher(top_k=8)

origins = [
    "http://localhost:5173",
    # Add more origins here
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

memory_db = {
    "most_recent_query": "",
    "text_flags": Flags(flags=[]),
    "image_flags": Flags(flags=[]),
}


@app.get("/flags", response_model=Flags)
def get_flags():
    return memory_db["text_flags"]


# TODO(bjafek) this isn't adding a flag, it's querying based on text
@app.post("/flags")
def add_flag(flag: Flag):
    if memory_db["text_flags"]:
        memory_db["text_flags"] = Flags(flags=[])

    flags = flag_searcher.query(flag.name, is_image=False)
    memory_db["text_flags"] = flags

    # But always log the query.
    memory_db["most_recent_query"] = flag

    return


@app.get("/upload_image", response_model=Flags)
def get_image_flags():
    print(memory_db["image_flags"])
    return memory_db["image_flags"]


@app.post("/upload_image")
def get_uploaded_image(img: Image):
    """
    TODO(bjafek) describe
    """
    # TODO(bjafek) how to actually pass the image instead
    #  of this incomplete filename?
    if memory_db["image_flags"]:
        memory_db["image_flags"] = Flags(flags=[])
    flags = flag_searcher.query(img, is_image=True)

    memory_db["image_flags"] = flags
    return


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
