from flask import Flask


def register_blueprints(app: Flask):
    from .api import api
    from .images import images
    from .pages import pages

    app.register_blueprint(pages)
    app.register_blueprint(api)
    app.register_blueprint(images)
