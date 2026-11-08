# WishLog
WishLog is a self-hostable personal wishlist

## Running with Docker

All persistent state lives in two directories inside the container:

- `/var/database`: the SQLite database and the session secret key
- `/var/images`: uploaded item images

The easiest way to run it is Docker Compose, which sets up both volumes for you:

```sh
cp .env.example .env    # optional: change the port or other settings
docker compose up -d
```

Then open http://localhost:8080 and register the owner account.

Without Compose, mount both directories as named volumes so your data and logins survive the container being recreated:

```sh
docker build -t wishlog .
docker run -d -p 8080:80 \
    -v wishlog-db:/var/database \
    -v wishlog-images:/var/images \
    wishlog
```

See [.env.example](.env.example) for all the settings.
