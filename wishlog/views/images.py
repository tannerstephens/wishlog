from pathlib import Path

from flask import Blueprint, current_app, send_file

IMAGE_DIR = Path(current_app.config["IMAGE_STORAGE_DIRECTORY"])

images = Blueprint("images", __name__)


@images.route("/images/<string:filename>")
def serve(filename: str):
    return send_file(IMAGE_DIR / filename, mimetype="image/png")
