#!/usr/bin/env sh

set -e

mkdir -p data/table_schemas

pip install -r requirements.txt
which antiword > /dev/null || sudo apt-get install antiword
pip install -e .[develop]
