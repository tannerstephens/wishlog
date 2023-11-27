from flask import Blueprint, jsonify, request, session

from ..constants import USER_ID
from ..models import User

api = Blueprint("api", __name__, url_prefix="/api")


def api_response(success: bool, **kwargs):
    return jsonify(dict(success=success, **kwargs))


@api.errorhandler(500)
def handle_500(err):
    return api_response(False, error=str(err))


@api.route("/users", methods=["POST"])
def register():
    if User.get_by_id(1) is not None:
        return api_response(False)

    new_user = User(request.json.get("username"), request.json.get("password")).save()

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
