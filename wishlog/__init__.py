from flask import Flask

from .before_request import register_before_request
from .database import db
from .views import register_blueprints


def create_app(config="wishlog.config.Config") -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)

    db.init_app(app)

    with app.app_context():
        register_blueprints(app)

    register_before_request(app)

    return app
