#!/usr/bin/env sh

# install the local development environment

set -e

mkdir -p data/table_schemas data/aggregations

pip install -r requirements.txt
which antiword > /dev/null || sudo apt-get install antiword
pip install -e .[develop]
