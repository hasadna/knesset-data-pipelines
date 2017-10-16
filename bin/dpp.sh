#!/usr/bin/env bash

# execute dpp inside the docker container (for local development only)

PASSTHROUGH_ENV_VARS=""
PASSTHROUGH_ENV_VARS+="OVERRIDE_COMMITTEE_MEETING_IDS=${OVERRIDE_COMMITTEE_MEETING_IDS} "

docker-compose exec app bash -c "${PASSTHROUGH_ENV_VARS}dpp $*"
