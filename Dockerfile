FROM python:3.12 AS base

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONFAULTHANDLER=1

FROM base AS python-deps


RUN pip install pipenv
RUN apt-get update && apt-get install -y --no-install-recommends gcc

COPY Pipfile .
COPY Pipfile.lock .
RUN PIPENV_VENV_IN_PROJECT=1 pipenv install --deploy

FROM base AS runtime

COPY --from=python-deps /.venv /.venv
ENV PATH="/.venv/bin:$PATH"
ENV FLASK_APP=wishlog:create_app

# Keep all persistent state under /var so it can be mounted as volumes
ENV DATABASE_URI=sqlite:////var/database/wishlog.db
ENV SECRET_KEY_FILE=/var/database/.secret_key
ENV IMAGE_STORAGE_DIRECTORY=/var/images

# Headless Chromium for link previews of stores that refuse plain requests.
# Installed system-wide so the unprivileged app user can run it.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN playwright install --with-deps --only-shell chromium \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser
RUN mkdir /var/database
RUN mkdir /var/images
RUN chown -R appuser:appuser /var/database
RUN chown -R appuser:appuser /var/images
VOLUME ["/var/database", "/var/images"]
WORKDIR /home/appuser
USER appuser

COPY . .

EXPOSE 80
ENTRYPOINT ["/home/appuser/docker-entrypoint.sh"]
