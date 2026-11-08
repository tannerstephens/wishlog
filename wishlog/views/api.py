from datetime import datetime
from math import isfinite
from re import match

from flask import Blueprint, current_app, flash, jsonify, request, session
from sqlalchemy.exc import IntegrityError

from ..constants import USER_ID
from ..database import db
from ..image_processor import ImageProcessor, InvalidImageError
from ..models import Item, User

api = Blueprint("api", __name__, url_prefix="/api")

image_processor = ImageProcessor(current_app.config["IMAGE_STORAGE_DIRECTORY"])


def api_response(success: bool, **kwargs):
    return jsonify(dict(success=success, **kwargs))


def parse_cost(value) -> float:
    cost = float(value)
    if not isfinite(cost) or cost < 0:
        raise ValueError("cost must be a finite, non-negative number")
    return cost


@api.route("/users", methods=["POST"])
def register():
    if User.setup_complete():
        return api_response(False, message="Setup has already been completed")

    username = request.json.get("username")
    password = request.json.get("password")

    if not isinstance(username, str) or not username.strip():
        return api_response(False, message="`username` is required")
    if not isinstance(password, str) or not password:
        return api_response(False, message="`password` is required")

    try:
        new_user = User(username.strip(), password).save()
    except IntegrityError:
        db.session.rollback()
        return api_response(False, message="Setup has already been completed")

    # Two registrations can pass the check above at the same time.
    # Only the first user becomes the owner, so undo any later one.
    if User.owner().id != new_user.id:
        new_user.delete()
        return api_response(False, message="Setup has already been completed")

    flash("Registration successful! You may now login", "success")

    return api_response(True, user=new_user.to_dict())


@api.route("/session", methods=["GET"])
def get_session():
    user = None
    if request.user:
        user = request.user.to_dict()

    return api_response(True, user=user)


@api.route("/session", methods=["POST"])
def login():
    if request.user:
        return api_response(False, message="Already authenticated")

    username = request.json.get("username")
    password = request.json.get("password")

    if username is None or password is None:
        return api_response(False, message="`username` and `password` are required")

    if (user := User.get_by_uername(username)) is None or not user.check_password(
        password
    ):
        return api_response(False, message="Username or password incorrect")

    session[USER_ID] = user.id

    return api_response(True, user=user.to_dict())


@api.route("/session", methods=["DELETE"])
def logout():
    session.clear()

    return api_response(True)


@api.route("/items", methods=["GET"])
def all_items():
    desc = "desc" in request.args
    items_filter = Item.order_by(request.args.get("order_by"), desc)

    if "show_claimed" in request.args:
        items = items_filter.all()
    else:
        items = items_filter.filter_by(claimed=False).all()

    return api_response(True, items=[item.to_dict() for item in items])


@api.route("/items", methods=["POST"])
def create_item():
    if request.user is None:
        return api_response(False)

    title = request.json.get("title")

    if not isinstance(title, str) or not title.strip():
        return api_response(False, message="`title` is required")

    try:
        cost = parse_cost(request.json.get("cost"))
        desire = int(request.json.get("desire"))
    except (TypeError, ValueError):
        return api_response(False, message="`cost` and `desire` must be valid numbers")

    link = request.json.get("link")
    if link is not None and not isinstance(link, str):
        return api_response(False, message="`link` must be a string")

    if link and match(r"^https?:\/\/", link) is None:
        link = "http://" + link

    base64_image = request.json.get("image")

    image_file_path = None
    if base64_image:
        if not isinstance(base64_image, str):
            return api_response(False, message="`image` must be a base64 string")
        try:
            image_file_path = image_processor.process_image(base64_image)
        except InvalidImageError:
            return api_response(False, message="Could not read the uploaded image")

    new_item = Item(
        title=title, cost=cost, link=link, image_file_path=image_file_path, desire=desire
    ).save()

    return api_response(True, item=new_item.to_dict())


@api.route("/items/<int:item_id>", methods=["GET"])
def get_item(item_id: int):
    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    return api_response(True, item=item.to_dict())

@api.route("/items/<int:item_id>", methods=["PATCH"])
def patch_item(item_id: int):
    if request.user is None:
        return api_response(False)

    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    new_desire = request.json.get("desire")
    new_cost = request.json.get("cost")

    try:
        if new_desire not in (None, ""):
            item.desire = int(new_desire)
        if new_cost not in (None, ""):
            item.cost = parse_cost(new_cost)
    except (TypeError, ValueError):
        db.session.rollback()
        return api_response(False, message="`cost` and `desire` must be valid numbers")

    item.save()

    return api_response(True, item=item.to_dict())

@api.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id: int):
    if request.user is None:
        return api_response(False)

    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    image_file_path = item.image_file_path
    item.delete()

    # Remove the file only after the row is gone, so a failed delete keeps its image
    if image_file_path:
        image_processor.delete_image(image_file_path)

    return api_response(True)


@api.route("/items/<int:item_id>/claim", methods=["POST"])
def claim(item_id: int):
    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    # A single conditional UPDATE, so two simultaneous claims can't both succeed
    updated = (
        Item.filter(Item.id == item.id, Item.claimed.isnot(True))
        .update(
            {Item.claimed: True, Item.claimed_date: datetime.now()},
            synchronize_session=False,
        )
    )
    db.session.commit()

    if not updated:
        flash("Item already claimed", "warning")
        return api_response(False, message="Item already claimed")

    return api_response(True)


@api.route("/items/<int:item_id>/unclaim", methods=["POST"])
def unclaim(item_id: int):
    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    item.claimed = False
    item.claimed_date = None

    item.save()

    return api_response(True)
