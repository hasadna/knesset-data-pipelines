#!/usr/bin/env bash

# clean the local development environment

bin/docker/stop.sh
docker-compose rm -f
