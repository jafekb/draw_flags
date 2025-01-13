"""
We want to make sure that it doesn't take too long to set-up
or run individual frames with the FlagSearcher. This is a benchmark.


TODO(bjafek) This should have at least some basic logic to make
sure the output is correct, not just fast lol.
"""

import random
import string
import time
from pathlib import Path

from tqdm import trange

from common.flag_data import Image

start = time.time()
from backend.src.flag_searcher import FlagSearcher  # noqa: E402

print(f"Time to import: {time.time() - start:.2f}s")


n_builds = 2
start = time.time()
for i in trange(n_builds, leave=False):
    flag_searcher = FlagSearcher(top_k=8, verbose=False)
elapsed = (time.time() - start) / n_builds
print(f"Time to build: {elapsed:.2f}s")


n_text_queries = 50
start = time.time()
all_chars = string.whitespace + string.ascii_uppercase + string.ascii_lowercase
for i in trange(n_text_queries, leave=False):
    # I don't think the actual choice of letters makes a big difference in speed
    text = "".join(random.choice(all_chars) for _ in range(10))
    flags = flag_searcher.query(text, is_image=False)
elapsed = (time.time() - start) / n_text_queries
print(f"Time to query text: {elapsed:.2f}s")


n_image_queries = 50
images = sorted(Path("/home/bjafek/personal/draw_flags/examples").glob("*.png"))
images = [Image(data=i.name) for i in images]

start = time.time()
for i in trange(n_image_queries, leave=False):
    # Just roll over back to the beginning if you don't have enough.
    img_fn = images[i % len(images)]
    flags = flag_searcher.query(img_fn, is_image=True)
elapsed = (time.time() - start) / n_image_queries
print(f"Time to query image: {elapsed:.2f}s")
