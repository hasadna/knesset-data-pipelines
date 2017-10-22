#!/usr/bin/env sh

# run a celery command - can be used both locally and from docker container

export CELERY_BACKEND="rpc://"
export CELERY_BROKER="redis://${DPP_REDIS_HOST:-localhost}:6379/6"

# TODO: allow to set a different redis port and db
python3 -m celery -A datapackage_pipelines.app $*
