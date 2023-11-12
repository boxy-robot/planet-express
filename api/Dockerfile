FROM ubuntu:latest

ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  POETRY_VIRTUALENVS_CREATE=false

RUN apt update && apt install -y \
    software-properties-common \
    python-setuptools \
    python3-pip \
    libindi-dev \
    swig \
    libcfitsio-dev \
    libnova-dev

RUN apt-add-repository ppa:mutlaqja/ppa
RUN apt update && apt install -y python3-indi-client

WORKDIR /app

RUN pip install poetry
COPY pyproject.toml poetry.lock /app/
RUN poetry install --no-interaction --no-ansi --no-root
