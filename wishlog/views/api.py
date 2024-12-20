from datetime import datetime
from re import match

from flask import Blueprint, current_app, flash, jsonify, request, session

from ..constants import USER_ID
from ..image_processor import ImageProcessor
from ..models import Item, User

api = Blueprint("api", __name__, url_prefix="/api")

image_processor = ImageProcessor(current_app.config["IMAGE_STORAGE_DIRECTORY"])


def api_response(success: bool, **kwargs):
    return jsonify(dict(success=success, **kwargs))


@api.route("/users", methods=["POST"])
def register():
    if User.get_by_id(1) is not None:
        return api_response(False)

    new_user = User(request.json.get("username"), request.json.get("password")).save()

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
        return api_response(False, "`username` and `password` are required")

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

    if title is None:
        return api_response(False, "`title` is required")

    cost = float(request.json["cost"])
    desire = int(request.json['desire'])
    link = request.json.get("link")

    if link and match(r"^https?:\/\/", link) is None:
        link = "http://" + link

    base64_image = request.json.get("image")

    image_file_path = None
    if base64_image:
        image_file_path = image_processor.process_image(base64_image)

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
    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    new_desire = request.json.get("desire")
    new_cost = request.json.get('cost')

    if (new_desire or new_cost):
        item.desire = int(new_desire) if new_desire else item.desire
        item.cost = float(new_cost) if new_cost else item.cost

        item.save()

    return api_response(True, item=item.to_dict())

@api.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id: int):
    if request.user is None:
        return api_response(False)

    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    item.delete()

    return api_response(True)


@api.route("/items/<int:item_id>/claim", methods=["POST"])
def claim(item_id: int):
    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    if item.claimed:
        flash("Item already claimed", "warning")
        return api_response(False, message="Item already claimed")

    item.claimed = True
    item.claimed_date = datetime.now()

    item.save()

    return api_response(True)


@api.route("/items/<int:item_id>/unclaim", methods=["POST"])
def unclaim(item_id: int):
    if (item := Item.get_by_id(item_id)) is None:
        return api_response(False, message="Item not found")

    item.claimed = False
    item.claimed_date = None

    item.save()

    return api_response(True)
