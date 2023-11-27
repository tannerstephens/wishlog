from flask import Flask

from .before_request import register_before_request
from .database import db
from .views import register_blueprints


def create_app(config="wishlog.config.Config") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    with app.app_context():
        db.init_app(app)
        register_blueprints(app)

    register_before_request(app)

    return app
