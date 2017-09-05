#!/usr/bin/env sh

if [ "${1}" == "" ]; then
  echo "usage: /execute_scheduled_pipeline.sh <pipeline_id>"
else
  echo "execute_scheduled_pipeline.delay('${1}')" | python3 -m celery -b redis://redis:6379/6 -A datapackage_pipelines.app shell --python
fi
