from flask import Flask

from .api import api
from .pages import pages


def register_blueprints(app: Flask):
    app.register_blueprint(pages)
    app.register_blueprint(api)
