#!/usr/bin/env sh

# run a celery task asynchroneously - can be used both locally and from within a docker container
# bin/celery_run_task.sh <task_name> <delay_params>

PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
TASK_NAME="${1}"
DELAY_PARAMS="${2}"
echo "${TASK_NAME}.delay(${DELAY_PARAMS})" | "${PIPELINES_BIN_PATH}/celery_run.sh" shell --python
