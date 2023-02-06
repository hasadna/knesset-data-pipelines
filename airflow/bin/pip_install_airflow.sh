#!/usr/bin/env bash

AIRFLOW_VERSION=2.5.1
PYTHON_VERSION="$(python --version | cut -d " " -f 2 | cut -d "." -f 1-2)"

[ "${PYTHON_VERSION}" != "3.8" ] && echo invalid Python version, must use Python 3.8 && exit 1

CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip install --upgrade "apache-airflow[async,virtualenv,password,postgres]==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}" &&\
pip install -r requirements.txt