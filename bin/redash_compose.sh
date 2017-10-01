#!/usr/bin/env bash

# start the local redash for testing

docker-compose -f docker-compose.redash.yml -p knessetdatapipelines_redash $*
