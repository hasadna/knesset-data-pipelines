#!/usr/bin/env sh

# run a celery command - can be used both locally and from docker container

DPP_REDIS_HOST="${DPP_REDIS_HOST:-localhost}"

# TODO: allow to set a different redis port and db
python3 -m celery -b "redis://${DPP_REDIS_HOST}:6379/6" -A datapackage_pipelines.app $*
