FROM frictionlessdata/datapackage-pipelines
RUN pip install --no-cache-dir pipenv pew
RUN apk --update --no-cache add build-base python3-dev bash jq libxml2 libxml2-dev git libxslt libxslt-dev curl \
                                libpq postgresql-dev openssl antiword
RUN apk --update --no-cache add linux-headers
COPY Pipfile /pipelines/
COPY Pipfile.lock /pipelines/
RUN pipenv install --system --deploy --ignore-pipfile
RUN apk --update --no-cache add python && pip install psycopg2-binary
RUN pip install --upgrade https://github.com/OriHoch/datapackage-pipelines/archive/cli-support-list-of-pipeline-ids.zip
RUN cd / && wget -q https://storage.googleapis.com/pub/gsutil.tar.gz && tar xfz gsutil.tar.gz && rm gsutil.tar.gz
COPY boto.config /root/.boto
COPY datapackage_pipelines_knesset /pipelines/datapackage_pipelines_knesset
COPY setup.py /pipelines/
RUN pip install .
COPY bills /pipelines/bills
COPY committees /pipelines/committees
COPY knesset /pipelines/knesset
COPY laws /pipelines/laws
COPY lobbyists /pipelines/lobbyists
COPY members /pipelines/members
COPY plenum /pipelines/plenum
COPY votes /pipelines/votes
COPY votes_kmember /pipelines/votes_kmember
COPY bin /pipelines/bin
COPY *.py /pipelines/
COPY knesset /pipelines/knesset
COPY *.sh /pipelines/
ENV RTF_EXTRACTOR_BIN /knesset/bin/rtf_extractor.py
ENTRYPOINT ["/pipelines/pipelines_script.sh"]
