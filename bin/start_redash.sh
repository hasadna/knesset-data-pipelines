#!/usr/bin/env bash

# start the redash local testing environment

bin/start.sh

# wait 3 seconds to ensure DB is up
sleep 3

bin/initialize_redash_db.sh

bin/redash_compose.sh up -d
