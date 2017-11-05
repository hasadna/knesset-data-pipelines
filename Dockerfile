FROM orihoch/knesset-data-pipelines-base:v1.0.5

COPY requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN mkdir /knesset
WORKDIR /knesset

COPY datapackage_pipelines_knesset /knesset/datapackage_pipelines_knesset
COPY setup.py /knesset/

ENV PYTHONUNBUFFERED 1

RUN cd /knesset && pip install .

ENV PIPELINES_BIN_PATH /knesset/bin
ENV RTF_EXTRACTOR_BIN /knesset/bin/rtf_extractor.py

# this environment variable is set by k8s - so we force it to the default here
# see the comments on https://github.com/puckel/docker-airflow/issues/46
ENV FLOWER_PORT 5555

COPY bills /knesset/bills
COPY committees /knesset/committees
COPY laws /knesset/laws
COPY plenum /knesset/plenum
COPY votes /knesset/votes
COPY members /knesset/members
COPY bin /knesset/bin
COPY docker-run.sh /knesset/

ENTRYPOINT ["/knesset/docker-run.sh"]

EXPOSE 5000
VOLUME /knesset/data
