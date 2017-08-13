#!/bin/sh

# wait for redis
sleep 2

if [ "${1}" == "" ]; then
    dpp init
    rm -f *.pid
    if [ "${DPP_WORKER_CONCURRENCY}" != "0" ]; then
        python3 -m celery -b "redis://${DPP_REDIS_HOST}:6379/6" -A datapackage_pipelines.app -l INFO beat &
        python3 -m celery -b "redis://${DPP_REDIS_HOST}:6379/6" --concurrency=1 -A datapackage_pipelines.app -Q datapackage-pipelines-management -l INFO worker &
        python3 -m celery -b "redis://${DPP_REDIS_HOST}:6379/6" --concurrency=$DPP_WORKER_CONCURRENCY -A datapackage_pipelines.app -Q datapackage-pipelines -l INFO worker &
    fi
    dpp serve
else
    /bin/sh -c "$*"
fi
