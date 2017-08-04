#!/usr/bin/env bash

docker-compose -f ./docker-compose.yml -f ./docker-compose.override.deployment.yml config > docker-compose-deployment-combined.yml
