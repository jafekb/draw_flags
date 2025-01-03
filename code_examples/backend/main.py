import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from src.flag_searcher import FlagSearcher


class Flag(BaseModel):
    name: str
    wikipedia_link: str = "https://en.wikipedia.org/wiki/Flag_of_the_United_States"


class Flags(BaseModel):
    fruits: List[Flag]


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
    "list_of_fruits": [],
    "flags": [],
}

@app.get("/fruits", response_model=Flags)
def get_fruits():
    return Flags(fruits=memory_db["list_of_fruits"])


@app.post("/fruits")
def add_fruit(flag: Flag):
    if flag.name.startswith("flag"):
        flag.name = flag.name.lstrip("flag")
        flag.name = flag.name.lstrip(": ")
        images, labels, scores = flag_searcher.query(flag.name)
        memory_db["flags"] = labels
        print (labels, scores)
        return

    if flag.name == "delete":
        memory_db["list_of_fruits"] = memory_db["list_of_fruits"][:-1]
    elif flag.name in [i.name for i in memory_db["list_of_fruits"]]:
        print ("It's already there!")
    else:
        memory_db["list_of_fruits"].append(flag)

    return None


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
