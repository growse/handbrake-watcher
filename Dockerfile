FROM python:3.12-slim

RUN --mount=type=cache,target=/var/cache/apt \
        apt-get update && apt-get install -y git ffmpeg

RUN pip install poetry

COPY . /app
WORKDIR /app

RUN poetry install

ENTRYPOINT ["poetry", "run"]