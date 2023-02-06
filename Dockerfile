FROM ghcr.io/hasadna/knesset-data-pipelines/knesset-data-pipelines:8028b98004108716f5f59d652c333c2176c664c3
#FROM orihoch/datapackage-pipelines:1.7.1-oh-2
#RUN apk --update --no-cache add \
#        build-base python3-dev bash jq libxml2 libxml2-dev git libxslt libxslt-dev curl \
#        libpq postgresql-dev openssl antiword linux-headers python &&\
#    python3 -m pip install --no-cache-dir pipenv pew 'pip<18.1' psycopg2 &&\
#    cd / && wget -q https://storage.googleapis.com/pub/gsutil.tar.gz && tar xfz gsutil.tar.gz && rm gsutil.tar.gz
#COPY boto.config /root/.boto
#COPY Pipfile /pipelines/
#COPY Pipfile.lock /pipelines/
#RUN pipenv install --system --deploy --ignore-pipfile
#RUN python3 -m pip install jupyterlab
COPY datapackage_pipelines_knesset /pipelines/datapackage_pipelines_knesset
COPY setup.py /pipelines/
RUN pip install -e .
COPY jupyter-notebooks /pipelines/jupyter-notebooks
RUN jupyter nbconvert -y --to=html --output-dir=committees/dist/static/html/jupyter-notebooks jupyter-notebooks/*.ipynb
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
COPY .dpp_spec_ignore /pipelines/
ENV RTF_EXTRACTOR_BIN /knesset/bin/rtf_extractor.py
ENV KNESSET_PIPELINES_DATA_PATH=/pipelines/data
#ENV KNESSET_DATASERVICE_INCREMENTAL=1
