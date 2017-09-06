#!/usr/bin/env sh

# bin/update_pipelines.sh [status] [completed_pipeline_id] [completed_pipeline_trigger]

PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
STATUS="${1:-'update'}"
COMPLETED_PIPELINE_ID="${2:-None}"
COMPLETED_PIPELINE_TRIGGER="${3:-None}"
"${PIPELINES_BIN_PATH}/celery_run_task.sh" update_pipelines "${STATUS}, ${COMPLETED_PIPELINE_ID}, ${COMPLETED_PIPELINE_TRIGGER}"
