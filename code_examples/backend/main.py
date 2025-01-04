import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# from src.flag_searcher import FlagSearcher
from src.utils import Flag, Flags


app = FastAPI(debug=True)
# flag_searcher = FlagSearcher(top_k=4)

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
    "list_of_queries": [],
    "flags": [],
}

@app.get("/flags", response_model=Flags)
def get_flags():
    return Flags(flags=memory_db["list_of_queries"])


@app.post("/flags")
def add_flag(flag: Flag):
    if flag.name.startswith("flag"):
        # TODO(bjafek) Only do this part if it is so indicated
        flag.name = flag.name.lstrip("flag")
        flag.name = flag.name.lstrip(": ")
        # flags = flag_searcher.query(flag.name)
        flags = Flags(flags=[
            Flag(name="usa/usa"),
            Flag(name="usa/alabama"),
            Flag(name="usa/california"),
        ])
        # TODO(bjafek) can I return just "flags"?
        memory_db["flags"] = flags.flags

    # But always log the query.
    if flag.name == "delete":
        memory_db["list_of_queries"] = memory_db["list_of_queries"][:-1]
    elif flag.name in [i.name for i in memory_db["list_of_queries"]]:
        print ("It's already there!")
    else:
        memory_db["list_of_queries"].append(flag)

    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
