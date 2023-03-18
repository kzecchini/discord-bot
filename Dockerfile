FROM python:3.10-slim

COPY ./requirements.txt ./requirements.txt

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# for now we just include secrets in the container
COPY ./.env ./.env
COPY ./app.py ./app.py
COPY ./audio.py ./audio.py

# install ffmpeg
RUN apt-get -y update && \
    apt-get -y install software-properties-common ffmpeg opus-tools

ENTRYPOINT [ "python", "app.py" ]
