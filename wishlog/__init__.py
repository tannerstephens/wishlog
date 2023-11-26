from flask import Flask


def create_app(config="wishlog.config.Config"):
    app = Flask(__name__)
    app.config.from_object(config)

    @app.route("/")
    def hello():
        return "world"

    return app
