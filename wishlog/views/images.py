from flask import Blueprint, current_app, send_from_directory

IMAGE_DIR = current_app.config["IMAGE_STORAGE_DIRECTORY"]

images = Blueprint("images", __name__)


@images.route("/images/<string:filename>")
def serve(filename: str):
    # send_from_directory refuses any path that escapes IMAGE_DIR
    return send_from_directory(IMAGE_DIR, filename, mimetype="image/png")
