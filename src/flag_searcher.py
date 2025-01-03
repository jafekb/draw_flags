"""
Class that can take in an image and output a bunch of
other images of flags that look like it.

Uses:
https://docs.openflags.net/implementations/python/
"""
import os
import glob
from pathlib import Path
from PIL import Image
import time

import cv2
import cairosvg
import numpy as np
import open_flags as of
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm

TMP_DIR = Path("/home/bjafek/personal/draw_flags/tmp")
TMP_DIR.mkdir(exist_ok=True, parents=False)


def load_all_flag_info():
    image_list = []
    label_list = []
    idx = 0
    for key, val in tqdm(of.flag_map.FLAG_MAP.items()):
        country, place = key.split("/")
        file_path = TMP_DIR / country / f"{place}.svg"
        file_path.parent.mkdir(exist_ok=True, parents=False)

        if not file_path.exists():
            svg = of.get_flag_svg(country, place)
            try:
                # https://cairosvg.org/documentation/
                img = cairosvg.svg2png(svg, write_to=str(file_path))
            except Exception as e:
                print (key, "failed!")
                # import pdb; pdb.set_trace()
                continue
        
        # TODO(bjafek) I don't totally understand the format that the model encode expects
        # lmao I think the reason it expects a string is because I'm using the SentenceTransformer
        # instead of an ImageTransformer
        img = Image.open(file_path)
        image_list.append(img)
        label_list.append(key)
        idx += 1
        # if idx > 10: break  # TODO(bjafek) remove this!!!
    return image_list, label_list


class FlagSearcher:
    def __init__(self, top_k):
        self._top_k = top_k

        # Load the OpenAI CLIP Model
        print('Loading CLIP Model...', end=" ")
        start = time.time()
        # TODO(bjafek) other models?
        self._model = SentenceTransformer('clip-ViT-B-32')
        print (f"success ({time.time() - start:.2f}s)!")

        print ("Loading & encoding images...", end=" ")
        start = time.time()
        self._image_list, self._label_list = load_all_flag_info()
        print (f"Images loaded ({time.time() - start:.2f}s)!")

        start = time.time()
        self._encoded_images = self._model.encode(
            self._image_list, batch_size=128, convert_to_tensor=True, show_progress_bar=True
        )
        print (f"Images encoded ({time.time() - start:.2f}s)!")


        # TODO(bjafek) obviously don't do this in the constructor
        self.recognize(None)

        # Now we run the clustering algorithm. This function compares images aganist
        # all other images and returns a list with the pairs that have the highest
        # cosine similarity score
        # processed_images = util.paraphrase_mining_embeddings(encoded_image)
        # NUM_SIMILAR_IMAGES = 10

        # =================
        # DUPLICATES
        # =================
        # print('Finding duplicate images...')
        # Filter list for duplicates. Results are triplets (score, image_id1, image_id2) and is scorted in decreasing order
        # A duplicate image will have a score of 1.00
        # duplicates = [image for image in processed_images if image[0] >= 1]

        # Output the top X duplicate images
        # for score, image_id1, image_id2 in duplicates[0:NUM_SIMILAR_IMAGES]:
            # print("\nScore: {:.3f}%".format(score * 100))
            # print(image_names[image_id1])
            # print(image_names[image_id2])

        # =================
        # NEAR DUPLICATES
        # =================
        # print('Finding near duplicate images...')
        # Use a threshold parameter to identify two images as similar. By setting the threshold lower,
        # you will get larger clusters which have less similar images in it. Threshold 0 - 1.00
        # A threshold of 1.00 means the two images are exactly the same. Since we are finding near
        # duplicate images, we can set it at 0.99 or any number 0 < X < 1.00.
        # threshold = 0.99
        # near_duplicates = [image for image in processed_images if image[0] < threshold]

        # for score, image_id1, image_id2 in near_duplicates[0:NUM_SIMILAR_IMAGES]:
            # print("\nScore: {:.3f}%".format(score * 100))
            # print(image_names[image_id1])
            # print(image_names[image_id2])

    def recognize(self, img : np.ndarray) -> np.ndarray:
        """
        Run the recognizer, comparing to all the existing stuff.
        """
        
        # TODO(bjafek) actually get it from the upload
        image_dir = Path("/home/bjafek/personal/draw_flags/examples").glob("*.jpg")
        for img_fn in image_dir:
            img = Image.open(img_fn)
            new_embedding = self._model.encode([img])
            similarity_scores = cosine_similarity(new_embedding, self._encoded_images)
            top_k_indices = similarity_scores.argsort()[0][::-1][:self._top_k]
            import pdb; pdb.set_trace()
        return np.array([])
