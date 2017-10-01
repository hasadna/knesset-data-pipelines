#!/usr/bin/env bash

# start the local development environment

mkdir -p .data-docker/postgresql
docker-compose up -d --build
