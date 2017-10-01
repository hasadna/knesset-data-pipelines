#!/usr/bin/env bash

# execute dpp inside the docker container (for local development only)

eval "docker-compose exec app dpp $*"
