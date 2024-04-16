FROM python:3.12-slim as poetry

RUN --mount=type=cache,target=/var/cache/apt \
        apt-get update && apt-get install -y binutils
ENV PYTHONPYCACHEPREFIX=/var/cache/pycache
RUN --mount=type=cache,target=/var/cache/pycache pip install poetry
COPY handbrake_watcher/ /app/handbrake_watcher
COPY pyproject.toml /app
COPY poetry.lock /app
COPY README.md /app
WORKDIR /app
RUN --mount=type=cache,target=/var/cache/pycache poetry install
RUN --mount=type=cache,target=/var/cache/pycache poetry run build_converter
RUN --mount=type=cache,target=/var/cache/pycache poetry run build_normalizer

FROM python:3.12-slim
RUN --mount=type=cache,target=/var/cache/apt \
        apt-get update && apt-get install -y ffmpeg
COPY --from=poetry /app/dist /dist
RUN pip3 install ffmpeg-normalize
ENTRYPOINT ["/dist/converter"]