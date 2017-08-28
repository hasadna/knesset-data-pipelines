FROM python:3.6-alpine

# install Python 2.7 - for rtf extractor
ENV GPG_KEY C01E1CAD5EA2C4F0B8E3571504C367C218ADD4FF
ENV PYTHON_VERSION 2.7.13
ENV PYTHON_PIP_VERSION 9.0.1

COPY .docker/install_python2.sh /install_python2.sh
RUN /install_python2.sh

# install system requirements
RUN apk add --update --no-cache --virtual=build-dependencies \
    antiword \
    build-base \
    curl \
    jpeg-dev \
    libxml2-dev libxml2 \
    libxslt-dev libxslt \
    libstdc++ \
    libpq \
    python3-dev postgresql-dev
RUN apk --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --update add leveldb leveldb-dev
RUN pip install psycopg2 datapackage-pipelines-github lxml datapackage-pipelines[speedup]
RUN apk add --update --no-cache git

# libre office was used to parse rtf file but it's too heavy, dropping for now
# RUN apk add libreoffice

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir /knesset
WORKDIR /knesset
COPY . /knesset/

ENV PYTHONUNBUFFERED 1

RUN cd /knesset && pip install .

ENTRYPOINT ["/knesset/docker-run.sh"]

EXPOSE 5000
VOLUME /knesset/data
