FROM orihoch/sk8s-pipelines:v0.0.3-b

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

# temporary fix for dpp not returning correct exit code
# TODO: remove once datapackage-pipelines v1.5.4 is released
RUN pip install --upgrade https://github.com/OriHoch/datapackage-pipelines/archive/fix-exit-code.zip

COPY datapackage_pipelines_knesset /pipelines/datapackage_pipelines_knesset
COPY setup.py /pipelines/
RUN pip install .

COPY --from=orihoch/sk8s-pipelines:v0.0.3-g /entrypoint.sh /entrypoint.sh

COPY bills /pipelines/bills
COPY committees /pipelines/committees
COPY knesset /pipelines/knesset
COPY laws /pipelines/laws
COPY lobbyists /pipelines/lobbyists
COPY members /pipelines/members
COPY plenum /pipelines/plenum
COPY votes /pipelines/votes
COPY votes_kmember /pipelines/votes
COPY bin /pipelines/bin
COPY *.py /pipelines/
COPY knesset /pipelines/knesset
COPY *.sh /pipelines/

ENV PIPELINES_SCRIPT="cd /pipelines && (source ./pipelines_script.sh)"
ENV RUN_PIPELINE_CMD=run_pipeline
