"""
Upload a picture, it will tell you what flag most closely
resembles it. Using ARTIFICIAL INTELLIGENCE.
"""
from flask import Flask, render_template, request
import werkzeug
import os

import cv2
import numpy as np

from src.flag_searcher import FlagSearcher


app = Flask(__name__)

# Initialize some classes (apparently this is a common place to do it)
FLAG_SEARCHER = FlagSearcher(
    top_k=10,
)

# Path to upload directory where your uploaded files will be stored
UPLOAD_FOLDER = '/home/bjafek/personal/draw_flags/tmp'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')


@app.route("/process", methods=["POST"])
def process():
    """
    This is the main access point where we'll put all the functions
    that will be called.
    """
    out_name = upload_file()
    recognize_image(out_name)

def recognize_image(out_name):
    """
    After the image has been selected, recognize it.
    """
    img = cv2.imread(out_name)
    topk_similar = FLAG_SEARCHER.recognize(img)
    import pdb; pdb.set_trace()
    
def upload_file():
    # Check if a file was posted
    if 'file' not in request.files:
        return "No file part in the request", 400

    file = request.files['file']

    # If the user does not select a file, an empty file variable will be sent.
    # So check if a file was uploaded and if it's of correct type (png, jpg, jpeg)
    if file.filename == '':
        return "No selected file", 400

    if file and allowed_file(file.filename):
        filename = werkzeug.utils.secure_filename(file.filename)
        out_name = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(out_name)
        return out_name

    return "Filetype not supported", 400  

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

if __name__ == '__main__':
    app.run(debug=True)