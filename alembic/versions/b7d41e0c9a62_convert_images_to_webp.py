"""Convert uploaded item images from PNG to WebP

Revision ID: b7d41e0c9a62
Revises: 4c2e7a91b5d3
Create Date: 2026-11-08 20:30:00.000000

"""

from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from PIL import Image

from alembic import op
from wishlog.config import Config as AppConfig

# revision identifiers, used by Alembic.
revision: str = "b7d41e0c9a62"
down_revision: Union[str, None] = "4c2e7a91b5d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Kept here rather than imported, so this migration doesn't change if the app does
WEBP_QUALITY = 82

items = sa.table(
    "items",
    sa.column("id", sa.Integer),
    sa.column("image_file_path", sa.String),
)


def _convert(old_suffix: str, new_suffix: str, save_options: dict) -> None:
    image_dir = Path(AppConfig.IMAGE_STORAGE_DIRECTORY)
    connection = op.get_bind()

    rows = connection.execute(
        sa.select(items.c.id, items.c.image_file_path).where(
            items.c.image_file_path.like(f"%{old_suffix}")
        )
    ).all()

    converted = []
    for item_id, filename in rows:
        old_path = image_dir / filename
        # Only plain names inside the image directory, as the app itself allows
        if Path(filename).name != filename or not old_path.is_file():
            continue

        new_name = filename[: -len(old_suffix)] + new_suffix
        try:
            with Image.open(old_path) as image:
                image.save(image_dir / new_name, **save_options)
        except OSError as e:
            # One unreadable image shouldn't stop the upgrade; it stays as it was
            print(f"Skipping {filename}: {e}")
            continue

        connection.execute(
            items.update().where(items.c.id == item_id).values(image_file_path=new_name)
        )
        converted.append(old_path)

    # Old files go last, once every row points at its new file. Each migration
    # commits on its own (see env.py), so only this migration's own commit
    # could still undo the row changes after this point.
    for old_path in converted:
        try:
            old_path.unlink()
        except OSError:
            pass

    print(f"Converted {len(converted)} image(s) to {new_suffix}")


def upgrade() -> None:
    _convert(".png", ".webp", {"format": "WEBP", "quality": WEBP_QUALITY, "method": 6})


def downgrade() -> None:
    _convert(".webp", ".png", {"format": "PNG"})
