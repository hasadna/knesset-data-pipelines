#!/usr/bin/env sh

# install the local development environment

set -e

pipenv install
which antiword > /dev/null || sudo apt-get install antiword
pipenv run pip install -e '.[develop]'
pipenv shell
