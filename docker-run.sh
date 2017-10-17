#!/usr/bin/env bash

export PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
export DPP_WORKER_CONCURRENCY="${DPP_WORKER_CONCURRENCY:-0}"
export DPP_REDIS_HOST="${DPP_REDIS_HOST:-localhost}"

# wait for redis
sleep 2

PIDS=""
GRACEFUL_SHUTDOWN="1"

if [ "${1}" == "" ]; then
    # run all processes - useful for development / testing
    dpp init
    rm -f *.pid
    if [ "${DPP_WORKER_CONCURRENCY}" != "0" ]; then
        "${PIPELINES_BIN_PATH}"/celery_start_all.sh &
        PIDS+="${!} "
    fi
    dpp serve &
    PIDS+="${!} "
    "${PIPELINES_BIN_PATH}"/start_dpp_metrics.sh &
    PIDS+="${!}"

elif [ "${1}" == "workers" ]; then
    if [ "${DPP_WORKER_CONCURRENCY}" == "0" ]; then
        # this is used for idle worker - which allows to run jobs manually on it using ssh
        echo "idling..."
    else
        # runs workers according to DPP_WORKER_CONCURRENCY
        GRACEFUL_SHUTDOWN="0"
        "${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "workers@%h" "--concurrency=${DPP_WORKER_CONCURRENCY}" -Q datapackage-pipelines &
        PIDS+="${!}"
    fi

elif [ "${1}" == "management" ]; then
    # runs management processes - must only run once
    dpp init
    "${PIPELINES_BIN_PATH}/celery_run.sh" beat -l INFO &
    PIDS+="${!} "
    "${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "management@%h" --concurrency=1 -Q datapackage-pipelines-management &
    PIDS+="${!}"

elif [ "${1}" == "serve" ]; then
    # runs the pipelines dashboard only - can have multiple instances
    dpp serve &
    PIDS+="${!}"

elif [ "${1}" == "flower" ]; then
    exec "${PIPELINES_BIN_PATH}/celery_run.sh" flower --url_prefix=flower &
    PIDS+="${!}"

elif [ "${1}" == "metrics" ]; then
    "${PIPELINES_BIN_PATH}"/start_dpp_metrics.sh &
    PIDS+="${!}"

else
    /bin/sh -c "$*"
    exit $?

fi

# waits for PIDS and handles shutdown

kill_handler() {
    if [ "${PIDS}" != "" ]; then
        echo "non graceful killing (PIDS = ${PIDS})"
        for PID in $PIDS; do kill -TERM "${PID}"; done
        sleep 2
        for PID in $PIDS; do kill -KILL "${PID}"; done
    fi
    exit 0
}

graceful_handler() {
    if [ "${PIDS}" != "" ]; then
        echo "graceful shutdown (PIDS = ${PIDS})"
        for PID in $PIDS; do kill -TERM "${PID}"; done
        for PID in $PIDS; do wait "${PID}"; done
    fi
    exit 0
}

if [ "${GRACEFUL_SHUTDOWN}" == "1" ]; then
    trap "echo 'caught SIGTERM, attempting graceful shutdown'; graceful_handler" SIGTERM;
    trap "echo 'caught SIGINT, attempting graceful shutdown'; graceful_handler" SIGINT;
else
    trap "echo 'caught SIGTERM, performing non-graceful shutdown'; kill_handler" SIGTERM;
    trap "echo 'caught SIGINT, performing non-graceful shutdown'; kill_handler" SIGINT;
fi

while true; do tail -f /dev/null & wait ${!}; done
