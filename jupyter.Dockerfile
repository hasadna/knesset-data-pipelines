FROM jupyter/minimal-notebook

USER root

RUN apt-get update -y &&\
    apt-get install -y \
        build-essential python3-dev libxml2 libxml2-dev git libxslt1.1 libxslt1-dev postgresql-client \
        redis libpq5 libpq-dev libleveldb-dev libleveldb1v5 bash jq curl openssl antiword &&\
    python3 -m pip install --no-cache-dir  \
        psycopg2 datapackage-pipelines-github datapackage-pipelines-sourcespec-registry \
        datapackage-pipelines-aws datapackage-pipelines[speedup] pipenv pew 'pip<18.1' &&\
    cd / && wget -q https://storage.googleapis.com/pub/gsutil.tar.gz && tar xfz gsutil.tar.gz && rm gsutil.tar.gz
COPY boto.config /root/.boto
WORKDIR /pipelines
COPY Pipfile /pipelines/
COPY Pipfile.lock /pipelines/
RUN pipenv install --system --deploy --ignore-pipfile
COPY datapackage_pipelines_knesset /pipelines/datapackage_pipelines_knesset
COPY setup.py /pipelines/
RUN pip install -e .
COPY bills /pipelines/bills
COPY committees /pipelines/committees
COPY knesset /pipelines/knesset
COPY laws /pipelines/laws
COPY lobbyists /pipelines/lobbyists
COPY members /pipelines/members
COPY people /pipelines/people
COPY plenum /pipelines/plenum
COPY votes /pipelines/votes
#COPY votes_kmember /pipelines/votes_kmember
COPY bin /pipelines/bin
COPY *.py /pipelines/
COPY *.sh /pipelines/
ENV RTF_EXTRACTOR_BIN /knesset/bin/rtf_extractor.py
ENV KNESSET_PIPELINES_DATA_PATH=/pipelines/data
ENV KNESSET_DATASERVICE_INCREMENTAL=1

COPY jupyter-notebooks /pipelines/jupyter-notebooks
RUN chown -R jovyan:root /pipelines /home/jovyan

USER jovyan
