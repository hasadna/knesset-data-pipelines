FROM orihoch/sk8s-pipelines

RUN apk --update add antiword

ENV PYTHONUNBUFFERED 1
ENV PIPELINES_BIN_PATH /knesset/bin
ENV RTF_EXTRACTOR_BIN /knesset/bin/rtf_extractor.py
# this environment variable is set by k8s - so we force it to the default here
# see the comments on https://github.com/puckel/docker-airflow/issues/46
ENV FLOWER_PORT 5555

COPY Pipfile /pipelines/
COPY Pipfile.lock /pipelines/
RUN pipenv install --system --deploy --ignore-pipfile && pipenv check

COPY datapackage_pipelines_knesset /pipelines/datapackage_pipelines_knesset
COPY setup.py /pipelines/
RUN pip install .

COPY bills /pipelines/bills
COPY committees /pipelines/committees
COPY laws /pipelines/laws
COPY members /pipelines/members
COPY plenum /pipelines/plenum
COPY votes /pipelines/votes
COPY bin /pipelines/bin
