# Pulled Feb 6, 2023
FROM --platform=linux/amd64 python:3.8@sha256:3e6443f94e3c82d4cce045f777042c67cff0fa3cdaa55b3ac7c36101e9b0405c

ARG KNESSET_DATA_PIPELINES_VERSION=467962784b807d7882b6ec6b7d9217afd19482d2
RUN cd /opt &&\
    curl -LO "https://github.com/hasadna/knesset-data-pipelines/archive/${KNESSET_DATA_PIPELINES_VERSION}.zip" &&\
    unzip "${KNESSET_DATA_PIPELINES_VERSION}.zip" &&\
    mv "knesset-data-pipelines-${KNESSET_DATA_PIPELINES_VERSION}" knesset-data-pipelines &&\
    rm "${KNESSET_DATA_PIPELINES_VERSION}.zip"

ENV KNESSET_DATA_PIPELINES_ROOT_DIR=/opt/knesset-data-pipelines
ENV KNESSET_DATA_PIPELINES_AIRFLOW_ROOT_DIR=/srv

WORKDIR /srv
COPY bin/ bin/
COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && bin/pip_install_airflow.sh
COPY dags/ dags/
COPY knesset_data_pipelines/ knesset_data_pipelines/
COPY setup.py ./
RUN pip install -e .

ENV AIRFLOW_HOME=/var/airflow
ENV AIRFLOW__CORE__DAGS_FOLDER=/srv/dags
ENV AIRFLOW__CORE__LOAD_EXAMPLES=False
ENV AIRFLOW__DATABASE__LOAD_DEFAULT_CONNECTIONS=False
ENV AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql://postgres:123456@airflow-db
ENV AIRFLOW__CORE__EXECUTOR=LocalExecutor
ENV AIRFLOW__CORE__PARALLELISM=4
ENV AIRFLOW__CORE__DAG_CONCURRENCY=1
ENV AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE=False
ENV AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION=False
ENV AIRFLOW__CORE__MAX_ACTIVE_RUNS_PER_DAG=1
ENV SQLALCHEMY_SILENCE_UBER_WARNING=1

COPY entrypoint.sh ./
ENTRYPOINT ["/srv/entrypoint.sh"]
