#!/usr/bin/env bash

if docker-compose exec db sudo -u postgres psql -c "CREATE DATABASE redash;"; then
    bin/redash_compose.sh run server create_db
fi
