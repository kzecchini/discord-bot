FROM python:3.10-slim

# for ghcr.io storage
LABEL org.opencontainers.image.source=https://github.com/kzecchini/discord-bot

# install ffmpeg
RUN apt-get -y update && \
    apt-get -y install software-properties-common ffmpeg opus-tools

COPY ./requirements.txt ./requirements.txt

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY ./app.py ./app.py
COPY ./audio.py ./audio.py

ENTRYPOINT [ "python", "app.py" ]
