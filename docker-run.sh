#!/bin/sh

PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
DPP_WORKER_CONCURRENCY="${DPP_WORKER_CONCURRENCY:-0}"

# wait for redis
sleep 2

mkdir -p data/table_schemas

if [ "${1}" == "" ]; then
    dpp init
    rm -f *.pid
    if [ "${DPP_WORKER_CONCURRENCY}" != "0" ]; then
        "${PIPELINES_BIN_PATH}"/celery_start_all.sh &
    fi
    dpp serve
elif [ "${1}" == "flower" ]; then
    "${PIPELINES_BIN_PATH}/celery_run.sh" flower --url_prefix=flower
else
    /bin/sh -c "$*"
fi
