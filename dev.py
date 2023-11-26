from wishlog import create_app


def dev_server():
    app = create_app()

    app.run(debug=True)


if __name__ == "__main__":
    dev_server()
