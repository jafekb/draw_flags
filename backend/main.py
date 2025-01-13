import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from src.flag_searcher import FlagSearcher

from common.flag_data import Flags, Image

# TODO(bjafek) remove the debug eventually
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


@app.get(path="/flags", response_model=Flags)
def get_flags():
    text_flags = memory_db["text_flags"]
    # Clear it afterwards
    memory_db["text_flags"] = Flags(flags=[])

    return text_flags


# TODO(bjafek) this isn't adding a flag, it's querying based on text
# TODO(bjafek) this works again, but it doesn't make sense to me why
#  this function had to be re-written this way when the get_image_flags()
#  was working fine. I think it has something to do with the Flag redefinition?
@app.post(path="/flags")
async def add_flag(text_query: Request):
    data = await text_query.json()  # Get the JSON data
    if memory_db["text_flags"]:
        memory_db["text_flags"] = Flags(flags=[])

    flags = flag_searcher.query(data["text_query"], is_image=False)
    memory_db["text_flags"] = flags

    # But always log the query.
    memory_db["most_recent_query"] = text_query

    return


@app.get(path="/upload_image", response_model=Flags)
def get_image_flags():
    image_flags = memory_db["image_flags"]
    # Clear it afterwards
    memory_db["image_flags"] = Flags(flags=[])

    return image_flags


@app.post(path="/upload_image")
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
