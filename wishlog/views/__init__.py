from flask import Flask

from .pages import pages


def register_blueprints(app: Flask):
    app.register_blueprint(pages)
