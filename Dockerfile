FROM python:3.10

COPY ./requirements.txt ./requirements.txt

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# for now we just include secrets in the container
COPY ./.env ./.env
COPY ./app.py ./app.py
COPY ./utils.py ./utils.py

# install ffmpeg
RUN apt-get -y update && \
    apt-get -y install software-properties-common && \
    apt-get -y install ffmpeg

ENTRYPOINT [ "python", "app.py" ]
