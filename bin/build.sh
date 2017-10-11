#!/usr/bin/env bash

# can be used to build all docker images needed for local development

if [ ! -f .env ]; then cp .env.dist .env; fi
docker-compose build
