FROM orihoch/knesset-data-pipelines-base:v1.0.5

ENV PYTHONUNBUFFERED 1
ENV PIPELINES_BIN_PATH /knesset/bin
ENV RTF_EXTRACTOR_BIN /knesset/bin/rtf_extractor.py
# this environment variable is set by k8s - so we force it to the default here
# see the comments on https://github.com/puckel/docker-airflow/issues/46
ENV FLOWER_PORT 5555

COPY entrypoint.sh .

RUN set xe \
    && pip install -r requirements.txt

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]