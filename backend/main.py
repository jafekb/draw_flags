import sys

# TODO(bjafek) why
sys.path.append("/home/bjafek/personal/draw_flags/backend")

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from src.flag_searcher import FlagSearcher
from common.flag_data import FlagList

# TODO(bjafek) remove the debug eventually
app = FastAPI(debug=True)
flag_searcher = FlagSearcher(top_k=8)

origins = [
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# TODO(bjafek) this isn't 'adding a flag', it's querying based on text
@app.post(path="/flags", response_model=FlagList)
async def add_flag(text_query: Request):
    data = await text_query.json()  # Get the JSON data
    flags = flag_searcher.query(data["text_query"], is_image=False)
    return flags


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
