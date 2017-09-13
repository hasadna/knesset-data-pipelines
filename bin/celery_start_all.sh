#!/usr/bin/env sh

# start all the celery services - can be used both locally and from within a docker container

PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
DPP_REDIS_HOST="${DPP_REDIS_HOST:-localhost}"
DPP_WORKER_CONCURRENCY="${DPP_WORKER_CONCURRENCY:-2}"

"${PIPELINES_BIN_PATH}/celery_run.sh" beat -l INFO &
"${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "management@%h" --concurrency=1 -Q datapackage-pipelines-management &
"${PIPELINES_BIN_PATH}/celery_run.sh" worker -l INFO -n "workers@%h" "--concurrency=${DPP_WORKER_CONCURRENCY}" -Q datapackage-pipelines
