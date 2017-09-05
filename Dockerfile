FROM orihoch/knesset-data-pipelines-base:v1.0.5

RUN mkdir /knesset
WORKDIR /knesset
COPY . /knesset/

ENV PYTHONUNBUFFERED 1

RUN cd /knesset && pip install .

ENTRYPOINT ["/knesset/docker-run.sh"]

EXPOSE 5000
VOLUME /knesset/data
