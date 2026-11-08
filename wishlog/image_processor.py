from base64 import b64decode
from binascii import Error as Base64Error
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image


class InvalidImageError(ValueError):
    pass


class ImageProcessor:
    def __init__(self, image_directory: str) -> None:
        self.image_directory = Path(image_directory)

    def process_image(self, b64_image_data: str) -> str | None:
        try:
            input_image = Image.open(BytesIO(b64decode(b64_image_data, validate=True)))
            input_image.load()
        except (Base64Error, OSError, ValueError, Image.DecompressionBombError) as e:
            # OSError covers PIL's UnidentifiedImageError and truncated files
            raise InvalidImageError("Could not read the uploaded image") from e

        target_image = Image.new("RGBA", (800, 600), "#ffffff00")

        input_image.thumbnail((800, 600), Image.Resampling.LANCZOS)

        in_w, in_h = input_image.size
        target_image.paste(input_image, ((800 - in_w) // 2, (600 - in_h) // 2))

        filename = f"{uuid4()}.png"
        target_image.save(self.image_directory / filename)

        return filename

    def delete_image(self, filename: str) -> None:
        # Only ever delete a plain file name directly inside the image directory
        if not filename or Path(filename).name != filename:
            return

        try:
            (self.image_directory / filename).unlink(missing_ok=True)
        except OSError:
            # A leftover file is harmless; don't fail the delete over it
            pass
