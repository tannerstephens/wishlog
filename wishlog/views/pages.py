from flask import Blueprint, flash, redirect, render_template, request

from ..models import User

pages = Blueprint("pages", __name__)


@pages.before_request
def check_for_setup():
    if request.path != "/register" and User.get_by_id(1) is None:
        flash("Please perform first time setup", "warning")
        return redirect("/register")


@pages.route("/")
def home():
    return render_template("pages/home.html")


@pages.route("/register")
def register():
    if User.get_by_id(1) is not None:
        return redirect("/")
    return render_template("pages/register.html")


@pages.route("/login")
def login():
    if request.user:
        return redirect("/")
    return render_template("pages/login.html")
