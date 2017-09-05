#!/usr/bin/env bash

mkdir -p .data-docker/postgresql
docker-compose up -d --build
