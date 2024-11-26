from wishlog import create_app


def dev_server():
    app = create_app()

    app.run(debug=True, host="127.0.0.1")


if __name__ == "__main__":
    dev_server()
