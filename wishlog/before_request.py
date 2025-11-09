from flask import Flask, redirect, request, session

from .models import User


def register_before_request(app: Flask):
    @app.before_request
    def process_session():
        current_user = None
        if user_id := session.get("user_id"):
            current_user = User.get_by_id(user_id)

        request.user = current_user

        session.permanent = True
