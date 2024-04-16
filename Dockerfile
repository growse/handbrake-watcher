FROM python:3.12-slim as poetry

RUN --mount=type=cache,target=/var/cache/apt \
        apt-get update && apt-get install -y git ffmpeg binutils
ENV PYTHONPYCACHEPREFIX=/var/cache/pycache
RUN --mount=type=cache,target=/var/cache/pycache pip install poetry
COPY handbrake_watcher/ /app/handbrake_watcher
COPY pyproject.toml /app
COPY poetry.lock /app
COPY README.md /app
WORKDIR /app
RUN --mount=type=cache,target=/var/cache/pycache poetry install
RUN --mount=type=cache,target=/var/cache/pycache poetry run build

FROM debian:bookworm-slim
COPY --from=poetry /app/dist /dist
ENTRYPOINT ["/dist/converter"]