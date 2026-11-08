"""Fill the database with sample data for local development.

    pipenv run python seed.py           # seed an empty database
    pipenv run python seed.py --reset   # wipe existing users and items first

Uses the same settings as the app (DATABASE_URI, IMAGE_STORAGE_DIRECTORY).
"""

import sys
from argparse import ArgumentParser
from base64 import b64encode
from datetime import datetime, timedelta
from io import BytesIO

from PIL import Image, ImageOps

from wishlog import create_app
from wishlog.database import db
from wishlog.image_processor import ImageProcessor
from wishlog.models import Item, User

OWNER_USERNAME = "owner"
OWNER_PASSWORD = "password"

# (title, cost, desire, link, image colors or None, days since claimed or None)
ITEMS = [
    ("Espresso grinder", 189.99, 95, "https://example.com/grinder", ("#3e2723", "#d7a86e"), None),
    ("Cast iron skillet", 39.50, 80, "https://example.com/skillet", ("#212121", "#9e9e9e"), None),
    ("Board game night bundle", 64.00, 75, "example.com/games", ("#1a237e", "#64b5f6"), 2),
    ("Wool hiking socks (honestly, as many pairs as you can find)", 24.00, 60, None, None, None),
    ("Houseplant, something hard to kill", 18.25, 55, None, ("#1b5e20", "#a5d6a7"), None),
    ("Noise-cancelling headphones", 249.00, 50, "https://example.com/headphones", ("#311b92", "#b39ddb"), 5),
    ("Hardcover sketchbook", 15.00, 40, "https://example.com/sketchbook", None, None),
    ("Bag of Cash", 1000.00, 10, None, ("#33691e", "#dce775"), None),
]


def sample_image(dark: str, light: str) -> str:
    """A simple gradient PNG, base64-encoded the way the frontend uploads it."""
    vertical = Image.linear_gradient("L")
    diagonal = Image.blend(vertical, vertical.rotate(90), 0.5)
    gradient = diagonal.resize((800, 600))
    image = ImageOps.colorize(gradient, black=dark, white=light)

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return b64encode(buffer.getvalue()).decode()


def reset(image_processor: ImageProcessor) -> None:
    for item in Item.all():
        if item.image_file_path:
            image_processor.delete_image(item.image_file_path)
        item.delete(commit=False)
    for user in User.all():
        user.delete(commit=False)
    db.session.commit()


def seed(image_processor: ImageProcessor) -> None:
    User(OWNER_USERNAME, OWNER_PASSWORD).save()

    now = datetime.now()
    for title, cost, desire, link, colors, claimed_days_ago in ITEMS:
        if link and not link.startswith(("http://", "https://")):
            link = "http://" + link  # matches what the API does

        image_file_path = None
        if colors:
            image_file_path = image_processor.process_image(sample_image(*colors))

        item = Item(
            title=title,
            cost=cost,
            desire=desire,
            link=link,
            image_file_path=image_file_path,
        )
        item.claimed = claimed_days_ago is not None
        if item.claimed:
            item.claimed_date = now - timedelta(days=claimed_days_ago)
        item.save(commit=False)

    db.session.commit()


def main() -> int:
    parser = ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--reset",
        action="store_true",
        help="delete all existing users, items and their images before seeding",
    )
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        image_processor = ImageProcessor(app.config["IMAGE_STORAGE_DIRECTORY"])

        if User.setup_complete() or Item.all():
            if not args.reset:
                print(
                    "The database already has data. Run with --reset to wipe it "
                    "and seed again (task seed -- --reset).",
                    file=sys.stderr,
                )
                return 1
            reset(image_processor)

        seed(image_processor)

    claimed = sum(1 for item in ITEMS if item[5] is not None)
    print(f"Seeded {len(ITEMS)} items ({claimed} claimed).")
    print(f"Log in at /login as {OWNER_USERNAME!r} with password {OWNER_PASSWORD!r}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
