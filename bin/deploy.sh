#!/usr/bin/env bash

if [ ! -f docker-compose-deployment-combined.yml ]; then
  echo "please run bin/generate-stack-file.py to generate a stack config file"
  echo "you might want to review/edit this stack file before deploying"
else
  bin/build.sh
  docker stack deploy -c docker-compose-deployment-combined.yml
fi

