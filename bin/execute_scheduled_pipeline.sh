#!/usr/bin/env sh

# schedule a pipeline to be execute immediately - can be used both locally and from docker container
# bin/execute_scheduled_pipeline.sh <pipeline_id>

PIPELINES_BIN_PATH="${PIPELINES_BIN_PATH:-bin}"
PIPELINE_ID="${1}"
"${PIPELINES_BIN_PATH}/celery_run_task.sh" execute_scheduled_pipeline "'${PIPELINE_ID}'"
