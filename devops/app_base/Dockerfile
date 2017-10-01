FROM python:3.6-alpine

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

# install python 2.7 - used for rtf_extractor
RUN apk add --update bash
RUN curl -kL https://raw.github.com/saghul/pythonz/master/pythonz-install | bash
RUN /usr/local/pythonz/bin/pythonz install 2.7.13
RUN curl https://bootstrap.pypa.io/get-pip.py > /get-pip.py
RUN ln -s /usr/local/pythonz/pythons/CPython-2.7.13/bin/python /usr/local/bin/python2
RUN python2 /get-pip.py
RUN ln -s /usr/local/pythonz/pythons/CPython-2.7.13/bin/pip /usr/local/bin/pip2
# install python2.7 dependencies
RUN pip2 install pyth==0.6.0

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt
