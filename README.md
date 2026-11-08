# WishLog

A self-hostable personal wishlist. Keep one list of the things you'd like and share the link with friends and family. They can mark things as purchased so nobody buys the same gift twice, and you don't find out what's coming.

## Features

- **One list, one owner.** The first account registered owns the list. Everyone else just visits the page, no account needed.
- **Duplicate-free gifting.** Visitors mark an item as purchased and it drops off the list for everyone else.
- **Surprises stay surprises.** As the owner you don't see what's been claimed, unless you turn on *Spoil My Surprises*.
- **Prioritize by desire.** Give each item a desire score and sort the list by desire, name or cost.
- **Links and pictures.** Attach a store link and an image to each item. Images are resized automatically.
- **Small and simple.** A single container with SQLite storage. No external database to run.

## Quick start

With Docker Compose, using the [`docker-compose.yml`](docker-compose.yml) in this repository:

```sh
cp .env.example .env    # optional: change the port or other settings
docker compose up -d
```

Open <http://localhost:8080> and register: that account becomes the owner. Then share the URL with whoever you're buying gifts with.

### Without Compose

```sh
docker run -d --name wishlog -p 8080:80 \
    -v wishlog-database:/var/database \
    -v wishlog-images:/var/images \
    ghcr.io/tannerstephens/wishlog:latest
```

Images are published to `ghcr.io/tannerstephens/wishlog` for `linux/amd64` and `linux/arm64` on every push to `master`. Use `latest`, or a `sha-<commit>` tag to pin an exact build.

## Configuration

Everything is optional. Copy [`.env.example`](.env.example) to `.env` to change settings.

| Variable | Default (in the container) | Description |
| --- | --- | --- |
| `WISHLOG_PORT` | `8080` | Port the app is published on (Compose only). |
| `SECRET_KEY` | *generated* | Key that signs login sessions. If unset, a random key is generated on first start and saved to `SECRET_KEY_FILE`. |
| `SECRET_KEY_FILE` | `/var/database/.secret_key` | Where the generated key is kept. |
| `DATABASE_URI` | `sqlite:////var/database/wishlog.db` | Database connection. Only SQLite is supported. |
| `IMAGE_STORAGE_DIRECTORY` | `/var/images` | Where uploaded images are stored. |

Leave unused settings commented out. An empty value such as `DATABASE_URI=` overrides the default instead of falling back to it.

## Running it for real

### Data and backups

All state lives in two volumes:

| Volume | Contents |
| --- | --- |
| `/var/database` | The SQLite database and the session secret key |
| `/var/images` | Uploaded item images |

To back up, copy both out of the container:

```sh
docker compose cp wishlog:/var/database ./backup/database
docker compose cp wishlog:/var/images ./backup/images
```

### Updating

```sh
docker compose pull
docker compose up -d
```

Database migrations run automatically when the container starts.

### Exposing it to the internet

The container serves plain HTTP on port 80. If people will reach it over the internet, put it behind a reverse proxy that handles HTTPS, such as Caddy, Traefik or nginx, so the owner's login isn't sent unencrypted.

## Development

You'll need Python 3.12, [Pipenv](https://pipenv.pypa.io/) and, optionally, [Task](https://taskfile.dev/).

```sh
pipenv install
export IMAGE_STORAGE_DIRECTORY="$PWD/images" && mkdir -p images
task migrate    # or: pipenv run alembic upgrade head
task dev        # or: pipenv run python dev.py
```

The dev server runs at <http://127.0.0.1:5000> with auto-reload. Locally the database is `wishlog.db` and the session key is `.secret_key`, both in the project root. Images default to `/tmp`, which is why the example above sets `IMAGE_STORAGE_DIRECTORY`.

After changing a model, generate a migration and check it before committing:

```sh
task make-migrations    # or: pipenv run alembic revision --autogenerate
```

### Project layout

```
wishlog/
├── models/          SQLAlchemy models (User, Item)
├── views/
│   ├── api.py       JSON API under /api
│   ├── pages.py     HTML pages
│   └── images.py    Serves uploaded images
├── templates/       Jinja page templates
├── static/          JavaScript, CSS and images for the frontend
└── config.py        Settings read from environment variables
alembic/             Database migrations
```

The frontend is plain JavaScript with [Handlebars](https://handlebarsjs.com/) templates and [Bulma](https://bulma.io/) styling, talking to the JSON API.

## License

[MIT](LICENSE) © Tanner Stephens
