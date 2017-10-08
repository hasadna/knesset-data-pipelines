#!/bin/sh

export PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
export DPP_WORKER_CONCURRENCY="${DPP_WORKER_CONCURRENCY:-0}"
export DPP_REDIS_HOST="${DPP_REDIS_HOST:-localhost}"

# wait for redis
sleep 2

trap "exit 1" SIGTERM;
trap "exit 2" SIGINT;

if [ "${1}" == "" ]; then
    # run all processes - useful for development / testing
    dpp init
    rm -f *.pid
    if [ "${DPP_WORKER_CONCURRENCY}" != "0" ]; then
        "${PIPELINES_BIN_PATH}"/celery_start_all.sh &
    fi
    dpp serve
elif [ "${1}" == "workers" ]; then
    # runs workers according to DPP_WORKER_CONCURRENCY
    "${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "workers@%h" "--concurrency=${DPP_WORKER_CONCURRENCY}" -Q datapackage-pipelines
elif [ "${1}" == "management" ]; then
    # runs management processes - must only run once
    dpp init
    "${PIPELINES_BIN_PATH}/celery_run.sh" beat -l INFO &
    "${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "management@%h" --concurrency=1 -Q datapackage-pipelines-management
elif [ "${1}" == "serve" ]; then
    # runs the pipelines dashboard only - can have multiple instances
    dpp serve
elif [ "${1}" == "flower" ]; then
    "${PIPELINES_BIN_PATH}/celery_run.sh" flower --url_prefix=flower
else
    /bin/sh -c "$*"
fi
