#!/usr/bin/env bash

# start all the celery services - can be used both locally and from within a docker container

PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
DPP_REDIS_HOST="${DPP_REDIS_HOST:-localhost}"
DPP_WORKER_CONCURRENCY="${DPP_WORKER_CONCURRENCY:-2}"


"${PIPELINES_BIN_PATH}/celery_run.sh" beat -l INFO &
BEAT_PID="${!}"

"${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "management@%h" --concurrency=1 -Q datapackage-pipelines-management &
MANAGEMENT_PID="${!} "

"${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "workers@%h" "--concurrency=${DPP_WORKER_CONCURRENCY}" -Q datapackage-pipelines &
WORKERS_PID="${!}"

kill_handler() {
    PIDS="${BEAT_PID} ${MANAGEMENT_PID} ${WORKERS_PID}"
    echo "non graceful killing (PIDS = ${PIDS})"
    for PID in $PIDS; do kill -TERM "${PID}"; done
    sleep 2
    for PID in $PIDS; do kill -KILL "${PID}"; done
    exit 1
}

trap "echo 'caught SIGTERM, performing non-graceful shutdown'; kill_handler" SIGTERM;
trap "echo 'caught SIGINT, performing non-graceful shutdown'; kill_handler" SIGINT;

while true; do tail -f /dev/null & wait ${!}; done
