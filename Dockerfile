FROM python:3.7.3

COPY ./requirements.txt ./requirements.txt

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# provide as secrets if necessary
COPY ./.env ./.env
COPY ./data ./data
COPY ./app.py ./app.py
COPY ./utils.py ./utils.py

# need to update en-sentiment.xml file
RUN cp ./data/en-sentiment.xml /usr/local/lib/python3.7/site-packages/textblob/en/en-sentiment.xml

# install ffmpeg
RUN apt-get -y update && \
    apt-get -y install software-properties-common && \
    apt-get -y install ffmpeg

ENTRYPOINT [ "python", "app.py" ]
