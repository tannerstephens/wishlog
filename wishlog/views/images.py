from flask import Blueprint, abort, current_app, send_from_directory

IMAGE_DIR = current_app.config["IMAGE_STORAGE_DIRECTORY"]

MIMETYPES = {".webp": "image/webp", ".png": "image/png"}

# Every upload gets a new random name and is never changed in place, so a
# browser can keep its copy for good instead of asking again on every visit
CACHE_SECONDS = 365 * 24 * 60 * 60

images = Blueprint("images", __name__)


@images.route("/images/<string:filename>")
def serve(filename: str):
    extension = filename[filename.rfind(".") :].lower() if "." in filename else ""
    if extension not in MIMETYPES:
        abort(404)

    # send_from_directory refuses any path that escapes IMAGE_DIR
    response = send_from_directory(
        IMAGE_DIR, filename, mimetype=MIMETYPES[extension], max_age=CACHE_SECONDS
    )
    response.cache_control.immutable = True
    return response
