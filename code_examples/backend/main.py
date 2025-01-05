import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from src.flag_searcher import FlagSearcher
from src.utils import Flag, Flags


app = FastAPI(debug=True)
flag_searcher = FlagSearcher(top_k=4)

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
    "flags": Flags(flags=[]),
}

@app.get("/flags", response_model=Flags)
def get_flags():
    return memory_db["flags"]


@app.post("/flags")
def add_flag(flag: Flag):
    if flag.name in ("delete", "clear"):
        memory_db["most_recent_query"] = ""
        memory_db["flags"] = Flags(flags=[])
        return

    flags = flag_searcher.query(flag.name)
    # flags = Flags(flags=[
        # Flag(name="usa/usa"),
        # Flag(name="usa/alabama"),
        # Flag(name="usa/california"),
    # ])
    memory_db["flags"] = flags

    # But always log the query.
    memory_db["most_recent_query"] = flag

    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
