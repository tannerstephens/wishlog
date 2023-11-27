from base64 import b64decode
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image


class ImageProcessor:
    def __init__(self, image_directory: str) -> None:
        self.image_directory = Path(image_directory)

    def process_image(self, b64_image_data: str) -> str | None:
        input_image = Image.open(BytesIO(b64decode(b64_image_data)))
        target_image = Image.new("RGBA", (800, 600), "#ffffff00")

        input_image.thumbnail((800, 600), Image.Resampling.LANCZOS)

        in_w, in_h = input_image.size
        target_image.paste(input_image, ((800 - in_w) // 2, (600 - in_h) // 2))

        filename = f"{uuid4()}.png"
        target_image.save(self.image_directory / filename)

        return filename
